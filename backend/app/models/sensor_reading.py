"""Sensor reading ORM model."""

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from app.db.base import Base


class SensorReading(Base):
    __tablename__ = "sensor_readings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    sensor_id = Column(Integer, ForeignKey("sensor_nodes.id"), nullable=False, index=True)
    timestamp = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), index=True)
    temperature = Column(Float, nullable=False)
    humidity = Column(Float, nullable=False)
    soil_moisture = Column(Float, nullable=False)
    wind_speed = Column(Float, nullable=True)
    raw_payload = Column(JSONB, nullable=False)

    sensor_node = relationship("SensorNode", back_populates="sensor_readings")
