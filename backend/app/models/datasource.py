from datetime import datetime, timezone

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey

from app.core.database import Base


class DataSource(Base):
    __tablename__ = "data_sources"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=False)
    source_type = Column(String(50), nullable=False, index=True)
    connection_config = Column(Text, nullable=True)
    description = Column(Text, nullable=True)
    status = Column(String(20), nullable=False, default="inactive")
    last_scan_at = Column(DateTime, nullable=True)
    total_tables = Column(Integer, nullable=False, default=0)
    total_fields = Column(Integer, nullable=False, default=0)
    is_active = Column(Boolean, nullable=False, default=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))


class ScanTask(Base):
    __tablename__ = "scan_tasks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    datasource_id = Column(Integer, ForeignKey("data_sources.id"), nullable=False, index=True)
    scan_type = Column(String(20), nullable=False, default="full")
    status = Column(String(20), nullable=False, default="pending")
    total_objects = Column(Integer, nullable=False, default=0)
    processed_objects = Column(Integer, nullable=False, default=0)
    new_fields = Column(Integer, nullable=False, default=0)
    updated_fields = Column(Integer, nullable=False, default=0)
    error_log = Column(Text, nullable=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
