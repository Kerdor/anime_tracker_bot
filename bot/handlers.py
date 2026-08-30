from aiogram import F, Router
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from aiogram.utils.markdown import hbold

from bot.keyboards import (
    library_actions,
    library_sections,
    main_menu,
    media_keyboard,
    media_type_menu,
    rating_keyboard,
    search_results_keyboard,
    status_keyboard,
)
from bot.library import get_library_page, library_keyboard, library_status_keyboard
from database.repository import (
    add_to_library,
    get_library_entry,
    get_media,
    get_or_create_user,
    remove_from_library,
    save_media,
    update_score,
    update_status,
)
from database.session import SessionLocal
from providers.aggregator import MediaAggregator

router = Router()


class SearchState(StatesGroup):
    media_type = State()
    query = State()


STATUS_NAMES = {
    "planning": "🟡 Хочу",
    "watching": "🔵 Смотрю / Читаю",
    "completed": "🟢 Завершено",
    "paused": "⚪ На паузе",
    "dropped": "🔴 Брошено",
}


def media_to_item(media) -> dict:
    return {
        "media_id": media.id,
        "type": media.type,
        "title": media.title,
        "title_original": media.title_original,
        "description": media.description,
        "image_url": media.image_url,
        "score": media.score,
        "year": media.year,
        "status": media.status,
        "genres": [genre.name for genre in media.genres],
    }


def media_card_text(item: dict) -> str:
    title = item["title"]
    original = item.get("title_original")
    score = f"⭐ {item['score']}" if item.get("score") is not None else "⭐ —"
    year = item.get("year") or "—"
    genres = ", ".join(item.get("genres", [])) or "—"
    description = item.get("description") or "Описание отсутствует."

    if len(description) > 1000:
        description = description[:997] + "..."

    lines = [hbold(title)]
    if original and original != title:
        lines.append(original)
    lines.extend(["", f"📅 {year}  •  {score}"])

    if item["type"] == "anime":
        lines.append("🎬 Эпизоды: —")
    else:
        lines.append("📖 Главы: —  •  Томов: —")

    lines.extend([
        f"🏷 Жанры: {genres}",
        "",
        description,
    ])

    return "\n".join(lines)


async def send_media_card(message: Message, item: dict, reply_markup=None) -> None:
    text = media_card_text(item)
    image_url = item.get("image_url")
    if image_url:
        await message.answer_photo(
            photo=image_url,
            caption=text,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML,
        )
    else:
        await message.answer(text, reply_markup=reply_markup, parse_mode=ParseMode.HTML)


@router.message(CommandStart())
async def start_handler(message: Message) -> None:
    async with SessionLocal() as session:
        await get_or_create_user(session, message.from_user.id, message.from_user.username, message.from_user.first_name)

    await message.answer(
        "👋 Привет!\n\nЗдесь ты сможешь вести свою библиотеку аниме, манги и других произведений.",
        reply_markup=main_menu(),
    )


@router.callback_query(F.data == "menu")
async def menu_handler(callback: CallbackQuery) -> None:
    await callback.message.edit_text("🏠 Главное меню", reply_markup=main_menu())
    await callback.answer()


@router.callback_query(F.data == "library")
async def library_handler(callback: CallbackQuery) -> None:
    await callback.message.edit_text("📚 Моя библиотека\n\nВыбери раздел:", reply_markup=library_sections())
    await callback.answer()


@router.callback_query(F.data.startswith("library:"))
async def library_type_handler(callback: CallbackQuery) -> None:
    media_type = callback.data.split(":", 1)[1]
    title = "🎬 Аниме" if media_type == "anime" else "📚 Манга"
    await callback.message.edit_text(f"{title}\n\nВыбери статус:", reply_markup=library_status_keyboard(media_type))
    await callback.answer()


@router.callback_query(F.data.startswith("library_filter:"))
async def library_filter_handler(callback: CallbackQuery) -> None:
    _, media_type, status, page = callback.data.split(":")
    status_filter = None if status == "all" else status
    page = int(page)

    async with SessionLocal() as session:
        user = await get_or_create_user(session, callback.from_user.id, callback.from_user.username, callback.from_user.first_name)
        entries, total_pages = await get_library_page(session, user.id, media_type, status_filter, page)

    title = "🎬 Аниме" if media_type == "anime" else "📚 Манга"
    if not entries:
        text = f"{title}\n\nСтатус: {STATUS_NAMES.get(status, '📋 Все')}\n\nЗдесь пока ничего нет."
        await callback.message.edit_text(text, reply_markup=library_status_keyboard(media_type))
        await callback.answer()
        return

    lines = [f"{title}", f"Статус: {STATUS_NAMES.get(status, '📋 Все')}", ""]
    for index, entry in enumerate(entries, page * 8 + 1):
        score = f"⭐ {entry.score}" if entry.score is not None else ""
        lines.append(f"{index}. {entry.media.title} {score}")

    await callback.message.edit_text("\n".join(lines), reply_markup=library_keyboard(entries, page, total_pages, status))
    await callback.answer()


@router.callback_query(F.data.startswith("library_page:"))
async def library_page_handler(callback: CallbackQuery) -> None:
    _, media_type, status, page = callback.data.split(":")
    status_filter = None if status == "all" else status
    page = int(page)

    async with SessionLocal() as session:
        user = await get_or_create_user(session, callback.from_user.id, callback.from_user.username, callback.from_user.first_name)
        entries, total_pages = await get_library_page(session, user.id, media_type, status_filter, page)

    title = "🎬 Аниме" if media_type == "anime" else "📚 Манга"
    lines = [f"{title}", f"Страница: {page + 1}/{total_pages}", ""]
    for index, entry in enumerate(entries, page * 8 + 1):
        score = f"⭐ {entry.score}" if entry.score is not None else ""
        lines.append(f"{index}. {entry.media.title} {score}")

    await callback.message.edit_text("\n".join(lines), reply_markup=library_keyboard(entries, page, total_pages, status))
    await callback.answer()


@router.callback_query(F.data == "library_noop")
async def library_noop_handler(callback: CallbackQuery) -> None:
    await callback.answer()


@router.callback_query(F.data.startswith("library_media:"))
async def library_media_handler(callback: CallbackQuery) -> None:
    media_id = int(callback.data.split(":", 1)[1])

    async with SessionLocal() as session:
        user = await get_or_create_user(session, callback.from_user.id, callback.from_user.username, callback.from_user.first_name)
        entry = await get_library_entry(session, user.id, media_id)

        if entry is None:
            await callback.answer("Произведение не найдено в библиотеке.", show_alert=True)
            return

        media = await get_media(session, media_id)

    if media is None:
        await callback.answer("Произведение не найдено.", show_alert=True)
        return

    item = media_to_item(media)
    await callback.message.delete()
    await send_media_card(callback.message, item, library_actions(media_id, entry.status, entry.score))
    await callback.answer()


@router.callback_query(F.data.startswith("edit_status:"))
async def edit_status_handler(callback: CallbackQuery) -> None:
    media_id = int(callback.data.split(":", 1)[1])
    await callback.message.edit_reply_markup(reply_markup=status_keyboard(media_id))
    await callback.answer()


@router.callback_query(F.data.startswith("rate:"))
async def rate_handler(callback: CallbackQuery) -> None:
    media_id = int(callback.data.split(":", 1)[1])
    await callback.message.edit_reply_markup(reply_markup=rating_keyboard(media_id))
    await callback.answer()


@router.callback_query(F.data.startswith("rating:"))
async def rating_handler(callback: CallbackQuery) -> None:
    _, media_id, score = callback.data.split(":")
    media_id = int(media_id)
    score = int(score)

    async with SessionLocal() as session:
        user = await get_or_create_user(session, callback.from_user.id, callback.from_user.username, callback.from_user.first_name)
        entry = await get_library_entry(session, user.id, media_id)
        if entry is None:
            await callback.answer("Произведение не найдено.", show_alert=True)
            return
        await update_score(session, entry, score)
        status = entry.status

    await callback.message.edit_reply_markup(reply_markup=library_actions(media_id, status, score))
    await callback.answer(f"Оценка {score}/10 сохранена!")


@router.callback_query(F.data.startswith("remove:"))
async def remove_handler(callback: CallbackQuery) -> None:
    media_id = int(callback.data.split(":", 1)[1])

    async with SessionLocal() as session:
        user = await get_or_create_user(session, callback.from_user.id, callback.from_user.username, callback.from_user.first_name)
        entry = await get_library_entry(session, user.id, media_id)
        if entry is None:
            await callback.answer("Произведение уже удалено.", show_alert=True)
            return
        await remove_from_library(session, entry)

    await callback.message.delete()
    await callback.message.answer("🗑 Произведение удалено из библиотеки.", reply_markup=main_menu())
    await callback.answer("Удалено")


@router.callback_query(F.data == "search")
async def search_handler(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.edit_text("🔎 Что будем искать?", reply_markup=media_type_menu())
    await callback.answer()


@router.callback_query(F.data.startswith("search_type:"))
async def search_type_handler(callback: CallbackQuery, state: FSMContext) -> None:
    media_type = callback.data.split(":", 1)[1]
    await state.update_data(media_type=media_type)
    await state.set_state(SearchState.query)
    title = "аниме" if media_type == "anime" else "мангу"
    await callback.message.edit_text(f"🔎 Введи название {title}:")
    await callback.answer()


@router.message(SearchState.query)
async def search_query_handler(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    media_type = data["media_type"]
    query = (message.text or "").strip()

    if not query:
        await message.answer("Введи название произведения.")
        return

    aggregator = MediaAggregator()
    try:
        results = await aggregator.search(query, media_type)
    except Exception:
        await message.answer("Не удалось выполнить поиск. Попробуй ещё раз позже.")
        return
    finally:
        await aggregator.close()

    if not results:
        await message.answer("Ничего не найдено. Попробуй другое название.")
        return

    try:
        async with SessionLocal() as session:
            for item in results:
                media = await save_media(session, item)
                item["media_id"] = media.id
    except Exception:
        await message.answer("Не удалось сохранить результаты поиска. Попробуй ещё раз позже.")
        return

    results = results[:10]
    lines = ["🔎 Результаты поиска:\n"]
    for index, item in enumerate(results, 1):
        score = f"⭐ {item['score']}" if item.get("score") is not None else "⭐ —"
        year = item.get("year") or "—"
        lines.append(f"{index}. {item['title']} ({year}) — {score}")

    await message.answer("\n".join(lines), reply_markup=search_results_keyboard(results))
    await state.clear()


@router.callback_query(F.data.startswith("media:"))
async def media_handler(callback: CallbackQuery) -> None:
    media_id = int(callback.data.split(":", 1)[1])

    async with SessionLocal() as session:
        media = await get_media(session, media_id)

    if media is None:
        await callback.answer("Произведение не найдено.", show_alert=True)
        return

    item = media_to_item(media)
    await callback.message.delete()
    await send_media_card(callback.message, item, media_keyboard(media_id))
    await callback.answer()


@router.callback_query(F.data.startswith("add:"))
async def add_handler(callback: CallbackQuery) -> None:
    media_id = int(callback.data.split(":", 1)[1])
    await callback.message.edit_reply_markup(reply_markup=status_keyboard(media_id))
    await callback.answer()


@router.callback_query(F.data.startswith("status:"))
async def status_handler(callback: CallbackQuery) -> None:
    _, media_id, status = callback.data.split(":")
    media_id = int(media_id)

    async with SessionLocal() as session:
        user = await get_or_create_user(session, callback.from_user.id, callback.from_user.username, callback.from_user.first_name)
        media = await get_media(session, media_id)
        if media is None:
            await callback.answer("Произведение не найдено.", show_alert=True)
            return
        entry = await add_to_library(session, user.id, media, status)

    await callback.message.edit_reply_markup(reply_markup=library_actions(media_id, status, entry.score))
    await callback.answer(f"Сохранено: {STATUS_NAMES[status]}")


@router.callback_query(F.data == "search_noop")
async def search_noop_handler(callback: CallbackQuery) -> None:
    await callback.answer()
