from typing import Any, TypeVar

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from rag_packages.shared.database.base import Base
from rag_packages.contracts.dto.shared_dto import BaseDTO
from rag_packages.contracts.types.shared_types import SortDirection


ModelType = TypeVar("ModelType", bound=Base)


class QueryParams(BaseDTO):
    filters: dict[str, Any] | None = None
    ids: list[int] | None = None
    query: str | None = None
    sort_by: str | None = None
    sort_direction: SortDirection = SortDirection.ASC
    limit: int | None = None
    offset: int | None = None


async def get_model_page(
    db: AsyncSession,
    model: type[ModelType],
    *,
    filters: dict[str, Any] | None = None,
    ids: list[int] | None = None,
    query: str | None = None,
    search_fields: list[str] | None = None,
    sort_by: str | None = None,
    sort_direction: SortDirection = SortDirection.ASC,
    limit: int | None = None,
    offset: int | None = None,
) -> tuple[list[ModelType], int]:
    model_columns = model.__table__.columns
    stmt = select(model)

    if filters:
        for field, value in filters.items():
            if field not in model_columns:
                raise ValueError(f"Invalid filter field: {field}")

            column = getattr(model, field)
            if isinstance(value, (list, tuple, set, frozenset)):
                stmt = stmt.where(column.in_(value))
            elif value is None:
                stmt = stmt.where(column.is_(None))
            else:
                stmt = stmt.where(column == value)

    if ids is not None:
        stmt = stmt.where(model.id.in_(ids))

    if query and search_fields:
        search = f"%{query}%"
        stmt = stmt.where(
            or_(*(getattr(model, field).ilike(search) for field in search_fields))
        )

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = await db.scalar(count_stmt)

    if sort_by:
        if sort_by not in model_columns:
            raise ValueError(f"Invalid sort field: {sort_by}")

        column = getattr(model, sort_by)
        stmt = stmt.order_by(
            column.desc() if sort_direction == "desc" else column.asc()
        )

    if offset is not None:
        stmt = stmt.offset(offset)

    if limit is not None:
        stmt = stmt.limit(limit)

    result = await db.execute(stmt)
    return list(result.scalars().all()), total or 0
