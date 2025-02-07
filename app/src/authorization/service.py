import logging
from typing import Annotated, List

import uvicorn
from fastapi import Depends, HTTPException, status
from fastapi.security import SecurityScopes
from pydantic import BaseModel
from pydantic.fields import FieldInfo
from src.auth.models import SecurityToken
from src.auth.service import auth_service
from src.configuration.settings import settings
from src.exceptions.exceptions import RETURN_MSG
from src.singleton import SingletonMeta
from src.users.models import User

logger = logging.getLogger(uvicorn.logging.__name__)


# Authorization_service.authorize
# Resolve context_user and scopes from access_token
# Compare permissions on the route against scopes in the access_token
# If at least single required permission(from the route) is not found on the user throw HTTP 403 exception

# Authorization_service.pre_authorize
# Resolve context_user and permissions from access_token
# Loop through all the model attributes
# For each attribute check if context_user has write access to it
# If user hass write acces add the attribtue to the list editable_attibutes


class Authorization(metaclass=SingletonMeta):
    async def authorize_user(
            self, scopes: SecurityScopes,
            current_security_token: SecurityToken = Depends(auth_service.get_access_token),
            ) -> User:
        """Authorizes user access. Returns the authorized user"""
        return await self.__do_authorize_user(scopes=scopes,
                                        current_security_token=current_security_token)

    async def authorize_user_for_section(
            self, section_name: str,
            scopes: SecurityScopes,
            current_security_token: SecurityToken = Depends(auth_service.get_access_token),
            ) -> User:
        """Authorizes user access for specific named data section. Returns the authorized user"""
        scopes.scopes.append(f"{section_name}:write")
        return await self.__do_authorize_user(scopes=scopes,
                                        current_security_token=current_security_token)

    async def __do_authorize_user(self, scopes: SecurityScopes, current_security_token: SecurityToken) -> User:
        permissions: List[str] = auth_service.get_permissions_from_token(current_security_token.token)
        required_permissions: set = set(scopes.scopes)
        user: User = current_security_token.user
        logger.info(current_security_token.token)
        logger.info(scopes.scopes)

        if not required_permissions or required_permissions.issubset(permissions) or self.__is_system_admin(user):
            return user
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=RETURN_MSG.access_denied % ", ".join(required_permissions),
            )

    def __is_system_admin(self, user: User) -> bool:
        return (user.role.name == settings.super_user_role) and (user.role.domain == settings.super_user_domain)

    def authorize_model_attributes(self, model: BaseModel, user: User) -> BaseModel:
        """Authorizes user access to response model attibutes. Returns the authorized response model"""
        editable_attributes = []
        logger.info(user.email)
        for field_name, field_info in model.model_fields.items():
            if field_name == "editable_attributes":
                continue
            attr_name = field_name
            if isinstance(field_info, FieldInfo) and field_info.alias:
                attr_name = field_info.alias
            #TODO: implement the permissions authorization
            editable_attributes.append(attr_name)
        return model.model_copy(update={"editable_attributes": editable_attributes})


authorization_service: Authorization = Authorization()
