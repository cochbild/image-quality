from sqlalchemy import Column, Integer, String, Boolean, DateTime, Float, ForeignKey, Text, CheckConstraint
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.base import Base


class Assessment(Base):
    __tablename__ = "iqa_assessments"

    id = Column(Integer, primary_key=True, index=True)
    scan_id = Column(Integer, ForeignKey("iqa_scans.id", ondelete="CASCADE"), nullable=False)
    filename = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    destination_path = Column(String, nullable=True)
    passed = Column(Boolean, nullable=True)
    triage_score = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    scan = relationship("Scan", back_populates="assessments")
    category_scores = relationship("CategoryScore", back_populates="assessment", cascade="all, delete-orphan")


class CategoryScore(Base):
    __tablename__ = "iqa_category_scores"

    id = Column(Integer, primary_key=True, index=True)
    assessment_id = Column(Integer, ForeignKey("iqa_assessments.id", ondelete="CASCADE"), nullable=False)
    category = Column(String(30), nullable=False)
    score = Column(Integer, nullable=False)
    reasoning = Column(Text, nullable=True)
    was_deep_dive = Column(Boolean, nullable=False, default=False)

    assessment = relationship("Assessment", back_populates="category_scores")

    __table_args__ = (
        CheckConstraint('score >= 1 AND score <= 10', name='ck_score_range'),
    )
