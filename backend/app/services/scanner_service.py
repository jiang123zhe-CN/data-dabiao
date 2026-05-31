import json
from datetime import datetime, timezone
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import Session
from app.models.field import Field
from app.models.datasource import DataSource, ScanTask


class ScanOrchestrator:
    """Orchestrates data source scanning to discover fields."""

    SOURCE_TYPES = ["mysql", "postgresql", "csv", "excel"]

    def __init__(self, db: Session):
        self.db = db

    def test_connection(self, ds: DataSource) -> tuple[bool, str]:
        """Test if a data source connection works."""
        try:
            if ds.source_type in ("mysql", "postgresql"):
                config = json.loads(ds.connection_config or "{}")
                engine = create_engine(self._build_url(ds.source_type, config), connect_args={"connect_timeout": 5})
                with engine.connect():
                    pass
                return True, "连接成功"
            elif ds.source_type in ("csv", "excel"):
                return True, "文件类型数据源就绪"
            else:
                return False, f"不支持的数据源类型: {ds.source_type}"
        except Exception as e:
            return False, str(e)

    def scan(self, ds: DataSource, scan_type: str = "full", user_id: int = None) -> ScanTask:
        """Scan a data source and discover fields."""
        task = ScanTask(
            datasource_id=ds.id, scan_type=scan_type, status="running",
            started_at=datetime.now(timezone.utc), created_by=user_id,
        )
        self.db.add(task)
        self.db.commit()

        try:
            if ds.source_type in ("mysql", "postgresql"):
                config = json.loads(ds.connection_config or "{}")
                engine = create_engine(self._build_url(ds.source_type, config))
                inspector = inspect(engine)
                tables = inspector.get_table_names()
                task.total_objects = len(tables)
                new_fields = 0

                for table_name in tables:
                    columns = inspector.get_columns(table_name)
                    for col in columns:
                        field_code = f"{ds.source_type}_{table_name}_{col['name']}"
                        existing = self.db.query(Field).filter(Field.field_code == field_code).first()
                        if not existing:
                            field = Field(
                                field_code=field_code,
                                name=col["name"],
                                data_type=str(col["type"]).upper(),
                                table_name=table_name,
                                database_name=config.get("database", ""),
                                source="scanned",
                                created_by=user_id,
                            )
                            self.db.add(field)
                            new_fields += 1
                    task.processed_objects += 1
                    task.new_fields = new_fields

                ds.total_tables = len(tables)
                ds.total_fields += new_fields

            elif ds.source_type == "csv":
                task.status = "completed"
                task.completed_at = datetime.now(timezone.utc)
                task.new_fields = 0
                self.db.commit()
                return task

            ds.last_scan_at = datetime.now(timezone.utc)
            ds.status = "active"
            task.status = "completed"
            task.completed_at = datetime.now(timezone.utc)
            task.new_fields = new_fields
            self.db.commit()
            return task

        except Exception as e:
            task.status = "failed"
            task.error_log = str(e)
            self.db.commit()
            return task

    @staticmethod
    def _build_url(source_type: str, config: dict) -> str:
        if source_type == "mysql":
            return f"mysql+pymysql://{config['user']}:{config['password']}@{config['host']}:{config.get('port', 3306)}/{config['database']}"
        elif source_type == "postgresql":
            return f"postgresql+psycopg2://{config['user']}:{config['password']}@{config['host']}:{config.get('port', 5432)}/{config['database']}"
        raise ValueError(f"Unknown source type: {source_type}")
