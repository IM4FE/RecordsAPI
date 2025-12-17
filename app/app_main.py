from fastapi import FastAPI, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from typing import List, Optional
import datetime
from pathlib import Path
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from . import models, schemas
from .database import get_db, engine, Base

# Создаем таблицы
import asyncio
async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(models.Base.metadata.create_all)

app = FastAPI(title="Records API")

@app.on_event("startup")
async def startup_event():
    await init_db()

@app.on_event("shutdown")
async def shutdown_event():
    """Принудительно закрываем engine"""
    await engine.dispose()

static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/", tags=["system"])
def read_root():
    index_path = Path(__file__).parent / "static" / "index.html"
    if index_path.exists():
        return FileResponse(index_path)
    return {"message": "Welcome to Record API"}

# Проверка работы
@app.get("/health", tags=["system"])
async def health():
    return {"status": "ok", "timestamp": datetime.datetime.now().isoformat()}


# Создание записи
@app.post("/records", response_model=schemas.RecordResponse, status_code=201, tags=["records"])
async def create_record(record: schemas.RecordCreate, db: AsyncSession = Depends(get_db)):
    db_record = models.Record(**record.dict())
    db.add(db_record)
    await db.commit()
    await db.refresh(db_record)
    return db_record

# Получение списка записей с фильтрацией
@app.get("/records", response_model=List[schemas.RecordResponse], tags=["records"])
async def list_records(
        db: AsyncSession = Depends(get_db),
        q: Optional[str] = Query(None),
        is_done: Optional[bool] = Query(None),
        record_date_before: Optional[datetime.datetime] = Query(None),
        record_date_after: Optional[datetime.datetime] = Query(None),
        sort: str = Query("created_at"),
        order: str = Query("desc"),
        offset: int = Query(0, ge=0),
        limit: int = Query(50, ge=1, le=100),
):
    stmt = select(models.Record)

    if q:
        search_pattern = f"%{q}%"
        stmt = stmt.where(
            or_(
                models.Record.title.ilike(search_pattern),
                models.Record.details.ilike(search_pattern)
            )
        )

    if is_done is not None:
        stmt = stmt.where(models.Record.is_done == is_done)

    # Валидация сортировки (без изменений)
    valid_sort_fields = {"id", "title", "is_done", "record_date", "created_at", "updated_at"}
    if sort not in valid_sort_fields:
        raise HTTPException(400, detail=f"Invalid sort field: {valid_sort_fields}")

    # Сортировка
    sort_column = getattr(models.Record, sort)
    if order == "desc":
        sort_column = sort_column.desc()
    stmt = stmt.order_by(sort_column).offset(offset).limit(limit)

    result = await db.execute(stmt)
    records = result.scalars().all()
    return records

# Получение записи по ID
@app.get("/records/{record_id}", response_model=schemas.RecordResponse, tags=["records"])
async def get_record(record_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.get(models.Record, record_id)
    if not result:
        raise HTTPException(404, "Record not found")
    return result


# Обновление записи
@app.put("/records/{record_id}", response_model=schemas.RecordResponse, tags=["records"])
async def update_record(
        record_id: int,
        record_update: schemas.RecordUpdate,
        db: AsyncSession = Depends(get_db)
):
    record = await db.get(models.Record, record_id)
    if not record:
        raise HTTPException(404, "Record not found")

    update_data = record_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(record, field, value)

    record.updated_at = datetime.datetime.now()
    await db.commit()
    await db.refresh(record)
    return record

# Удаление записи
@app.delete("/records/{record_id}", status_code=204, tags=["records"])
async def delete_record(record_id: int, db: AsyncSession = Depends(get_db)):
    record = await db.get(models.Record, record_id)
    if not record:
        raise HTTPException(404, "Record not found")

    await db.delete(record)
    await db.commit()
    return None