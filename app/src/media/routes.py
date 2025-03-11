import logging
from datetime import datetime
from typing import TYPE_CHECKING, List

import uvicorn
from fastapi import APIRouter, Depends, File, HTTPException, Query, Security, UploadFile, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import Response
from fastapi_limiter.depends import RateLimiter
from pydantic import UUID4, ValidationError
from sqlalchemy.ext.asyncio import AsyncSession
from src.authorization.service import authorization_service
from src.configuration.db import get_db
from src.configuration.settings import settings
from src.exceptions.exceptions import RETURN_MSG
from src.media.repository import media_repository
from src.media.schemas import MediaAssetResponse
from src.services.cache import Cache
from src.users.models import User

if TYPE_CHECKING:
    from src.media.models import MediaAsset

logger = logging.getLogger(uvicorn.logging.__name__)
router = APIRouter(prefix=settings.media_prefix, tags=["media"])
media_router_cache: Cache = Cache(owner=router, all_prefix="media_assets", ttl=settings.default_cache_ttl)


@router.get(settings.media_assets_prefix,  response_model=List[MediaAssetResponse],
             description=settings.rate_limiter_get_description, dependencies=[Depends(RateLimiter(
                 times=settings.rate_limiter_get_times,
                 seconds=settings.rate_limiter_seconds))])
async def read_media_assets(from_date: datetime =  Query(default=None, description="Filter media assets by FROM date"),
                        to_date: datetime =  Query(default=None, description="Filter media assets by TO date"),
                        media_type: str =  Query(default=None,
                                                 description="Filter media assets by mime type, e.g. 'image/jpeg'"),
                        extension: str =  Query(default=None,
                                                description="Filter media assets by extension, e.g. 'jpg'"),
                        skip: int = Query(default=0, ge=0, description="Records to skip in response"),
                        limit: int = Query(default=20, ge=1, le=50, description="Records per response to show"),
                        db: AsyncSession = Depends(get_db),
                    ) -> List[MediaAssetResponse]:
    """Retrieves multiple media assets, allows multiple filters. Returns list of media asset information objects"""
    cache_key = media_router_cache.get_all_records_cache_key_with_params(
        from_date,
        to_date,
        media_type,
        extension,
        skip,
        limit,
    )
    media_assets: List[MediaAsset] = await media_router_cache.get(key=cache_key)
    if not media_assets:
        media_assets = await media_repository.read_media_assets(from_date=from_date,
                                                            to_date=to_date,
                                                            media_type=media_type,
                                                            extension = extension,
                                                            skip=skip,
                                                            limit=limit,
                                                            db=db)
        media_asset = [MediaAssetResponse.model_validate(media_asset) for media_asset in media_assets]
        if media_assets:
            await media_router_cache.set(key=cache_key, value=media_asset)
    if not media_assets:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=RETURN_MSG.media_not_found)
    return media_assets


@router.get(settings.media_assets_prefix + "/{media_id}",  response_model=MediaAssetResponse,
             description=settings.rate_limiter_get_description, dependencies=[Depends(RateLimiter(
                 times=settings.rate_limiter_get_times,
                 seconds=settings.rate_limiter_seconds))])
async def read_media_asset(media_id: UUID4,
                        db: AsyncSession = Depends(get_db),
                    ) -> MediaAssetResponse:
    """Retrieves a single media asset by its unique identifier. Returns media asset information"""
    cache_key = media_router_cache.get_cache_key(key=media_id)
    media_asset: MediaAsset = await media_router_cache.get(key=cache_key)
    if not media_asset:
        media_asset = await media_repository.read_media_asset(media_asset_id=media_id, db=db)
        media_asset = MediaAssetResponse.model_validate(media_asset)
        if media_asset:
            await media_router_cache.set(key=cache_key, value=media_asset)
    if media_asset is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=RETURN_MSG.media_not_found)
    return media_asset


@router.get("/{media_id}")
async def read_media(media_id: UUID4,
                        db: AsyncSession = Depends(get_db),
                    ) -> Response:
    """Retrieves media asset's binary stream by its unique identifier. Returns Response with media content"""
    cache_key = media_router_cache.get_cache_key(key=media_id)
    media_asset: MediaAsset = await media_router_cache.get(key=cache_key)
    if not media_asset:
        media_asset = await media_repository.read_media_asset(media_asset_id=media_id, db=db)
        media_asset = MediaAssetResponse.model_validate(media_asset)
        if media_asset:
            await media_router_cache.set(key=cache_key, value=media_asset)
    if media_asset is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=RETURN_MSG.media_not_found)
    media_bytes: bytes = await media_repository.read_blob(blob_id=media_asset.blob_id, db=db)
    if not media_bytes:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=RETURN_MSG.media_blob_not_found)
    return Response(content=media_bytes, media_type=media_asset.content_type)


@router.post(settings.media_assets_prefix, response_model=MediaAssetResponse, status_code=status.HTTP_201_CREATED,
            description=settings.rate_limiter_description,
            dependencies=[Depends(RateLimiter(times=settings.rate_limiter_times,
                                              seconds=settings.rate_limiter_seconds))])
async def create_media_asset(file: UploadFile = File(),
                        db: AsyncSession = Depends(get_db),
                        _current_user: User = Security(authorization_service.authorize_user,
                                                       scopes=["media:write"]),
                    ) -> MediaAssetResponse:
    """Creates a new media asset from the uploaded media file. Returns media response object"""
    media_asset: MediaAsset = None
    try:
        media_asset = await media_repository.create_media_asset(file=file, db=db)
    except ValidationError as err:
        raise HTTPException(detail=jsonable_encoder(err.errors()), status_code=status.HTTP_400_BAD_REQUEST)
    await media_router_cache.invalidate_all_keys()
    return media_asset


@router.delete(settings.media_assets_prefix + "/{meida_id}", status_code=status.HTTP_204_NO_CONTENT,
            description=settings.rate_limiter_description,
            dependencies=[Depends(RateLimiter(times=settings.rate_limiter_times,
                                              seconds=settings.rate_limiter_seconds))])
async def remove_media_asset(media_id: UUID4,
                        db: AsyncSession = Depends(get_db),
                        _current_user: User = Security(authorization_service.authorize_user,
                                                       scopes=["media:write"]),
                    ) -> None:
    """Deletes a media asset by its unique identifier"""
    media_asset: MediaAsset = await media_repository.read_media_asset(media_asset_id=media_id, db=db)
    if media_asset is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=RETURN_MSG.media_not_found)
    media_asset = await media_repository.remove_media_asset(media_asset=media_asset, db=db)
    cache_key = media_router_cache.get_cache_key(key=media_id)
    await media_router_cache.invalidate_key(key=cache_key)
    await media_router_cache.invalidate_all_keys()
