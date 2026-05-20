from datetime import date, datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class ExportFormat(StrEnum):
    json = "json"
    csv = "csv"
    xml = "xml"
    markdown = "markdown"


class WeatherRequestCreate(BaseModel):
    location: str = Field(..., min_length=2, max_length=255, examples=["Toronto", "10001", "Eiffel Tower"])
    start_date: date
    end_date: date
    notes: str | None = Field(default=None, max_length=1000)

    @field_validator("location")
    @classmethod
    def normalize_location_input(cls, value: str) -> str:
        cleaned = " ".join(value.strip().split())
        if not cleaned:
            raise ValueError("Location cannot be blank.")
        return cleaned

    @model_validator(mode="after")
    def validate_date_order(self) -> "WeatherRequestCreate":
        if self.end_date < self.start_date:
            raise ValueError("end_date must be on or after start_date.")
        return self


class WeatherRequestUpdate(BaseModel):
    location: str | None = Field(default=None, min_length=2, max_length=255)
    start_date: date | None = None
    end_date: date | None = None
    notes: str | None = Field(default=None, max_length=1000)

    @field_validator("location")
    @classmethod
    def normalize_optional_location(cls, value: str | None) -> str | None:
        if value is None:
            return value
        cleaned = " ".join(value.strip().split())
        if not cleaned:
            raise ValueError("Location cannot be blank.")
        return cleaned


class WeatherRequestRead(BaseModel):
    id: int
    original_location: str
    normalized_location: str
    latitude: float
    longitude: float
    timezone: str | None
    start_date: date
    end_date: date
    current_weather: dict
    daily_weather: list[dict]
    map_data: dict
    notes: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CurrentWeatherRead(BaseModel):
    original_location: str
    normalized_location: str
    latitude: float
    longitude: float
    timezone: str | None
    current_weather: dict
    map_data: dict


class ErrorResponse(BaseModel):
    detail: str
