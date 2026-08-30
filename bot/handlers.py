from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.state import State, StatesGroup

from bot.keyboards import main_menu, media_type_menu

router = Router()


class SearchState(StatesGroup):
    media_type = State()
    query = State()


@router.message(CommandStart())
async def start_handler(message: Message) -> None:
    await message.answer(
        "👋 Привет!\n\nЗдесь ты сможешь вести свою библиотеку аниме, манги и других произведений.",
        reply_markup=main_menu(),
    )


@router.callback_query(F.data == "menu")
async def menu_handler(callback: CallbackQuery) -> None:
    await callback.message.edit_text(
        "🏠 Главное меню",
        reply_markup=main_menu(),
    )
    await callback.answer()


@router.callback_query(F.data == "search")
async def search_handler(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.edit_text(
        "🔎 Что будем искать?",
        reply_markup=media_type_menu(),
    )
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
    from providers.jikan import JikanClient

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

    await message.answer("\n".join(lines))
    await state.clear()
