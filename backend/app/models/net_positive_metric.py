"""Net positive metric ORM model."""

from sqlalchemy import Column, Float, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from app.db.base import Base


class NetPositiveMetric(Base):
    __tablename__ = "net_positive_metrics"

    id = Column(Integer, primary_key=True, autoincrement=True)
    burn_id = Column(Integer, ForeignKey("burns.id"), nullable=False, index=True)
    co2_prevented = Column(Float, nullable=False)
    prescribed_emissions = Column(Float, nullable=False)
    wildfire_baseline_emissions = Column(Float, nullable=False)
    biodiversity_gain_index = Column(Float, nullable=False)
    fuel_load_reduction_pct = Column(Float, nullable=False)
    vegetation_recovery_curve = Column(JSONB, nullable=False)

    burn = relationship("Burn", back_populates="net_positive_metrics")
