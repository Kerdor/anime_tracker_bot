from aiogram import F, Router
from aiogram.types import CallbackQuery
from sqlalchemy import select

from bot.keyboards import main_menu
from database.models import Media, UserMedia
from database.repository import get_or_create_user, get_user_statistics
from database.session import SessionLocal

router = Router()

STATUS_NAMES = {
    "planning": "🟡 Хочу",
    "watching": "🔵 Смотрю / Читаю",
    "completed": "🟢 Завершено",
    "paused": "⚪ На паузе",
    "dropped": "🔴 Брошено",
}


def format_profile(user, stats: dict) -> str:
    by_type = stats["by_type_status"]
    anime = by_type.get("anime", {})
    manga = by_type.get("manga", {})
    average = stats["average_score"]
    average_text = f"⭐ {average}/10" if average is not None else "⭐ —"

    return (
        "👤 <b>Мой профиль</b>\n\n"
        f"Имя: <b>{user.first_name or 'Пользователь'}</b>\n"
        f"Username: @{user.username if user.username else '—'}\n\n"
        f"📚 Всего в библиотеке: <b>{stats['total']}</b>\n"
        f"🎬 Аниме: <b>{sum(anime.values())}</b>\n"
        f"📖 Манга: <b>{sum(manga.values())}</b>\n"
        f"{average_text} Средняя оценка\n\n"
        "<b>Аниме</b>\n"
        f"🟢 {anime.get('completed', 0)}  🔵 {anime.get('watching', 0)}  🟡 {anime.get('planning', 0)}\n"
        f"⚪ {anime.get('paused', 0)}  🔴 {anime.get('dropped', 0)}\n\n"
        "<b>Манга</b>\n"
        f"🟢 {manga.get('completed', 0)}  🔵 {manga.get('watching', 0)}  🟡 {manga.get('planning', 0)}\n"
        f"⚪ {manga.get('paused', 0)}  🔴 {manga.get('dropped', 0)}"
    )


@router.callback_query(F.data == "profile")
async def profile_handler(callback: CallbackQuery) -> None:
    async with SessionLocal() as session:
        user = await get_or_create_user(
            session,
            callback.from_user.id,
            callback.from_user.username,
            callback.from_user.first_name,
        )
        stats = await get_user_statistics(session, user.id)

    await callback.message.edit_text(format_profile(user, stats), reply_markup=main_menu())
    await callback.answer()


@router.callback_query(F.data == "stats")
async def stats_handler(callback: CallbackQuery) -> None:
    async with SessionLocal() as session:
        user = await get_or_create_user(
            session,
            callback.from_user.id,
            callback.from_user.username,
            callback.from_user.first_name,
        )
        stats = await get_user_statistics(session, user.id)

    by_type = stats["by_type_status"]
    anime = by_type.get("anime", {})
    manga = by_type.get("manga", {})
    average = stats["average_score"]
    average_text = f"⭐ {average}/10" if average is not None else "⭐ —"

    text = (
        "📊 <b>Статистика</b>\n\n"
        f"📚 Всего: <b>{stats['total']}</b>\n"
        f"🎬 Аниме: <b>{sum(anime.values())}</b>\n"
        f"📖 Манга: <b>{sum(manga.values())}</b>\n"
        f"{average_text}\n\n"
        "<b>По статусам</b>\n"
        f"🟢 Завершено: <b>{anime.get('completed', 0) + manga.get('completed', 0)}</b>\n"
        f"🔵 Смотрю / Читаю: <b>{anime.get('watching', 0) + manga.get('watching', 0)}</b>\n"
        f"🟡 Хочу: <b>{anime.get('planning', 0) + manga.get('planning', 0)}</b>\n"
        f"⚪ На паузе: <b>{anime.get('paused', 0) + manga.get('paused', 0)}</b>\n"
        f"🔴 Брошено: <b>{anime.get('dropped', 0) + manga.get('dropped', 0)}</b>"
    )

    await callback.message.edit_text(text, reply_markup=main_menu())
    await callback.answer()
