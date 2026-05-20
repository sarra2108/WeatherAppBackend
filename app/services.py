import csv
import io
import json
import re
from datetime import date, timedelta
from html import escape
from typing import Any

import httpx

from app.config import Settings, get_settings
from app.exceptions import ExternalServiceError, LocationNotFoundError, WeatherValidationError
from app.models import WeatherRequest


COORDINATE_PATTERN = re.compile(r"^\s*(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)\s*$")


def validate_date_range(start_date: date, end_date: date, settings: Settings | None = None) -> None:
    settings = settings or get_settings()
    if end_date < start_date:
        raise WeatherValidationError("end_date must be on or after start_date.")
    requested_days = (end_date - start_date).days + 1
    if requested_days > settings.max_date_range_days:
        raise WeatherValidationError(f"Date ranges are limited to {settings.max_date_range_days} days.")

    earliest_supported = date.today() - timedelta(days=90)
    latest_supported = date.today() + timedelta(days=16)
    if start_date < earliest_supported or end_date > latest_supported:
        raise WeatherValidationError(
            f"Date range must be between {earliest_supported.isoformat()} and {latest_supported.isoformat()}."
        )


def _parse_coordinates(location: str) -> tuple[float, float] | None:
    match = COORDINATE_PATTERN.match(location)
    if not match:
        return None
    latitude = float(match.group(1))
    longitude = float(match.group(2))
    if not -90 <= latitude <= 90 or not -180 <= longitude <= 180:
        raise WeatherValidationError("GPS coordinates must be valid latitude and longitude values.")
    return latitude, longitude


async def resolve_location(location: str, settings: Settings | None = None) -> dict[str, Any]:
    settings = settings or get_settings()
    coordinates = _parse_coordinates(location)
    try:
        async with httpx.AsyncClient(timeout=settings.http_timeout_seconds) as client:
            headers = {"User-Agent": "weather-app-assessment/1.0"}
            if coordinates:
                latitude, longitude = coordinates
                params = {"lat": latitude, "lon": longitude, "format": "jsonv2"}
                response = await client.get(f"{settings.nominatim_base_url}/reverse", params=params, headers=headers)
                _raise_for_external_response(response, "reverse geocoding")
                payload = response.json()
                display_name = payload.get("display_name") or f"{latitude},{longitude}"
                return {
                    "original_location": location,
                    "normalized_location": display_name,
                    "latitude": latitude,
                    "longitude": longitude,
                    "raw": payload,
                }

            params = {"q": location, "format": "jsonv2", "limit": 1, "addressdetails": 1}
            response = await client.get(f"{settings.nominatim_base_url}/search", params=params, headers=headers)
            _raise_for_external_response(response, "location search")
            results = response.json()
            if not results:
                raise LocationNotFoundError(f"Could not find a real location matching '{location}'.")
            best = results[0]
            return {
                "original_location": location,
                "normalized_location": best.get("display_name", location),
                "latitude": float(best["lat"]),
                "longitude": float(best["lon"]),
                "raw": best,
            }
    except httpx.RequestError as exc:
        raise ExternalServiceError("Failed to reach location service.") from exc


async def fetch_weather(
    latitude: float,
    longitude: float,
    start_date: date,
    end_date: date,
    settings: Settings | None = None,
) -> dict[str, Any]:
    settings = settings or get_settings()
    validate_date_range(start_date, end_date, settings)

    today = date.today()
    current_payload: dict[str, Any] = {}
    daily_rows: list[dict[str, Any]] = []

    try:
        async with httpx.AsyncClient(timeout=settings.http_timeout_seconds) as client:
            forecast_params = {
                "latitude": latitude,
                "longitude": longitude,
                "current": "temperature_2m,relative_humidity_2m,apparent_temperature,precipitation,weather_code,wind_speed_10m",
                "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_sum,wind_speed_10m_max",
                "temperature_unit": "fahrenheit",
                "wind_speed_unit": "mph",
                "precipitation_unit": "inch",
                "timezone": "auto",
            }
            current_response = await client.get(f"{settings.open_meteo_base_url}/forecast", params=forecast_params)
            _raise_for_external_response(current_response, "current weather")
            current_payload = current_response.json()

            if start_date <= min(end_date, today - timedelta(days=1)):
                archive_end = min(end_date, today - timedelta(days=1))
                archive_params = _daily_params(latitude, longitude, start_date, archive_end)
                archive_response = await client.get(settings.open_meteo_archive_url, params=archive_params)
                _raise_for_external_response(archive_response, "historical weather")
                daily_rows.extend(_daily_records(archive_response.json(), "archive"))

            if end_date >= today:
                forecast_start = max(start_date, today)
                forecast_params = _daily_params(latitude, longitude, forecast_start, end_date)
                forecast_response = await client.get(f"{settings.open_meteo_base_url}/forecast", params=forecast_params)
                _raise_for_external_response(forecast_response, "forecast weather")
                daily_rows.extend(_daily_records(forecast_response.json(), "forecast"))
    except httpx.RequestError as exc:
        raise ExternalServiceError("Failed to reach weather service.") from exc

    current = current_payload.get("current", {})
    units = current_payload.get("current_units", {})
    return {
        "timezone": current_payload.get("timezone"),
        "current_weather": {
            "temperature": current.get("temperature_2m"),
            "temperature_unit": units.get("temperature_2m"),
            "feels_like": current.get("apparent_temperature"),
            "humidity": current.get("relative_humidity_2m"),
            "precipitation": current.get("precipitation"),
            "weather_code": current.get("weather_code"),
            "wind_speed": current.get("wind_speed_10m"),
            "observed_at": current.get("time"),
        },
        "daily_weather": sorted(daily_rows, key=lambda item: item["date"]),
    }


async def build_map_data(latitude: float, longitude: float, settings: Settings | None = None) -> dict[str, Any]:
    settings = settings or get_settings()
    headers = {"User-Agent": "weather-app-assessment/1.0"}
    params = {"lat": latitude, "lon": longitude, "format": "jsonv2", "addressdetails": 1}
    try:
        async with httpx.AsyncClient(timeout=settings.http_timeout_seconds) as client:
            response = await client.get(f"{settings.nominatim_base_url}/reverse", params=params, headers=headers)
            _raise_for_external_response(response, "map enrichment")
            payload = response.json()
    except httpx.RequestError as exc:
        raise ExternalServiceError("Failed to reach map service.") from exc
    return {
        "google_maps_url": f"https://www.google.com/maps/search/?api=1&query={latitude},{longitude}",
        "openstreetmap_url": f"https://www.openstreetmap.org/?mlat={latitude}&mlon={longitude}#map=12/{latitude}/{longitude}",
        "nearby_display_name": payload.get("display_name"),
        "address": payload.get("address", {}),
    }


def export_records(records: list[WeatherRequest], export_format: str) -> tuple[str, str]:
    rows = [_record_to_dict(record) for record in records]
    if export_format == "json":
        return "application/json", json.dumps(rows, default=str, indent=2)
    if export_format == "csv":
        return "text/csv", _to_csv(rows)
    if export_format == "xml":
        return "application/xml", _to_xml(rows)
    if export_format == "markdown":
        return "text/markdown", _to_markdown(rows)
    raise WeatherValidationError("Unsupported export format.")


def _daily_params(latitude: float, longitude: float, start_date: date, end_date: date) -> dict[str, Any]:
    return {
        "latitude": latitude,
        "longitude": longitude,
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_sum,wind_speed_10m_max",
        "temperature_unit": "fahrenheit",
        "wind_speed_unit": "mph",
        "precipitation_unit": "inch",
        "timezone": "auto",
    }


def _daily_records(payload: dict[str, Any], source: str) -> list[dict[str, Any]]:
    daily = payload.get("daily") or {}
    dates = daily.get("time") or []
    records = []
    for index, day in enumerate(dates):
        records.append(
            {
                "date": day,
                "source": source,
                "weather_code": _value_at(daily, "weather_code", index),
                "temperature_max": _value_at(daily, "temperature_2m_max", index),
                "temperature_min": _value_at(daily, "temperature_2m_min", index),
                "precipitation_sum": _value_at(daily, "precipitation_sum", index),
                "wind_speed_max": _value_at(daily, "wind_speed_10m_max", index),
            }
        )
    return records


def _value_at(payload: dict[str, list[Any]], key: str, index: int) -> Any:
    values = payload.get(key) or []
    return values[index] if index < len(values) else None


def _raise_for_external_response(response: httpx.Response, service_name: str) -> None:
    try:
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        raise ExternalServiceError(f"Failed to retrieve {service_name}: HTTP {response.status_code}.") from exc


def _record_to_dict(record: WeatherRequest) -> dict[str, Any]:
    return {
        "id": record.id,
        "original_location": record.original_location,
        "normalized_location": record.normalized_location,
        "latitude": record.latitude,
        "longitude": record.longitude,
        "timezone": record.timezone,
        "start_date": record.start_date.isoformat(),
        "end_date": record.end_date.isoformat(),
        "current_weather": record.current_weather,
        "daily_weather": record.daily_weather,
        "map_data": record.map_data,
        "notes": record.notes,
        "created_at": record.created_at.isoformat() if record.created_at else None,
        "updated_at": record.updated_at.isoformat() if record.updated_at else None,
    }


def _to_csv(rows: list[dict[str, Any]]) -> str:
    output = io.StringIO()
    fieldnames = [
        "id",
        "original_location",
        "normalized_location",
        "latitude",
        "longitude",
        "timezone",
        "start_date",
        "end_date",
        "current_temperature",
        "notes",
    ]
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    for row in rows:
        writer.writerow(
            {
                "id": row["id"],
                "original_location": row["original_location"],
                "normalized_location": row["normalized_location"],
                "latitude": row["latitude"],
                "longitude": row["longitude"],
                "timezone": row["timezone"],
                "start_date": row["start_date"],
                "end_date": row["end_date"],
                "current_temperature": row["current_weather"].get("temperature"),
                "notes": row["notes"],
            }
        )
    return output.getvalue()


def _to_xml(rows: list[dict[str, Any]]) -> str:
    parts = ["<?xml version=\"1.0\" encoding=\"UTF-8\"?>", "<weather_requests>"]
    for row in rows:
        parts.append("  <weather_request>")
        for key, value in row.items():
            serialized = json.dumps(value, default=str) if isinstance(value, (dict, list)) else str(value or "")
            parts.append(f"    <{key}>{escape(serialized)}</{key}>")
        parts.append("  </weather_request>")
    parts.append("</weather_requests>")
    return "\n".join(parts)


def _to_markdown(rows: list[dict[str, Any]]) -> str:
    lines = ["# Weather Requests", "", "| ID | Location | Date Range | Current Temp | Notes |", "|---:|---|---|---:|---|"]
    for row in rows:
        current_temp = row["current_weather"].get("temperature")
        lines.append(
            f"| {row['id']} | {row['normalized_location']} | {row['start_date']} to {row['end_date']} | "
            f"{current_temp if current_temp is not None else ''} | {row['notes'] or ''} |"
        )
    return "\n".join(lines) + "\n"
