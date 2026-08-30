from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


def main_menu() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🎬 Аниме", callback_data="section:anime")
    builder.button(text="📚 Манга", callback_data="section:manga")
    builder.button(text="🔎 Поиск", callback_data="search")
    builder.button(text="👤 Мой профиль", callback_data="profile")
    builder.button(text="📊 Статистика", callback_data="stats")
    builder.adjust(2, 2, 1)
    return builder.as_markup()


def media_type_menu() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🎬 Аниме", callback_data="search_type:anime")
    builder.button(text="📚 Манга", callback_data="search_type:manga")
    builder.button(text="◀️ Назад", callback_data="menu")
    builder.adjust(2, 1)
    return builder.as_markup()


def search_results_keyboard(results: list[dict]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for index, item in enumerate(results):
        builder.button(
            text=f"{index + 1}. {item['title'][:45]}",
            callback_data=f"media:{item['type']}:{item['mal_id']}",
        )
    builder.button(text="◀️ Главное меню", callback_data="menu")
    builder.adjust(1)
    return builder.as_markup()


def media_keyboard(media_type: str, mal_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="➕ Добавить в библиотеку", callback_data=f"add:{media_type}:{mal_id}")
    builder.button(text="◀️ К поиску", callback_data="search")
    builder.button(text="🏠 Главное меню", callback_data="menu")
    builder.adjust(1)
    return builder.as_markup()


def status_keyboard(media_type: str, mal_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    statuses = [
        ("🟡 Хочу", "planning"),
        ("🔵 Смотрю / Читаю", "watching"),
        ("🟢 Завершено", "completed"),
        ("⚪ На паузе", "paused"),
        ("🔴 Брошено", "dropped"),
    ]
    for text, status in statuses:
        builder.button(text=text, callback_data=f"status:{media_type}:{mal_id}:{status}")
    builder.adjust(1)
    return builder.as_markup()


def library_sections() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🎬 Аниме", callback_data="library:anime")
    builder.button(text="📚 Манга", callback_data="library:manga")
    builder.button(text="🏠 Главное меню", callback_data="menu")
    builder.adjust(2, 1)
    return builder.as_markup()
