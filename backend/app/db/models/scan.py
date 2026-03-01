from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.base import Base


class Scan(Base):
    __tablename__ = "iqa_scans"

    id = Column(Integer, primary_key=True, index=True)
    input_dir = Column(String, nullable=False)
    output_dir = Column(String, nullable=False)
    reject_dir = Column(String, nullable=False)
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    total_images = Column(Integer, nullable=False, default=0)
    passed_count = Column(Integer, nullable=False, default=0)
    failed_count = Column(Integer, nullable=False, default=0)
    status = Column(String(20), nullable=False, default="running")

    assessments = relationship("Assessment", back_populates="scan", cascade="all, delete-orphan")
