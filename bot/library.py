from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Media, UserMedia


def library_keyboard(entries: list[UserMedia], page: int, total_pages: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for entry in entries:
        builder.button(
            text=entry.media.title[:45],
            callback_data=f"library_media:{entry.media.type}:{entry.media.mal_id}",
        )

    if total_pages > 1:
        if page > 0:
            builder.button(text="◀️", callback_data=f"library_page:{page - 1}")
        builder.button(text=f"{page + 1}/{total_pages}", callback_data="library_noop")
        if page + 1 < total_pages:
            builder.button(text="▶️", callback_data=f"library_page:{page + 1}")

    builder.button(text="🏠 Главное меню", callback_data="menu")
    builder.adjust(1)
    return builder.as_markup()


async def get_library_page(
    session: AsyncSession,
    user_id: int,
    status: str | None,
    page: int,
    per_page: int = 10,
) -> tuple[list[UserMedia], int]:
    query = (
        select(UserMedia)
        .join(Media, UserMedia.media_id == Media.id)
        .where(UserMedia.user_id == user_id)
        .order_by(UserMedia.updated_at.desc())
    )
    if status:
        query = query.where(UserMedia.status == status)

    from sqlalchemy import func

    count_query = select(func.count(UserMedia.id)).where(UserMedia.user_id == user_id)
    if status:
        count_query = count_query.where(UserMedia.status == status)

    total = (await session.execute(count_query)).scalar_one()
    total_pages = max(1, (total + per_page - 1) // per_page)

    result = await session.execute(
        query.offset(page * per_page).limit(per_page)
    )
    return list(result.scalars().unique().all()), total_pages
