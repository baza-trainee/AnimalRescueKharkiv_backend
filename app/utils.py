import inspect
import pkgutil
from importlib import import_module
from importlib.machinery import FileFinder
from types import ModuleType
from typing import Any, Dict

import src
from fastapi import APIRouter
from src.configuration.db import Base


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
    ).values())

def find_attributes_recursively(module: ModuleType,
                    attribute_name: str|None = None,
                    attribute_type: type|None = None,
                    match_module_name: str|None = None) -> Dict[int, Any]:
    """Recursively loops through modules to find global attributes by name and/or type"""
    attributes:Dict[int,Any] = {}
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
                                                match_module_name))
                elif not match_module_name or module_name == match_module_name:
                    submodule = module_spec.loader.load_module(module_name)
                    for global_attr_name in dir(submodule):
                        if attribute_name and attribute_name != global_attr_name:
                            continue
                        global_attr = getattr(submodule,global_attr_name)
                        if (global_attr and id(global_attr) not in attributes):
                            if attribute_type and not isinstance(global_attr, attribute_type):
                                continue
                            attributes[id(global_attr)] = global_attr
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
