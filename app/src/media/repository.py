import base64
import io
import logging
import uuid
from datetime import datetime
from typing import BinaryIO

import uvicorn
from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from src.configuration.settings import settings
from src.media.cache import MediaCache
from src.media.models import Blob, MediaAsset
from src.singleton import SingletonMeta

logger = logging.getLogger(uvicorn.logging.__name__)

class MediaRepository (metaclass=SingletonMeta):
    def __init__(self, media_cache: MediaCache) -> None:
        """Initializes an instance of MediaRepository type"""
        self.__media_cache = media_cache

    async def save_blob(self, blob_data: BinaryIO, db: AsyncSession) -> uuid.UUID:
        """Saves binary/bytes data as a number of indexed chunks into database. Returns id of the saved binary blob"""
        blob_id: uuid.UUID = uuid.uuid4()
        data = base64.b64encode(blob_data.read())
        chunk_size = settings.blob_chunk_size_bytes
        bytes_array = bytearray(data)
        for blob_index, chunk_index in enumerate(range(0, len(bytes_array), chunk_size), start=0):
            chunk = bytes_array[chunk_index: chunk_size+chunk_index]
            blob = Blob(blob_id=blob_id, index=blob_index, data=bytes(chunk))
            db.add(blob)
        await db.commit()
        return blob_id

    async def read_blob(self, blob_id: uuid.UUID, db: AsyncSession) -> bytes | None:
        """Reads bytes chunks from database into a bytes stream. Returns the bytes stream."""
        bytes_data = self.__media_cache.get(blob_id)
        if not bytes_data:
            statement = select(Blob.data).filter_by(blob_id=blob_id).order_by(Blob.index)
            result = await db.execute(statement)
            chunks = result.scalars().all()
            data = bytearray()
            for chunk in chunks:
                data += bytearray(chunk)
            if data:
                bytes_data = base64.b64decode(bytes(data))
                self.__media_cache.add(blob_id, bytes_data)
        return bytes_data

    async def delete_blob(self, blob_id: uuid.UUID, db: AsyncSession) -> bool:
        """Deletes bytes chunks from database into. Returns boolean."""
        statement = select(Blob).filter_by(blob_id=blob_id).order_by(Blob.index)
        result = await db.execute(statement)
        blobs = result.scalars().all()
        if not blobs:
            return False
        try:
            for blob in blobs:
                await db.delete(blob)
            await db.commit()
            self.__media_cache.delete(blob_id)
        except Exception:
            return False
        return True


    async def create_media_asset(self, file: UploadFile, db: AsyncSession) -> MediaAsset:
        """Creates media asset enity. Returns the created media asset"""
        extension = file.filename.split(".")[-1]
        blob_id = await self.save_blob(blob_data=file.file, db=db)
        media_asset = MediaAsset(extension = extension,
            content_type = file.content_type,
            blob_id = blob_id,
        )
        db.add(media_asset)
        await db.commit()
        await db.refresh(media_asset)
        return media_asset

    async def read_media_asset(self, media_asset_id: uuid.UUID, db: AsyncSession) -> MediaAsset | None:
        """Reads a media asset enity by its id from database. Returns the retrieved media asset"""
        statement = select(MediaAsset).filter_by(id=media_asset_id)
        result = await db.execute(statement)
        return result.scalar_one_or_none()

    async def read_media_assets(self,
                                from_date: datetime,
                                to_date: datetime,
                                media_type: str,
                                extension: str,
                                skip: int,
                                limit: int,
                                db: AsyncSession) -> list[MediaAsset]:
        """Reads a media asset enity by its id from database. Returns the retrieved media asset"""
        statement = select(MediaAsset)
        if media_type:
            statement = statement.filter_by(content_type = media_type)
        if extension:
            statement = statement.filter_by(extension = extension)
        if from_date:
            statement = statement.filter(MediaAsset.created_at >= from_date)
        if to_date:
            statement = statement.filter(MediaAsset.created_at < to_date)
        statement = statement.offset(skip).limit(limit)
        result = await db.execute(statement)
        media_assets = result.scalars().all()
        return list(media_assets)

    async def remove_media_asset(self, media_asset: MediaAsset, db: AsyncSession) -> MediaAsset | None:
        """Deletes a media asset enity by its id from database. Returns the deleted media asset"""
        if media_asset:
            await self.delete_blob(media_asset.blob_id, db=db)
            await db.delete(media_asset)
            await db.commit()
        return media_asset


media_repository:MediaRepository = MediaRepository(MediaCache(media_cache_size=settings.media_cache_size_bytes,
                                              media_cache_record_limit=settings.media_cache_record_limit_bytes))
