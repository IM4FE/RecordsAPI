from fastapi import FastAPI, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import select, or_
from typing import List, Optional
import datetime

from . import models, schemas
from .database import get_db, engine, Base

# Создаем таблицы
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="DefaultRecord API")


# Проверка работы
@app.get("/health", tags=["system"])
def health():
    return {"status": "ok", "timestamp": datetime.datetime.now().isoformat()}


# Создание записи
@app.post(
    "/records",
    response_model=schemas.RecordResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["records"]
)
def create_record(record: schemas.RecordCreate, db: Session = Depends(get_db)):
    db_record = models.Record(**record.dict())
    db.add(db_record)
    db.commit()
    db.refresh(db_record)
    return db_record


# Получение списка записей с фильтрацией
@app.get("/records", response_model=List[schemas.RecordResponse], tags=["records"])
def list_records(
        db: Session = Depends(get_db),
        q: Optional[str] = Query(None, description="Поиск по названию или описанию"),
        is_done: Optional[bool] = Query(None, description="Фильтр по готовности"),
        record_date_before: Optional[datetime.datetime] = Query(None, description="Дата записи до"),
        record_date_after: Optional[datetime.datetime] = Query(None, description="Дата записи после"),
        sort: Optional[str] = Query("created_at", description="Поле для сортировки"),
        order: Optional[str] = Query("desc", description="Порядок сортировки (asc/desc)"),
        offset: int = Query(0, ge=0),
        limit: int = Query(50, ge=1, le=100),
):
    # Валидация параметров сортировки
    valid_sort_fields = {"id", "title", "is_done", "record_date", "created_at", "updated_at"}
    valid_orders = {"asc", "desc"}

    if sort not in valid_sort_fields:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid sort field. Must be one of: {valid_sort_fields}"
        )

    if order not in valid_orders:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid order. Must be one of: {valid_orders}"
        )

    # Построение запроса
    stmt = select(models.Record)

    # Применение фильтров
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

    if record_date_before is not None:
        stmt = stmt.where(models.Record.record_date <= record_date_before)

    if record_date_after is not None:
        stmt = stmt.where(models.Record.record_date >= record_date_after)

    # Сортировка
    sort_column = getattr(models.Record, sort)
    if order == "desc":
        sort_column = sort_column.desc()
    stmt = stmt.order_by(sort_column)

    # Пагинация
    stmt = stmt.offset(offset).limit(limit)

    records = db.scalars(stmt).all()
    return records


# Получение записи по ID
@app.get("/records/{record_id}", response_model=schemas.RecordResponse, tags=["records"])
def get_record(record_id: int, db: Session = Depends(get_db)):
    record = db.get(models.Record, record_id)
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")
    return record


# Обновление записи
@app.put("/records/{record_id}", response_model=schemas.RecordResponse, tags=["records"])
def update_record(
        record_id: int,
        record_update: schemas.RecordUpdate,
        db: Session = Depends(get_db)
):
    record = db.get(models.Record, record_id)
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")

    # Обновляем только переданные поля
    update_data = record_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(record, field, value)

    record.updated_at = datetime.datetime.now()
    db.commit()
    db.refresh(record)
    return record


# Удаление записи
@app.delete("/records/{record_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["records"])
def delete_task(record_id: int, db: Session = Depends(get_db)):
    record = db.get(models.Record, record_id)
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")

    db.delete(record)
    db.commit()
    return None