from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user, require_role
from app.models.user import User
from app.models.datasource import DataSource, ScanTask
from app.schemas.datasource import (
    DataSourceCreate, DataSourceUpdate, DataSourceResponse,
    ScanTaskResponse, ConnectionTestResult,
)
from app.services.scanner_service import ScanOrchestrator
from app.services.log_service import log_action

router = APIRouter(prefix="/api/datasources", tags=["DataSources"])


@router.get("/", response_model=list[DataSourceResponse])
def list_datasources(
    source_type: str | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    q = db.query(DataSource).filter(DataSource.is_active == True)
    if source_type:
        q = q.filter(DataSource.source_type == source_type)
    return q.order_by(DataSource.updated_at.desc()).all()


@router.get("/{ds_id}", response_model=DataSourceResponse)
def get_datasource(ds_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    ds = db.query(DataSource).filter(DataSource.id == ds_id, DataSource.is_active == True).first()
    if not ds:
        raise HTTPException(status_code=404, detail="Data source not found")
    return ds


@router.post("/", response_model=DataSourceResponse, status_code=201)
def create_datasource(
    body: DataSourceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("data_admin", "admin")),
    request: Request = None,
):
    ds = DataSource(**body.model_dump(), created_by=current_user.id)
    db.add(ds)
    db.commit()
    db.refresh(ds)
    log_action(db, user_id=current_user.id, username=current_user.username,
               action="create", module="datasources", target_type="datasource", target_id=ds.id,
               detail={"name": ds.name, "source_type": ds.source_type},
               ip_address=request.client.host if request else None)
    return ds


@router.put("/{ds_id}", response_model=DataSourceResponse)
def update_datasource(
    ds_id: int, body: DataSourceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("data_admin", "admin")),
    request: Request = None,
):
    ds = db.query(DataSource).filter(DataSource.id == ds_id, DataSource.is_active == True).first()
    if not ds:
        raise HTTPException(status_code=404, detail="Data source not found")
    for key, val in body.model_dump(exclude_unset=True).items():
        setattr(ds, key, val)
    db.commit()
    db.refresh(ds)
    log_action(db, user_id=current_user.id, username=current_user.username,
               action="update", module="datasources", target_type="datasource", target_id=ds.id,
               ip_address=request.client.host if request else None)
    return ds


@router.delete("/{ds_id}")
def delete_datasource(
    ds_id: int, db: Session = Depends(get_db),
    current_user: User = Depends(require_role("data_admin", "admin")),
    request: Request = None,
):
    ds = db.query(DataSource).filter(DataSource.id == ds_id, DataSource.is_active == True).first()
    if not ds:
        raise HTTPException(status_code=404, detail="Data source not found")
    ds.is_active = False
    db.commit()
    log_action(db, user_id=current_user.id, username=current_user.username,
               action="delete", module="datasources", target_type="datasource", target_id=ds_id,
               ip_address=request.client.host if request else None)
    return {"message": "Data source deleted"}


@router.post("/{ds_id}/test", response_model=ConnectionTestResult)
def test_connection(
    ds_id: int, db: Session = Depends(get_db),
    current_user: User = Depends(require_role("data_admin", "admin")),
):
    ds = db.query(DataSource).filter(DataSource.id == ds_id, DataSource.is_active == True).first()
    if not ds:
        raise HTTPException(status_code=404, detail="Data source not found")
    orchestrator = ScanOrchestrator(db)
    success, message = orchestrator.test_connection(ds)
    return ConnectionTestResult(success=success, message=message)


@router.post("/{ds_id}/scan", response_model=ScanTaskResponse)
def scan_datasource(
    ds_id: int, scan_type: str = "full",
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("data_admin", "admin")),
):
    ds = db.query(DataSource).filter(DataSource.id == ds_id, DataSource.is_active == True).first()
    if not ds:
        raise HTTPException(status_code=404, detail="Data source not found")
    orchestrator = ScanOrchestrator(db)
    task = orchestrator.scan(ds, scan_type=scan_type, user_id=current_user.id)
    return task


@router.get("/{ds_id}/scan/status", response_model=ScanTaskResponse)
def get_scan_status(ds_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    task = db.query(ScanTask).filter(
        ScanTask.datasource_id == ds_id
    ).order_by(ScanTask.created_at.desc()).first()
    if not task:
        raise HTTPException(status_code=404, detail="No scan task found")
    return task


@router.get("/scans/", response_model=list[ScanTaskResponse])
def list_scans(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return db.query(ScanTask).order_by(ScanTask.created_at.desc()).limit(50).all()
