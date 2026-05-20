from datetime import date, datetime

from sqlalchemy import Date, DateTime, Float, Integer, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class WeatherRequest(Base):
    __tablename__ = "weather_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    original_location: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    normalized_location: Mapped[str] = mapped_column(String(512), nullable=False, index=True)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    timezone: Mapped[str | None] = mapped_column(String(128), nullable=True)
    start_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    end_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    current_weather: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    daily_weather: Mapped[list[dict]] = mapped_column(JSON, nullable=False, default=list)
    map_data: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
