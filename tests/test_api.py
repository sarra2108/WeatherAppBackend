from collections.abc import Generator
from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app


@pytest.fixture()
def client(monkeypatch: pytest.MonkeyPatch) -> Generator[TestClient, None, None]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=engine)

    def override_get_db() -> Generator[Session, None, None]:
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    async def fake_resolve_location(location: str) -> dict:
        return {
            "original_location": location,
            "normalized_location": f"{location}, Ontario, Canada",
            "latitude": 43.6532,
            "longitude": -79.3832,
            "raw": {},
        }

    async def fake_fetch_weather(latitude: float, longitude: float, start_date: date, end_date: date) -> dict:
        return {
            "timezone": "America/Toronto",
            "current_weather": {
                "temperature": 72.4,
                "temperature_unit": "°F",
                "feels_like": 71.0,
                "humidity": 55,
                "precipitation": 0,
                "weather_code": 1,
                "wind_speed": 8.2,
                "observed_at": "2026-05-18T12:00",
            },
            "daily_weather": [
                {
                    "date": start_date.isoformat(),
                    "source": "forecast",
                    "temperature_max": 75.0,
                    "temperature_min": 62.0,
                    "precipitation_sum": 0.1,
                    "wind_speed_max": 12.0,
                    "weather_code": 2,
                }
            ],
        }

    async def fake_build_map_data(latitude: float, longitude: float) -> dict:
        return {
            "google_maps_url": f"https://www.google.com/maps/search/?api=1&query={latitude},{longitude}",
            "openstreetmap_url": f"https://www.openstreetmap.org/?mlat={latitude}&mlon={longitude}",
            "nearby_display_name": "Toronto, Ontario, Canada",
            "address": {"city": "Toronto"},
        }

    app.dependency_overrides[get_db] = override_get_db
    monkeypatch.setattr("app.main.resolve_location", fake_resolve_location)
    monkeypatch.setattr("app.main.fetch_weather", fake_fetch_weather)
    monkeypatch.setattr("app.main.build_map_data", fake_build_map_data)

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


def test_create_read_update_delete_weather_request(client: TestClient) -> None:
    create_response = client.post(
        "/weather-requests",
        json={
            "location": "Toronto",
            "start_date": "2026-05-18",
            "end_date": "2026-05-20",
            "notes": "Pack a light jacket.",
        },
    )
    assert create_response.status_code == 201
    created = create_response.json()
    assert created["id"] == 1
    assert created["normalized_location"] == "Toronto, Ontario, Canada"
    assert created["current_weather"]["temperature"] == 72.4

    list_response = client.get("/weather-requests")
    assert list_response.status_code == 200
    assert len(list_response.json()) == 1

    update_response = client.patch("/weather-requests/1", json={"location": "Ottawa", "notes": "Updated"})
    assert update_response.status_code == 200
    updated = update_response.json()
    assert updated["original_location"] == "Ottawa"
    assert updated["notes"] == "Updated"

    delete_response = client.delete("/weather-requests/1")
    assert delete_response.status_code == 204
    assert client.get("/weather-requests/1").status_code == 404


def test_rejects_invalid_date_order(client: TestClient) -> None:
    response = client.post(
        "/weather-requests",
        json={"location": "Toronto", "start_date": "2026-05-20", "end_date": "2026-05-18"},
    )
    assert response.status_code == 422


def test_export_csv_and_markdown(client: TestClient) -> None:
    client.post(
        "/weather-requests",
        json={"location": "Toronto", "start_date": "2026-05-18", "end_date": "2026-05-18"},
    )

    csv_response = client.get("/weather-requests/export?format=csv")
    assert csv_response.status_code == 200
    assert "original_location" in csv_response.text
    assert "Toronto" in csv_response.text

    markdown_response = client.get("/weather-requests/1/export?format=markdown")
    assert markdown_response.status_code == 200
    assert "# Weather Requests" in markdown_response.text
