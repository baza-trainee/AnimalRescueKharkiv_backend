from datetime import datetime
import logging
import uuid
from typing import Annotated, List
from fastapi.encoders import jsonable_encoder
from fastapi.responses import StreamingResponse
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi_limiter.depends import RateLimiter
import uvicorn
from fastapi import APIRouter, Form, HTTPException, Depends, Path, Query, status, UploadFile, File
from src.configuration.db import get_db
from src.configuration.settings import settings
from src.media.models import MediaAsset, Blob
from src.media.schemas import MediaAssetInfo, MediaAssetResponse
from src.media.repository import media_repository

logger = logging.getLogger(uvicorn.logging.__name__)
router = APIRouter(prefix="/media", tags=["media"])

@router.get("/{media_id}")
async def read_media(media_id: uuid.UUID,
                        db: AsyncSession = Depends(get_db),
                        # current_user: User = Depends(auth_service.get_current_user),
                        # authorization: authorization_service = Depends(authorization_service(
                        #             [
                        #                 access_rule(Operation.read, [Role.user, Role.moderator, Role.admin])
                        #             ]
                        #         ).authorize)
                    ):
    """
    Retrieves a binary stream of a single media file by its unique identifier. Returns StreamingResponse containing the media file
    """

    media_asset = await media_repository.read_media_asset(media_asset_id=media_id, db=db)    
    if media_asset is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Media not found")
    # permissions = authorization.check_entity_permissions(photo.user)
    # if not permissions[0]:
    #     raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"You don't have permissions for {', '.join(permissions[1])} operation")
    media_stream = await media_repository.read_blob(blob_id=media_asset.blob_id, db=db)    
    if media_stream is None or not media_stream.seekable():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Media blob data not found")
    return StreamingResponse(content=media_stream, media_type=media_asset.content_type)


@router.get("/asset/{media_id}",  response_model=MediaAssetResponse,
            description=settings.rate_limiter_description,
            dependencies=[Depends(RateLimiter(times=settings.rate_limiter_times, seconds=settings.rate_limiter_seconds))])
async def read_media(media_id: uuid.UUID,
                        db: AsyncSession = Depends(get_db),
                        # current_user: User = Depends(auth_service.get_current_user),
                        # authorization: authorization_service = Depends(authorization_service(
                        #             [
                        #                 access_rule(Operation.read, [Role.user, Role.moderator, Role.admin])
                        #             ]
                        #         ).authorize)
                    ):
    """
    Retrieves a single media asset by its unique identifier. Returns media asset information
    """

    media_asset = await media_repository.read_media_asset(media_asset_id=media_id, db=db)    
    if media_asset is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Media not found")    
    return media_asset

@router.get("/asset/",  response_model=List[MediaAssetResponse],
            description=settings.rate_limiter_description,
            dependencies=[Depends(RateLimiter(times=settings.rate_limiter_times, seconds=settings.rate_limiter_seconds))])
async def read_media(from_date: datetime =  Query(default=None, description="Filter media assets by FROM date"),
                        to_date: datetime =  Query(default=None, description="Filter media assets by TO date"),
                        media_type: str =  Query(default=None, description="Filter media assets by media type, e.g. 'image/jpeg'"),
                        extension: str =  Query(default=None, description="Filter media assets by extension, e.g. 'jpg'"),
                        skip: int = Query(default=0, ge=0, description="Records to skip in response"),
                        limit: int = Query(default=20, ge=1, le=50, description="Records per response to show"),
                        db: AsyncSession = Depends(get_db),
                        # current_user: User = Depends(auth_service.get_current_user),
                        # authorization: authorization_service = Depends(authorization_service(
                        #             [
                        #                 access_rule(Operation.read, [Role.user, Role.moderator, Role.admin])
                        #             ]
                        #         ).authorize)
                    ):
    """
    Retrieves multiple media assets optionally filtered by date, type and extention, support paging via skip & limit. Returns collection of media asset information objects
    """

    media_assets = await media_repository.read_media_assets(from_date=from_date, to_date=to_date, media_type=media_type, extension = extension, skip=skip, limit=limit, db=db)    
    if not media_assets:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No media assets found")    
    return media_assets


@router.post("/", response_model=MediaAssetResponse, status_code=status.HTTP_201_CREATED,
            description=settings.rate_limiter_description,
            dependencies=[Depends(RateLimiter(times=settings.rate_limiter_times, seconds=settings.rate_limiter_seconds))])
async def create_media_asset(file: UploadFile = File(),
                        db: AsyncSession = Depends(get_db),
                        # current_user: User = Depends(auth_service.get_current_user),
                        # authorization: authorization_service = Depends(authorization_service(
                        #             [                                        
                        #                 access_rule(Operation.create, [Role.user, Role.moderator, Role.admin])
                        #             ]
                        #         ).authorize)
                    ):
    """
    Creates a new media asset from the uploaded media file. Returns media response object
    """

    media_asset = None
    try:
        # permissions = authorization.check_entity_permissions()
        # if not permissions[0]:
        #     raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"You don't have permissions for {', '.join(permissions[1])} operation")
        media_asset = await media_repository.create_media_asset(file=file, db=db)        
    except ValidationError as err:
        raise HTTPException(detail=jsonable_encoder(err.errors()), status_code=status.HTTP_400_BAD_REQUEST)       
    return media_asset


@router.delete("/{photo_id}", status_code=status.HTTP_204_NO_CONTENT,
            description=settings.rate_limiter_description,
            dependencies=[Depends(RateLimiter(times=settings.rate_limiter_times, seconds=settings.rate_limiter_seconds))])
async def remove_media_asset(media_id: uuid.UUID,
                        db: AsyncSession = Depends(get_db),
                        # current_user: User = Depends(auth_service.get_current_user),
                        # authorization: authorization_service = Depends(authorization_service(
                        #             [
                        #                 access_rule(Operation.read, [Role.user, Role.moderator, Role.admin]),
                        #                 access_rule(Operation.delete, [Role.admin])
                        #             ]
                        #         ).authorize)
                    ):
    media_asset = await media_repository.read_media_asset(media_asset_id=media_id, db=db)    
    if media_asset is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Photo not found")
    # permissions = authorization.check_entity_permissions(photo.user)
    # if not permissions[0]:
    #     raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"You don't have permissions for {', '.join(permissions[1])} operation")
    media_asset = await media_repository.remove_media_asset(media_asset=media_asset, db=db)
    return None