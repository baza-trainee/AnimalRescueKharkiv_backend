import logging
from typing import TYPE_CHECKING, List

import uvicorn
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.encoders import jsonable_encoder
from fastapi_limiter.depends import RateLimiter
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from src.configuration.db import get_db
from src.configuration.settings import settings
from src.users.repository import users_repository
from src.users.schemas import UserBase, UserCreate, UserResponse, UserUpdate

if TYPE_CHECKING:
    from src.users.models import User

logger = logging.getLogger(uvicorn.logging.__name__)
router = APIRouter(prefix=settings.users_prefix, tags=["users"])


@router.post("/", response_model=List[UserResponse], status_code=status.HTTP_201_CREATED,
             description=settings.rate_limiter_description, dependencies=[Depends(RateLimiter(
                 times=settings.rate_limiter_times,
                 seconds=settings.rate_limiter_seconds))])
async def create_users(models: List[UserCreate], db: AsyncSession = Depends(get_db)) -> List[UserResponse]:
    """Creates new users. Returns list of created users"""
    users: List[UserResponse] = []
    try:
        for model in models:
            user = await users_repository.create_user(model=model, db=db)
            if user:
                users.append(user)
    except ValidationError as err:
        raise HTTPException(detail=jsonable_encoder(err.errors()), status_code=status.HTTP_400_BAD_REQUEST)
    except IntegrityError as err:
        raise HTTPException(detail=jsonable_encoder(err), status_code=status.HTTP_409_CONFLICT)

    return users


@router.get("/",  response_model=List[UserResponse])
async def read_users(
    username: str = Query(default=None),
    domain: str = Query(default=None),
    db: AsyncSession = Depends(get_db),
) -> List[UserResponse]:
    """Retrieves all users with optional filtering. Returns list of users"""
    users: List[UserResponse] = await users_repository.read_users(username=username, domain=domain, db=db)
    if not users:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No users found")
    return users


@router.patch("/{domain}/{username}", response_model=UserResponse, status_code=status.HTTP_200_OK,
              description=settings.rate_limiter_description, dependencies=[Depends(RateLimiter(
                  times=settings.rate_limiter_times, seconds=settings.rate_limiter_seconds))])
async def update_user(
    domain: str,
    username: str,
    body: UserUpdate,
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    """Updates user's data. Returns updated user"""
    user: User = None
    try:
        user_model = UserBase(username=username, domain=domain)
        user = await users_repository.read_user(model=user_model, db=db)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        user = await users_repository.update_user(user=user, new_data=body, db=db)

    except ValidationError as err:
        raise HTTPException(detail=jsonable_encoder(err.errors()), status_code=status.HTTP_400_BAD_REQUEST)

    return user


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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Users not found")

    for user_to_delete in users_to_delete:
        await users_repository.delete_user(user=user_to_delete, db=db)
