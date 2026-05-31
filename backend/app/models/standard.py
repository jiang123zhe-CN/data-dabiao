from datetime import datetime, timezone

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey

from app.core.database import Base


class ClassificationCategory(Base):
    __tablename__ = "classification_categories"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=False)
    code = Column(String(100), unique=True, nullable=False, index=True)
    parent_id = Column(Integer, ForeignKey("classification_categories.id"), nullable=True, index=True)
    level = Column(Integer, nullable=False, default=0)
    category_type = Column(String(50), nullable=False, default="business")
    description = Column(Text, nullable=True)
    keywords = Column(String(500), nullable=True)
    regulatory_ref = Column(String(500), nullable=True)
    version = Column(String(50), nullable=False, default="v1.0")
    sort_order = Column(Integer, nullable=False, default=0)
    is_active = Column(Boolean, nullable=False, default=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))


class TieringRule(Base):
    __tablename__ = "tiering_rules"

    id = Column(Integer, primary_key=True, autoincrement=True)
    tier_level = Column(String(10), nullable=False, index=True)
    tier_name = Column(String(50), nullable=False)
    rule_type = Column(String(50), nullable=False, default="keyword")
    rule_content = Column(Text, nullable=False)
    priority = Column(Integer, nullable=False, default=0)
    regulatory_basis = Column(String(500), nullable=True)
    version = Column(String(50), nullable=False, default="v1.0")
    is_active = Column(Boolean, nullable=False, default=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
