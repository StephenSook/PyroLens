"""Burn window score ORM model."""

from sqlalchemy import CheckConstraint, Column, DateTime, Float, ForeignKey, Integer, String, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from app.db.base import Base


class BurnWindowScore(Base):
    __tablename__ = "burn_window_scores"
    __table_args__ = (
        CheckConstraint("score >= 0 AND score <= 100", name="ck_burn_window_scores_score_range"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    burn_id = Column(Integer, ForeignKey("burns.id"), nullable=True, index=True)
    lat = Column(Float, nullable=False)
    lon = Column(Float, nullable=False)
    timestamp = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), index=True)
    score = Column(Integer, nullable=False)
    recommendation = Column(String, nullable=False)
    source = Column(String, nullable=False, server_default=text("'ml'"))
    conditions = Column(JSONB, nullable=False)

    burn = relationship("Burn", back_populates="burn_window_scores")
