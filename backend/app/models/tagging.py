from datetime import datetime, timezone

from sqlalchemy import Column, Integer, String, Float, DateTime, Text, ForeignKey

from app.core.database import Base


class TaggingHistory(Base):
    __tablename__ = "tagging_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    field_id = Column(Integer, ForeignKey("fields.id"), nullable=False, index=True)
    action = Column(String(50), nullable=False)
    old_category_id = Column(Integer, ForeignKey("classification_categories.id"), nullable=True)
    new_category_id = Column(Integer, ForeignKey("classification_categories.id"), nullable=True)
    old_tier_level = Column(String(10), nullable=True)
    new_tier_level = Column(String(10), nullable=True)
    old_confidence = Column(Float, nullable=True)
    new_confidence = Column(Float, nullable=True)
    tagging_method = Column(String(50), nullable=True)
    operator_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    comment = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
