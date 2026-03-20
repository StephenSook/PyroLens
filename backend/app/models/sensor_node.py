"""Sensor node ORM model."""

from sqlalchemy import Column, DateTime, Integer, String, func
from sqlalchemy.orm import relationship

from geoalchemy2 import Geometry

from app.db.base import Base


class SensorNode(Base):
    __tablename__ = "sensor_nodes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    device_id = Column(String, unique=True, nullable=False)
    location_geom = Column(Geometry(srid=4326), nullable=False)
    site_name = Column(String, nullable=False)
    installed_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    status = Column(String, nullable=False)

    sensor_readings = relationship("SensorReading", back_populates="sensor_node")
