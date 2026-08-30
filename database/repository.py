from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from database.models import Genre, Media, MediaSource, User, UserMedia


async def get_or_create_user(session: AsyncSession, telegram_id: int, username: str | None, first_name: str | None) -> User:
    result = await session.execute(select(User).where(User.telegram_id == telegram_id))
    user = result.scalar_one_or_none()
    if user is None:
        user = User(telegram_id=telegram_id, username=username, first_name=first_name)
        session.add(user)
    else:
        user.username = username
        user.first_name = first_name
    await session.commit()
    await session.refresh(user)
    return user


async def get_media(session: AsyncSession, media_id: int) -> Media | None:
    result = await session.execute(
        select(Media)
        .options(selectinload(Media.sources), selectinload(Media.genres))
        .where(Media.id == media_id)
    )
    return result.scalar_one_or_none()


async def get_media_by_source(session: AsyncSession, source: str, source_id: str) -> Media | None:
    result = await session.execute(
        select(Media)
        .join(MediaSource)
        .options(selectinload(Media.sources), selectinload(Media.genres))
        .where(MediaSource.source == source, MediaSource.source_id == str(source_id))
    )
    return result.scalar_one_or_none()


async def save_media(session: AsyncSession, data: dict) -> Media:
    source = data.get("provider")
    source_id = data.get("provider_id")
    media = None

    if source and source_id:
        media = await get_media_by_source(session, source, str(source_id))

    if media is None:
        for provider, external_id in data.get("source_ids", {}).items():
            media = await get_media_by_source(session, provider, str(external_id))
            if media is not None:
                break

    if media is None:
        media = Media(
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
    else:
        media.title = data["title"]
        media.title_original = data.get("title_original") or media.title_original
        media.description = data.get("description") or media.description
        media.image_url = data.get("image_url") or media.image_url
        media.score = data.get("score") if data.get("score") is not None else media.score
        media.year = data.get("year") or media.year
        media.status = data.get("status") or media.status

    source_ids = dict(data.get("source_ids", {}))
    if source and source_id:
        source_ids[source] = str(source_id)

    existing_sources = {(item.source, item.source_id): item for item in media.sources}
    for provider, external_id in source_ids.items():
        external_id = str(external_id)
        key = (provider, external_id)
        if key not in existing_sources:
            session.add(MediaSource(media_id=media.id, source=provider, source_id=external_id))

    for name in data.get("genres", []):
        name = str(name).strip()
        if not name:
            continue
        result = await session.execute(select(Genre).where(Genre.name == name))
        genre = result.scalar_one_or_none()
        if genre is None:
            genre = Genre(name=name)
            session.add(genre)
            await session.flush()
        if genre not in media.genres:
            media.genres.append(genre)

    await session.commit()
    await session.refresh(media)
    return media


async def add_to_library(session: AsyncSession, user_id: int, media: Media, status: str = "planning") -> UserMedia:
    result = await session.execute(select(UserMedia).where(UserMedia.user_id == user_id, UserMedia.media_id == media.id))
    entry = result.scalar_one_or_none()
    if entry is None:
        entry = UserMedia(user_id=user_id, media_id=media.id, status=status)
        session.add(entry)
    else:
        entry.status = status
    await session.commit()
    await session.refresh(entry)
    return entry


async def get_library(session: AsyncSession, user_id: int, media_type: str, status: str | None = None, page: int = 0, per_page: int = 8) -> tuple[list[UserMedia], int]:
    query = select(UserMedia).join(Media).options(selectinload(UserMedia.media)).where(UserMedia.user_id == user_id, Media.type == media_type).order_by(UserMedia.updated_at.desc())
    count_query = select(func.count(UserMedia.id)).join(Media).where(UserMedia.user_id == user_id, Media.type == media_type)
    if status:
        query = query.where(UserMedia.status == status)
        count_query = count_query.where(UserMedia.status == status)
    total = (await session.execute(count_query)).scalar_one()
    total_pages = max(1, (total + per_page - 1) // per_page)
    result = await session.execute(query.offset(page * per_page).limit(per_page))
    return list(result.scalars().all()), total_pages


async def get_library_entry(session: AsyncSession, user_id: int, media_id: int) -> UserMedia | None:
    result = await session.execute(
        select(UserMedia)
        .options(selectinload(UserMedia.media).selectinload(Media.genres))
        .where(UserMedia.user_id == user_id, UserMedia.media_id == media_id)
    )
    return result.scalar_one_or_none()


async def update_status(session: AsyncSession, entry: UserMedia, status: str) -> UserMedia:
    entry.status = status
    await session.commit()
    await session.refresh(entry)
    return entry


async def update_score(session: AsyncSession, entry: UserMedia, score: int) -> UserMedia:
    entry.score = score
    await session.commit()
    await session.refresh(entry)
    return entry


async def remove_from_library(session: AsyncSession, entry: UserMedia) -> None:
    await session.delete(entry)
    await session.commit()


async def get_user_statistics(session: AsyncSession, user_id: int) -> dict:
    result = await session.execute(
        select(Media.type, UserMedia.status, func.count(UserMedia.id))
        .join(Media)
        .where(UserMedia.user_id == user_id)
        .group_by(Media.type, UserMedia.status)
    )

    by_type_status: dict[str, dict[str, int]] = {}
    for media_type, status, count in result.all():
        by_type_status.setdefault(media_type, {})[status] = count

    result = await session.execute(
        select(func.count(UserMedia.id), func.avg(UserMedia.score))
        .where(UserMedia.user_id == user_id)
    )
    total, average_score = result.one()

    return {
        "total": total or 0,
        "average_score": round(float(average_score), 2) if average_score is not None else None,
        "by_type_status": by_type_status,
    }
