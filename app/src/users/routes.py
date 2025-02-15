import logging
from typing import TYPE_CHECKING, List

import uvicorn
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Security, status
from fastapi.encoders import jsonable_encoder
from fastapi_limiter.depends import RateLimiter
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from src.authorization.service import authorization_service
from src.configuration.db import get_db
from src.configuration.settings import settings
from src.exceptions.exceptions import RETURN_MSG
from src.media.repository import media_repository
from src.roles.repository import roles_repository
from src.services.cache import Cache
from src.services.email import email_service
from src.users.models import User
from src.users.repository import users_repository
from src.users.schemas import UserBase, UserCreate, UserPasswordUpdate, UserResponse, UserUpdate

if TYPE_CHECKING:
    from src.media.models import MediaAsset
    from src.roles.models import Role

logger = logging.getLogger(uvicorn.logging.__name__)
router = APIRouter(prefix=settings.users_prefix, tags=["users"])
users_router_cache: Cache = Cache(owner=router, all_prefix="users", ttl=settings.default_cache_ttl)


@router.post("/", response_model=List[UserResponse], status_code=status.HTTP_201_CREATED,
             description=settings.rate_limiter_description, dependencies=[Depends(RateLimiter(
                 times=settings.rate_limiter_times,
                 seconds=settings.rate_limiter_seconds))])
async def create_users(models: List[UserCreate], db: AsyncSession = Depends(get_db)) -> List[UserResponse]:
    """Creates new users. Returns a list of created users"""
    users: List[UserResponse] = []
    try:
        for model in models:
            user = await users_repository.create_user(model=model, db=db)
            if model.role and model.role.name and model.role.domain:
                role: Role = await roles_repository.read_role(model=model.role, db=db)
                user = await users_repository.assign_role_to_user(user=user, role=role, db=db)
            if model.photo and model.photo.id:
                photo: MediaAsset = await media_repository.read_media_asset(media_asset_id=model.photo.id, db=db)
                user = await users_repository.assign_photo_to_user(user=user, photo=photo, db=db)
            if user:
                users.append(user)
    except ValidationError as err:
        raise HTTPException(detail=jsonable_encoder(err.errors()), status_code=status.HTTP_400_BAD_REQUEST)
    except IntegrityError as err:
        raise HTTPException(detail=jsonable_encoder(err), status_code=status.HTTP_409_CONFLICT)

    await users_router_cache.invalidate_all_keys()
    return users


@router.get("/",  response_model=List[UserResponse])
async def read_users(
    email: str = Query(default=None),
    domain: str = Query(default=None),
    db: AsyncSession = Depends(get_db),
    _current_user: User = Security(authorization_service.authorize_user, scopes=["user:read"]),
) -> List[UserResponse]:
    """Retrieves all users with optional filtering. Returns a list of users"""
    cache_key = users_router_cache.get_all_records_cache_key_with_params(
        email,
        domain,
    )
    users: List[UserResponse] = await users_router_cache.get(key=cache_key)
    if not users:
        users = await users_repository.read_users(email=email, domain=domain, db=db)
        users = [UserResponse.model_validate(user) for user in users]
        if users:
            await users_router_cache.set(key=cache_key, value=users)
    if not users:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=RETURN_MSG.user_not_found % "")
    return users


@router.patch("/{domain}/{email}", response_model=UserResponse, status_code=status.HTTP_200_OK,
              description=settings.rate_limiter_description, dependencies=[Depends(RateLimiter(
                  times=settings.rate_limiter_times, seconds=settings.rate_limiter_seconds))])
async def update_user(
    domain: str,
    email: str,
    body: UserUpdate,
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    """Updates user data. Returns the updated user"""
    user: User = None
    try:
        user_model = UserBase(email=email, domain=domain)
        user = await users_repository.read_user(model=user_model, db=db)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=RETURN_MSG.user_not_found % email)
        user = await users_repository.update_user(user=user, new_data=body, db=db)
        if body.role and body.role.name and body.role.domain:
            role: Role = await roles_repository.read_role(model=body.role, db=db)
            user = await users_repository.assign_role_to_user(user=user, role=role, db=db)
        if body.photo and body.photo.id:
            photo: MediaAsset = await media_repository.read_media_asset(media_asset_id=body.photo.id, db=db)
            user = await users_repository.assign_photo_to_user(user=user, photo=photo, db=db)
    except ValidationError as err:
        raise HTTPException(detail=jsonable_encoder(err.errors()), status_code=status.HTTP_400_BAD_REQUEST)
    await users_router_cache.invalidate_all_keys()
    return user


@router.patch("/password/{domain}/{email}", response_model=UserResponse, status_code=status.HTTP_200_OK,
              description=settings.rate_limiter_description, dependencies=[Depends(RateLimiter(
                  times=settings.rate_limiter_times, seconds=settings.rate_limiter_seconds))])
async def change_user_password(
    domain: str,
    email: str,
    update: UserPasswordUpdate,
    background_tasks: BackgroundTasks,
    language: str = "UA",
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    """Change user password if the "entered password" matches the current user password and "new password" is correct.
    Returns updated user
    """
    try:
        user_model: UserBase = UserBase(email=email, domain=domain)
        user: User = await users_repository.read_user(model=user_model, db=db)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=RETURN_MSG.user_not_found % email)

        user = await users_repository.update_password(user=user, update=update, db=db)
        await users_router_cache.invalidate_all_keys()
        template_body = {"url": settings.url_login, "first_name": user.first_name, "last_name": user.last_name}
        background_tasks.add_task(email_service.send_email,
                                  email=user.email,
                                  template_body=template_body,
                                  template_name=email_service.EmailTemplate.PASS_CHANGED,
                                  language=language)
        return user # noqa:TRY300
    except ValidationError as err:
        raise HTTPException(detail=jsonable_encoder(err.errors()), status_code=status.HTTP_400_BAD_REQUEST)
    except ValueError:
        raise HTTPException(detail=RETURN_MSG.pwd_not_match,
                            status_code=status.HTTP_400_BAD_REQUEST)


@router.delete("/", status_code=status.HTTP_204_NO_CONTENT,
               description=settings.rate_limiter_description,
               dependencies=[Depends(RateLimiter(
                   times=settings.rate_limiter_times,
                   seconds=settings.rate_limiter_seconds))])
async def delete_users(models: List[UserBase], db: AsyncSession = Depends(get_db)) -> None:
    """Deletes users"""
    users_to_delete = []
    for model in models:
        user = await users_repository.read_user(model=model, db=db)
        if user:
            users_to_delete.append(user)

    if not users_to_delete:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=RETURN_MSG.user_not_found % "")

    for user_to_delete in users_to_delete:
        await users_repository.delete_user(user=user_to_delete, db=db)
    await users_router_cache.invalidate_all_keys()
