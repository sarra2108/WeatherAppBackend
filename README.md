# Weather App Backend

FastAPI backend for a weather assessment. It accepts flexible user-entered locations, validates them against OpenStreetMap/Nominatim, retrieves real-time and date-range weather from Open-Meteo, persists requests in SQLite, supports CRUD operations, enriches records with map links and nearby points of interest, and exports stored data.

## Run Locally

Use Python 3.11 or 3.12 for the pinned dependency set.

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open API docs at `http://127.0.0.1:8000/docs`.

## Main Endpoints

- `POST /weather-requests` - create a weather request for a location and date range.
- `GET /weather-requests` - list previous records.
- `GET /weather-requests/{id}` - read one stored record.
- `PATCH /weather-requests/{id}` - update location/date range/notes and refresh weather.
- `DELETE /weather-requests/{id}` - delete a stored record.
- `GET /weather-requests/{id}/export?format=json|csv|xml|markdown` - export one record.
- `GET /weather-requests/export?format=json|csv|xml|markdown` - export all records.
- `GET /weather/current?location=Toronto` - real-time weather lookup without persistence.

## Location Input

The backend accepts city/town names, postal or ZIP codes, landmarks, addresses, and GPS coordinates such as `43.6532,-79.3832`.

## Extra API Integration

- OpenStreetMap/Nominatim validates and normalizes locations.
- Open-Meteo provides current and daily weather.
- Nominatim reverse lookup enriches stored records with nearby map context.
- Records include Google Maps and OpenStreetMap URLs for the resolved coordinates.
