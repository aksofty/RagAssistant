from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.source import Source

async def get_sources(
        session: AsyncSession, active=True) -> list[Source]:

    query = (
        select(Source)
        .where(Source.active == active)
        .order_by(Source.id.asc())
    )
    result = await session.execute(query)
    return result.scalars().all()