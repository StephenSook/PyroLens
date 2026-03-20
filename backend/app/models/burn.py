"""Burn ORM model."""

from sqlalchemy import Column, Date, DateTime, Float, Integer, String, func
from sqlalchemy.orm import relationship

from geoalchemy2 import Geometry

from app.db.base import Base


class Burn(Base):
    __tablename__ = "burns"

    id = Column(Integer, primary_key=True, autoincrement=True)
    location_geom = Column(Geometry(srid=4326), nullable=False)
    county = Column(String, nullable=False)
    burn_date = Column(Date, nullable=False)
    acreage = Column(Float, nullable=False)
    objective = Column(String, nullable=False)
    outcome = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    burn_window_scores = relationship("BurnWindowScore", back_populates="burn")
    net_positive_metrics = relationship("NetPositiveMetric", back_populates="burn")
