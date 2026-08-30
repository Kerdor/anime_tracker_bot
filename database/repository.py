from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

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
            description=data.get("description"),
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


async def get_library(
    session: AsyncSession,
    user_id: int,
    media_type: str,
    status: str | None = None,
    page: int = 0,
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


async def get_library_entry(
    session: AsyncSession,
    user_id: int,
    mal_id: int,
) -> UserMedia | None:
    result = await session.execute(
        select(UserMedia)
        .join(Media)
        .options(selectinload(UserMedia.media))
        .where(UserMedia.user_id == user_id, Media.mal_id == mal_id)
    )
    return result.scalar_one_or_none()


async def update_status(
    session: AsyncSession,
    entry: UserMedia,
    status: str,
) -> UserMedia:
    entry.status = status
    await session.commit()
    await session.refresh(entry)
    return entry


async def update_score(
    session: AsyncSession,
    entry: UserMedia,
    score: int,
) -> UserMedia:
    entry.score = score
    await session.commit()
    await session.refresh(entry)
    return entry


async def remove_from_library(session: AsyncSession, entry: UserMedia) -> None:
    await session.delete(entry)
    await session.commit()
