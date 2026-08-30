from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from database.models import Media, UserMedia


def library_keyboard(entries: list[UserMedia], page: int, total_pages: int, status: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for entry in entries:
        score = f"⭐{entry.score}" if entry.score is not None else ""
        title = entry.media.title[:38]
        builder.button(text=f"{score} {title}".strip(), callback_data=f"library_media:{entry.media.type}:{entry.media.mal_id}")

    if total_pages > 1:
        media_type = entries[0].media.type if entries else "anime"
        if page > 0:
            builder.button(text="◀️", callback_data=f"library_page:{media_type}:{status}:{page - 1}")
        builder.button(text=f"{page + 1}/{total_pages}", callback_data="library_noop")
        if page + 1 < total_pages:
            builder.button(text="▶️", callback_data=f"library_page:{media_type}:{status}:{page + 1}")

    builder.button(text="🏠 Главное меню", callback_data="menu")
    builder.adjust(1)
    return builder.as_markup()


def library_sections() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🎬 Аниме", callback_data="library:anime")
    builder.button(text="📚 Манга", callback_data="library:manga")
    builder.button(text="🏠 Главное меню", callback_data="menu")
    builder.adjust(2, 1)
    return builder.as_markup()


def library_status_keyboard(media_type: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    statuses = [
        ("📋 Всё", "all"),
        ("🟢 Завершено", "completed"),
        ("🔵 Смотрю / Читаю", "watching"),
        ("🟡 Хочу", "planning"),
        ("⚪ На паузе", "paused"),
        ("🔴 Брошено", "dropped"),
    ]
    for text, status in statuses:
        builder.button(text=text, callback_data=f"library_filter:{media_type}:{status}:0")
    builder.button(text="◀️ Разделы", callback_data="library")
    builder.adjust(1)
    return builder.as_markup()


async def get_library_page(
    session: AsyncSession,
    user_id: int,
    media_type: str,
    status: str | None,
    page: int,
    per_page: int = 8,
) -> tuple[list[UserMedia], int]:
    query = (
        select(UserMedia)
        .join(Media)
        .options(selectinload(UserMedia.media))
        .where(UserMedia.user_id == user_id, Media.type == media_type)
        .order_by(UserMedia.updated_at.desc())
    )
    count_query = (
        select(func.count(UserMedia.id))
        .join(Media)
        .where(UserMedia.user_id == user_id, Media.type == media_type)
    )

    if status:
        query = query.where(UserMedia.status == status)
        count_query = count_query.where(UserMedia.status == status)

    total = (await session.execute(count_query)).scalar_one()
    total_pages = max(1, (total + per_page - 1) // per_page)

    result = await session.execute(query.offset(page * per_page).limit(per_page))
    return list(result.scalars().all()), total_pages
