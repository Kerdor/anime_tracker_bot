from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Media, User, UserMedia


async def get_or_create_user(
    session: AsyncSession,
    telegram_id: int,
    username: str | None,
    first_name: str | None,
) -> User:
    result = await session.execute(select(User).where(User.telegram_id == telegram_id))
    user = result.scalar_one_or_none()

    if user is None:
        user = User(
            telegram_id=telegram_id,
            username=username,
            first_name=first_name,
        )
        session.add(user)
    else:
        user.username = username
        user.first_name = first_name

    await session.commit()
    await session.refresh(user)
    return user


async def get_media(session: AsyncSession, mal_id: int) -> Media | None:
    result = await session.execute(select(Media).where(Media.mal_id == mal_id))
    return result.scalar_one_or_none()


async def save_media(session: AsyncSession, data: dict) -> Media:
    media = await get_media(session, data["mal_id"])

    if media is None:
        media = Media(
            mal_id=data["mal_id"],
            type=data["type"],
            title=data["title"],
            title_original=data.get("title_original"),
            image_url=data.get("image_url"),
            score=data.get("score"),
            year=data.get("year"),
            status=data.get("status"),
        )
        session.add(media)
        await session.flush()

    return media


async def add_to_library(
    session: AsyncSession,
    user_id: int,
    media: Media,
    status: str = "planning",
) -> UserMedia:
    result = await session.execute(
        select(UserMedia).where(
            UserMedia.user_id == user_id,
            UserMedia.media_id == media.id,
        )
    )
    entry = result.scalar_one_or_none()

    if entry is None:
        entry = UserMedia(user_id=user_id, media_id=media.id, status=status)
        session.add(entry)
    else:
        entry.status = status

    await session.commit()
    await session.refresh(entry)
    return entry
