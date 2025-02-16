import logging
from datetime import timedelta
from typing import Dict

import uvicorn
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from fastapi_limiter.depends import RateLimiter
from pydantic import EmailStr
from pydantic_core import PydanticCustomError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session
from src.auth.extensions import OAuth2PasswordWithDomainRequestForm
from src.auth.managers import token_manager
from src.auth.models import SecurityToken, TokenType
from src.auth.schemas import EmailInvite, TokenBase, UserRegister
from src.auth.service import auth_service
from src.configuration.db import get_db
from src.configuration.settings import settings
from src.exceptions.exceptions import RETURN_MSG
from src.roles.repository import roles_repository
from src.roles.schemas import RoleBase
from src.services.email import email_service
from src.users.repository import users_repository
from src.users.schemas import UserBase, UserCreate, UserPasswordNew, UserResponse, UserUpdate

logger = logging.getLogger(uvicorn.logging.__name__)
router = APIRouter(prefix=settings.auth_prefix, tags=["auth"])


@router.post("/invite/{domain}", status_code=status.HTTP_202_ACCEPTED,
             description=settings.rate_limiter_description, dependencies=[Depends(RateLimiter(
                  times=settings.rate_limiter_times, seconds=settings.rate_limiter_seconds))])
async def invite_user(
    domain: str,
    body: EmailInvite,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, str]:
    """Sends an invitation email to a new user for registration"""
    try:
        user_model = UserBase(email=body.email, domain=domain)
        existing_user = await users_repository.read_user(model=user_model, db=db)
        if existing_user:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                            detail=RETURN_MSG.user_duplicate % (body.email, domain))
        role_model = RoleBase(name=body.role, domain=domain)
        existing_role = await roles_repository.read_role(model=role_model, db=db)
        if not existing_role:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=RETURN_MSG.role_not_found)
        title = existing_role.title or existing_role.name
        template_body = {"url": settings.url_register, "role": title.capitalize()}
        token = await auth_service.create_email_token(
            data={"sub": body.email, "domain": domain, "role": existing_role.name},
            token_type=TokenType.invitation,
            expiration_delta=timedelta(days=settings.invitation_token_expire_days),
            db=db,
        )
        background_tasks.add_task(email_service.send_email,
                                  email=body.email,
                                  template_body=template_body,
                                  template_name=email_service.EmailTemplate.INVITATION,
                                  token=token,
                                  language=body.language)
        logger.debug(f"Invitation token: {token}")
        return {"message": RETURN_MSG.email_sent % "Invitation"}
    except PydanticCustomError as e:
        logger.error(f"{e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail=e.message())
    except HTTPException as e:
        logger.error(f"{e}")
        raise
    except Exception as e:
        logger.error(f"Failed to send invitation email: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=RETURN_MSG.email_failed % "Invitation")


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED,
              description=settings.rate_limiter_description, dependencies=[Depends(RateLimiter(
                  times=settings.rate_limiter_times, seconds=settings.rate_limiter_seconds))])
async def register_user(
    user_register: UserRegister,
    token: str,
    background_tasks: BackgroundTasks,
    language: str = "UA",
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    """Registers a new user using the token from the invitation email"""
    try:
        token_record = await auth_service.validate_token(token=token, token_type=TokenType.invitation, db=db)
        token_payload = auth_service.get_payload_from_token(token=token_record.token)
        email = token_payload["sub"]
        if email != user_register.email.lower():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=RETURN_MSG.token_email_invalid)
        domain = token_payload["domain"]
        user_create = UserCreate(domain=domain,
                                 email=user_register.email,
                                 password=user_register.password,
                                 first_name=user_register.first_name,
                                 last_name=user_register.last_name,
                                 phone=user_register.phone)
        user = await users_repository.create_user(model=user_create, db=db)
        role = token_payload["role"]
        user_update = UserUpdate(role=RoleBase(domain=user.domain, name=role))
        user = await users_repository.update_user(user=user, new_data=user_update, db=db)
        template_body = {
            "url": settings.url_login,
            "email": user.email,
            "role": user.role.name,
            "first_name": user.first_name,
            "last_name": user.last_name,
            }
        background_tasks.add_task(email_service.send_email,
                                  email=user.email,
                                  template_body=template_body,
                                  template_name=email_service.EmailTemplate.WELCOME,
                                  language=language)
        await token_manager.delete_token(token=token_record, db=db)
        return user # noqa: TRY300
    except HTTPException as e:
        logger.error(f"{e}")
        raise
    except Exception as e:
        logger.error(f"Failed to register user: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=RETURN_MSG.user_reg_failed % e)


@router.post("/login", response_model=TokenBase, status_code=status.HTTP_200_OK,
             description=settings.rate_limiter_description, dependencies=[Depends(RateLimiter(
                  times=settings.rate_limiter_times, seconds=settings.rate_limiter_seconds))])
async def login(
    response: Response,
    body: OAuth2PasswordWithDomainRequestForm = Depends(),
    db: Session = Depends(get_db),
) -> TokenBase:
    """Logs in a user and returns a JWT token if credentials are valid"""
    user_model = UserBase(domain=body.domain, email=body.username)
    user = await users_repository.read_user(model=user_model, db=db)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=RETURN_MSG.user_not_found % body.username)
    if body.password != user.password:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=RETURN_MSG.pwd_invalid)

    refresh_token, refresh_id = await auth_service.create_refresh_token(user=user, db=db)
    access_token = await auth_service.create_access_token(user=user, refresh_id=refresh_id, db=db)

    logger.info(f"refersh_token={refresh_token}")
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=True,
        samesite="Strict",
        path="/auth",
    )

    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/logout", status_code=status.HTTP_200_OK,
             description=settings.rate_limiter_description, dependencies=[Depends(RateLimiter(
                  times=settings.rate_limiter_times, seconds=settings.rate_limiter_seconds))])
async def logout(
    token: SecurityToken = Depends(auth_service.get_access_token),
    db: Session = Depends(get_db),
) -> Dict[str, str]:
    """Logs out user, revokes access and refresh tokens"""
    try:
        result = await auth_service.revoke_auth_tokens(access_token=token.token, db=db)
        if result:
            return {"logout": RETURN_MSG.user_logout}
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=RETURN_MSG.user_logout_failed)
    except HTTPException as e:
        logger.error(f"{e}")
        raise
    except Exception:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=RETURN_MSG.user_logout_failed)


@router.post("/refresh", response_model=TokenBase, status_code=status.HTTP_200_OK)
async def refresh_access_token(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> TokenBase:
    """Refreshes an access token using the HTTP-only refresh token cookie"""
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=RETURN_MSG.token_refresh_missing)

    user, refresh_id = await auth_service.validate_user_from_refresh_token(refresh_token=refresh_token, db=db)
    access_token = await auth_service.create_access_token(user=user, refresh_id=refresh_id, db=db)

    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/password/forgot/{domain}/{email}", status_code=status.HTTP_202_ACCEPTED,
             description=settings.rate_limiter_description, dependencies=[Depends(RateLimiter(
                  times=settings.rate_limiter_times, seconds=settings.rate_limiter_seconds))])
async def forgot_pasword(
    domain: str,
    email: EmailStr,
    background_tasks: BackgroundTasks,
    language: str = "UA",
    db: AsyncSession = Depends(get_db),
) -> Dict[str, str]:
    """Sends a forgot-password email to the user"""
    try:
        user_model = UserBase(domain=domain, email=email)
        user = await users_repository.read_user(model=user_model, db=db)
        if user is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=RETURN_MSG.email_invalid)
        template_body = {"url": settings.url_reset_pwd, "first_name": user.first_name, "last_name": user.last_name}
        hashed_password = str(user.password.hash)
        token = await auth_service.create_email_token(
            data={"sub": email, "domain": domain, "key": hashed_password},
            token_type=TokenType.reset,
            expiration_delta=timedelta(minutes=settings.reset_password_expire_mins),
            db=db,
            user=user,
        )
        background_tasks.add_task(email_service.send_email,
                                  email=email,
                                  template_body=template_body,
                                  template_name=email_service.EmailTemplate.RESET_PASS,
                                  token=token,
                                  language=language)
        logger.debug(f"Reset token: {token}")
        return {"message": RETURN_MSG.email_sent % "Reset password"}
    except HTTPException as e:
        logger.error(f"{e}")
        raise
    except Exception as e:
        logger.error(f"Failed to send Reset password email: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=RETURN_MSG.email_failed % "Reset password")


@router.post("/password/reset", status_code=status.HTTP_200_OK,
             description=settings.rate_limiter_description, dependencies=[Depends(RateLimiter(
                  times=settings.rate_limiter_times, seconds=settings.rate_limiter_seconds))])
async def reset_pasword(
    token: str,
    user_password: UserPasswordNew,
    background_tasks: BackgroundTasks,
    language: str = "UA",
    db: AsyncSession = Depends(get_db),
) -> Dict[str, str]:
    """Resets password for the user from token"""
    try:
        token_record = await auth_service.validate_token(token=token, token_type=TokenType.reset, db=db)
        payload = auth_service.get_payload_from_token(token=token_record.token)
        user_model = UserBase(domain=payload["domain"], email=payload["sub"])
        user = await users_repository.read_user(model=user_model, db=db)
        if user is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=RETURN_MSG.user_not_found)
        if user.id != token_record.user.id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=RETURN_MSG.token_invalid)
        if payload["key"] != str(user.password.hash):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=RETURN_MSG.token_invalid)
        await users_repository.set_new_password(user=user, body=user_password, db=db)
        await token_manager.delete_token(token=token_record, db=db)
        template_body = {"url": settings.url_login, "first_name": user.first_name, "last_name": user.last_name}
        background_tasks.add_task(email_service.send_email,
                                  email=user.email,
                                  template_body=template_body,
                                  template_name=email_service.EmailTemplate.PASS_CHANGED,
                                  language=language)
        return {"message": RETURN_MSG.pwd_changed} # noqa: TRY300
    except HTTPException as e:
        logger.error(f"{e}")
        raise
    except Exception as e:
        logger.error(f"Failed to reset password: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=RETURN_MSG.pwd_change_failed)
