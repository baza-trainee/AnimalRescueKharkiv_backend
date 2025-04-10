import inspect
import pkgutil
import re
from importlib import import_module
from importlib.machinery import FileFinder
from types import ModuleType
from typing import TYPE_CHECKING, Any, Callable, Dict, List, TypeVar

import src
from fastapi import APIRouter
from sqlalchemy import asc, desc, func
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.sql.elements import UnaryExpression
from src.base_schemas import SORTING_VALIDATION_REGEX
from src.configuration.db import Base
from src.exceptions.exceptions import RETURN_MSG

if TYPE_CHECKING:
    from sqlalchemy.sql.functions import coalesce

_T = TypeVar("_T")


def get_app_models() -> list:
    """Get all sqlalchemy models' metadata from nested modules"""
    app_models = find_attributes_recursively(
        module=src,
        attribute_name="Base",
        match_module_name="models",
    ).values()
    return [model.metadata for model in app_models]

def get_app_routers() -> list:
    """Get all application routers from nested modules"""
    return list(find_attributes_recursively(
        module=src,
        attribute_type=APIRouter,
        match_module_name="routes",
        unique_key=lambda x: x.prefix,
    ).values())

def __get_unique_attr_key(global_attr: object,
                           attribute_type: type|None = None,
                           unique_key: Callable[[Any], str]|None = None) -> str:
    key = str(id(global_attr))
    if unique_key and attribute_type is not None  and isinstance(global_attr, attribute_type):
        key = unique_key(global_attr)
    return key

def find_attributes_recursively(module: ModuleType,
                    attribute_name: str|None = None,
                    attribute_type: type|None = None,
                    match_module_name: str|None = None,
                    unique_key: Callable[[Any], str]|None = None) -> Dict[str, Any]:
    """Recursively loops through modules to find global attributes by name and/or type"""
    attributes:Dict[str,Any] = {}
    for loader, module_name, is_pkg in pkgutil.walk_packages(module.__path__):
        if isinstance(loader, FileFinder):
            module_spec = loader.find_spec(module_name)
            if module_spec and module_spec.loader:
                if is_pkg:
                    submodule = module_spec.loader.load_module(module_name)
                    attributes.update(
                        find_attributes_recursively(submodule,
                                                attribute_name,
                                                attribute_type,
                                                match_module_name,
                                                unique_key=unique_key))
                elif not match_module_name or module_name == match_module_name:
                    submodule = module_spec.loader.load_module(module_name)
                    for global_attr_name in dir(submodule):
                        if attribute_name and attribute_name != global_attr_name:
                            continue
                        global_attr = getattr(submodule,global_attr_name)
                        key = __get_unique_attr_key(global_attr=global_attr,
                                                    attribute_type=attribute_type,
                                                    unique_key=unique_key)
                        if (global_attr and key not in attributes):
                            if attribute_type and not isinstance(global_attr, attribute_type):
                                continue
                            attributes[key] = global_attr
    return attributes


def import_models_from_src() -> None:
    """Imports all model classes from src packages into a file"""
    imported_classes = {}
    package_name = "src"
    package = import_module(package_name)

    for finder, name, ispkg in pkgutil.walk_packages(package.__path__, package.__name__ + "."): # noqa: B007
        if not ispkg and name.endswith(".models"):
            module = import_module(name)
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if inspect.isclass(attr) and issubclass(attr, Base) and \
                (attr is not Base) and (attr_name not in imported_classes):
                        imported_classes[attr_name] = attr
                        globals()[attr_name] = attr


def get_sql_order_expression(sort: str,
                             model_type: DeclarativeBase,
                             default_dorting: UnaryExpression[_T],
                            ) -> UnaryExpression[_T]:
        """Creates SqlAlchemy order expression"""
        if not re.match(SORTING_VALIDATION_REGEX, sort):
            raise ValueError(RETURN_MSG.illegal_sort)
        field, direction = sort.split("|", 1)
        order_attr = None
        if "+" in field:
            parts: List[object] = []
            for part in field.split("+"):
                if not hasattr(model_type, part):
                    raise ValueError(RETURN_MSG.illegal_sort_field_name % part)
                attr: coalesce[_T] = func.coalesce(getattr(model_type, part), "")
                parts.append(attr)
                parts.append(" ")
                order_attr = func.concat(*parts)
        else:
            if not hasattr(model_type, field):
                raise ValueError(RETURN_MSG.illegal_sort_field_name % field)
            order_attr = getattr(model_type, field)

        if order_attr is not None:
            match direction.lower():
                case "asc":
                    return asc(order_attr)
                case "desc":
                    return desc(order_attr)
        return default_dorting
