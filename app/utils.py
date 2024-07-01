import pkgutil
from importlib.machinery import FileFinder
from types import ModuleType
from typing import Any, Dict, ValuesView

import src
from fastapi import APIRouter


def get_app_models() -> list:
    """..."""
    app_models = find_attribute_by_name_recursively(
        module=src,
        attribute_name="Base",
        match_module_name="models",
    ).values()
    return [model.metadata for model in app_models]

def get_app_routers() -> list:
    """..."""
    return list(find_attribute_by_type_recursively(
        module=src,
        attribute_type=APIRouter,
        match_module_name="routes",
    ).values())

def find_attribute_by_name_recursively(module: ModuleType,
                                       attribute_name: str,
                                       match_module_name: str|None = None) -> Dict[int, Any]:
    """..."""
    attributes:Dict[int, Any] = {}
    for loader, module_name, is_pkg in pkgutil.walk_packages(module.__path__):
        if isinstance(loader, FileFinder):
            module_spec = loader.find_spec(module_name)
            if module_spec and module_spec.loader:
                submodule = module_spec.loader.load_module(module_name)
                if is_pkg:
                    attributes.update(find_attribute_by_name_recursively(submodule, attribute_name, match_module_name))
                elif not match_module_name or module_name == match_module_name:
                    for global_attr_name in dir(submodule):
                        if global_attr_name == attribute_name:
                            global_attr = getattr(submodule,global_attr_name)
                            if global_attr and id(global_attr) not in attributes:
                                attributes[id(global_attr)] = global_attr
    return attributes


def find_attribute_by_type_recursively(module: ModuleType,
                                       attribute_type: type,
                                         match_module_name: str|None = None) -> Dict[int, Any]:
    """..."""
    attributes:Dict[int,Any] = {}
    for loader, module_name, is_pkg in pkgutil.walk_packages(module.__path__):
        if isinstance(loader, FileFinder):
            module_spec = loader.find_spec(module_name)
            if module_spec and module_spec.loader:
                submodule = module_spec.loader.load_module(module_name)
                if is_pkg:
                    attributes.update(find_attribute_by_type_recursively(submodule, attribute_type, match_module_name))
                elif not match_module_name or module_name == match_module_name:
                    for global_attr_name in dir(submodule):
                        global_attr = getattr(submodule,global_attr_name)
                        if (global_attr and isinstance(global_attr, attribute_type)
                            and id(global_attr) not in attributes):
                            attributes[id(global_attr)] = global_attr
    return attributes
