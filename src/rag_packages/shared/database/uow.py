from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session


class UnitOfWork:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            await self.session.rollback()
        else:
            await self.session.commit()


class UnitOfWorkSync:
    def __init__(self, db_session: Session):
        self.db = db_session

    # def commit(self, instance, should_refresh=True):
    #     self.db.commit()
    #     if should_refresh:
    #         self.db.refresh(instance)

    # def rollback(self):
    #     self.db.rollback()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            self.db.rollback()
        else:
            self.db.commit()
