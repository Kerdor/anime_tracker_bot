from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from bot.keyboards import (
    main_menu,
    media_keyboard,
    media_type_menu,
    search_results_keyboard,
    status_keyboard,
)
from bot.library import get_library_page, library_keyboard, library_sections, library_status_keyboard
from database.repository import add_to_library, get_or_create_user, save_media
from database.session import SessionLocal
from providers.jikan import JikanClient

router = Router()


class SearchState(StatesGroup):
    media_type = State()
    query = State()


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
    await callback.message.edit_text(
        f"{title}\n\nВыбери статус:",
        reply_markup=library_status_keyboard(media_type),
    )
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
    status_names = {
        "all": "Все",
        "planning": "Хочу",
        "watching": "Смотрю / Читаю",
        "completed": "Завершено",
        "paused": "На паузе",
        "dropped": "Брошено",
    }

    if not entries:
        text = f"{title}\n\nСтатус: {status_names[status]}\n\nЗдесь пока ничего нет."
    else:
        lines = [f"{title}", f"Статус: {status_names[status]}", ""]
        for index, entry in enumerate(entries, page * 8 + 1):
            score = f"⭐ {entry.score}" if entry.score is not None else ""
            lines.append(f"{index}. {entry.media.title} {score}")
        text = "\n".join(lines)

    await callback.message.edit_text(
        text,
        reply_markup=library_keyboard(entries, page, total_pages, status),
    )
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

    await callback.message.edit_text(
        "\n".join(lines),
        reply_markup=library_keyboard(entries, page, total_pages, status),
    )
    await callback.answer()


@router.callback_query(F.data == "library_noop")
async def library_noop_handler(callback: CallbackQuery) -> None:
    await callback.answer()


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

    client = JikanClient()
    try:
        results = await client.search(query, media_type)
    except Exception:
        await message.answer("Не удалось выполнить поиск. Попробуй ещё раз позже.")
        return
    finally:
        await client.close()

    if not results:
        await message.answer("Ничего не найдено. Попробуй другое название.")
        return

    lines = ["🔎 Результаты поиска:\n"]
    for index, item in enumerate(results, 1):
        score = f"⭐ {item['score']}" if item["score"] is not None else "⭐ —"
        year = item["year"] or "—"
        lines.append(f"{index}. {item['title']} ({year}) — {score}")

    await message.answer("\n".join(lines), reply_markup=search_results_keyboard(results))
    await state.clear()


@router.callback_query(F.data.startswith("media:"))
async def media_handler(callback: CallbackQuery) -> None:
    _, media_type, mal_id = callback.data.split(":")
    client = JikanClient()
    try:
        results = await client.search(str(mal_id), media_type)
        item = next((item for item in results if item["mal_id"] == int(mal_id)), None)
    except Exception:
        item = None
    finally:
        await client.close()

    if item is None:
        await callback.answer("Не удалось загрузить произведение.", show_alert=True)
        return

    score = f"⭐ {item['score']}" if item["score"] is not None else "⭐ —"
    year = item["year"] or "—"
    text = f"<b>{item['title']}</b>\n\n{year} • {score}\n\nMAL ID: {item['mal_id']}"
    await callback.message.edit_text(text, reply_markup=media_keyboard(media_type, int(mal_id)))
    await callback.answer()


@router.callback_query(F.data.startswith("add:"))
async def add_handler(callback: CallbackQuery) -> None:
    _, media_type, mal_id = callback.data.split(":")
    await callback.message.edit_text("📚 Выбери статус произведения:", reply_markup=status_keyboard(media_type, int(mal_id)))
    await callback.answer()


@router.callback_query(F.data.startswith("status:"))
async def status_handler(callback: CallbackQuery) -> None:
    _, media_type, mal_id, status = callback.data.split(":")
    client = JikanClient()
    try:
        results = await client.search(str(mal_id), media_type)
        item = next((item for item in results if item["mal_id"] == int(mal_id)), None)
    except Exception:
        item = None
    finally:
        await client.close()

    if item is None:
        await callback.answer("Не удалось сохранить произведение.", show_alert=True)
        return

    async with SessionLocal() as session:
        user = await get_or_create_user(session, callback.from_user.id, callback.from_user.username, callback.from_user.first_name)
        media = await save_media(session, item)
        await add_to_library(session, user.id, media, status)

    status_names = {
        "planning": "🟡 Хочу",
        "watching": "🔵 Смотрю / Читаю",
        "completed": "🟢 Завершено",
        "paused": "⚪ На паузе",
        "dropped": "🔴 Брошено",
    }

    await callback.message.edit_text(
        f"✅ <b>{item['title']}</b> добавлено в библиотеку.\n\nСтатус: {status_names[status]}",
        reply_markup=main_menu(),
    )
    await callback.answer("Сохранено!")
