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
