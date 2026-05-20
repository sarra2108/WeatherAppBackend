from datetime import date
from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

from fastapi import Depends, FastAPI, HTTPException, Query, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db, init_db
from app.exceptions import ExternalServiceError, LocationNotFoundError, WeatherValidationError
from app.models import WeatherRequest
from app.schemas import (
    CurrentWeatherRead,
    ExportFormat,
    WeatherRequestCreate,
    WeatherRequestRead,
    WeatherRequestUpdate,
)
from app.services import build_map_data, export_records, fetch_weather, resolve_location, validate_date_range


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncGenerator[None, None]:
    init_db()
    yield


app = FastAPI(
    title="Weather App Backend",
    description="CRUD weather persistence API with location validation, Open-Meteo weather data, map enrichment, and exports.",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/weather/current", response_model=CurrentWeatherRead)
async def current_weather(location: str = Query(..., min_length=2)) -> dict:
    try:
        resolved = await resolve_location(location)
        today = date.today()
        weather = await fetch_weather(resolved["latitude"], resolved["longitude"], today, today)
        map_data = await build_map_data(resolved["latitude"], resolved["longitude"])
    except (LocationNotFoundError, WeatherValidationError) as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    except ExternalServiceError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

    return {
        "original_location": resolved["original_location"],
        "normalized_location": resolved["normalized_location"],
        "latitude": resolved["latitude"],
        "longitude": resolved["longitude"],
        "timezone": weather["timezone"],
        "current_weather": weather["current_weather"],
        "map_data": map_data,
    }


@app.post("/weather-requests", response_model=WeatherRequestRead, status_code=status.HTTP_201_CREATED)
async def create_weather_request(payload: WeatherRequestCreate, db: Session = Depends(get_db)) -> WeatherRequest:
    try:
        validate_date_range(payload.start_date, payload.end_date)
        resolved = await resolve_location(payload.location)
        weather = await fetch_weather(
            resolved["latitude"],
            resolved["longitude"],
            payload.start_date,
            payload.end_date,
        )
        map_data = await build_map_data(resolved["latitude"], resolved["longitude"])
    except (LocationNotFoundError, WeatherValidationError) as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    except ExternalServiceError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

    record = WeatherRequest(
        original_location=payload.location,
        normalized_location=resolved["normalized_location"],
        latitude=resolved["latitude"],
        longitude=resolved["longitude"],
        timezone=weather["timezone"],
        start_date=payload.start_date,
        end_date=payload.end_date,
        current_weather=weather["current_weather"],
        daily_weather=weather["daily_weather"],
        map_data=map_data,
        notes=payload.notes,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@app.get("/weather-requests", response_model=list[WeatherRequestRead])
def list_weather_requests(
    db: Session = Depends(get_db),
    location: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[WeatherRequest]:
    statement = select(WeatherRequest).order_by(WeatherRequest.created_at.desc()).offset(offset).limit(limit)
    if location:
        statement = (
            select(WeatherRequest)
            .where(WeatherRequest.normalized_location.ilike(f"%{location}%"))
            .order_by(WeatherRequest.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
    return list(db.scalars(statement))


@app.get("/weather-requests/export")
def export_all_weather_requests(
    format: ExportFormat = Query(default=ExportFormat.json),
    db: Session = Depends(get_db),
) -> Response:
    records = list(db.scalars(select(WeatherRequest).order_by(WeatherRequest.created_at.desc())))
    media_type, body = export_records(records, format.value)
    return Response(content=body, media_type=media_type)


@app.get("/weather-requests/{request_id}", response_model=WeatherRequestRead)
def get_weather_request(request_id: int, db: Session = Depends(get_db)) -> WeatherRequest:
    return _get_record_or_404(db, request_id)


@app.patch("/weather-requests/{request_id}", response_model=WeatherRequestRead)
async def update_weather_request(
    request_id: int,
    payload: WeatherRequestUpdate,
    db: Session = Depends(get_db),
) -> WeatherRequest:
    record = _get_record_or_404(db, request_id)
    new_location = payload.location or record.original_location
    new_start = payload.start_date or record.start_date
    new_end = payload.end_date or record.end_date

    try:
        validate_date_range(new_start, new_end)
        should_refresh = bool(payload.location or payload.start_date or payload.end_date)
        if should_refresh:
            resolved = await resolve_location(new_location)
            weather = await fetch_weather(resolved["latitude"], resolved["longitude"], new_start, new_end)
            map_data = await build_map_data(resolved["latitude"], resolved["longitude"])

            record.original_location = new_location
            record.normalized_location = resolved["normalized_location"]
            record.latitude = resolved["latitude"]
            record.longitude = resolved["longitude"]
            record.timezone = weather["timezone"]
            record.start_date = new_start
            record.end_date = new_end
            record.current_weather = weather["current_weather"]
            record.daily_weather = weather["daily_weather"]
            record.map_data = map_data
        if "notes" in payload.model_fields_set:
            record.notes = payload.notes
    except (LocationNotFoundError, WeatherValidationError) as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    except ExternalServiceError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@app.delete("/weather-requests/{request_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_weather_request(request_id: int, db: Session = Depends(get_db)) -> Response:
    record = _get_record_or_404(db, request_id)
    db.delete(record)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.get("/weather-requests/{request_id}/export")
def export_weather_request(
    request_id: int,
    format: ExportFormat = Query(default=ExportFormat.json),
    db: Session = Depends(get_db),
) -> Response:
    record = _get_record_or_404(db, request_id)
    media_type, body = export_records([record], format.value)
    return Response(content=body, media_type=media_type)


def _get_record_or_404(db: Session, request_id: int) -> WeatherRequest:
    record = db.get(WeatherRequest, request_id)
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Weather request not found.")
    return record
