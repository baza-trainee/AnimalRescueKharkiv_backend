import pkgutil
from importlib.abc import MetaPathFinder
from types import ModuleType
from typing import Any, List

import src
from fastapi import APIRouter


def get_app_models() -> list:
    """..."""
    app_models = find_attribute_by_name_recursively(module=src, attribute_name="Base", match_module_name="models")
    return [model.metadata for model in app_models]

def get_app_routers() -> list:
    """..."""
    return find_attribute_by_type_recursively(module=src, attribute_type=APIRouter, match_module_name="routes")

def find_attribute_by_name_recursively(module: ModuleType,
                                       attribute_name: str,
                                       match_module_name: str|None = None) -> List[Any]:
    """..."""
    attributes:List[Any] = []
    for loader, module_name, is_pkg in pkgutil.walk_packages(module.__path__):
        if isinstance(loader, MetaPathFinder):
            module_spec = loader.find_spec(module_name, module.__path__)
            if module_spec and module_spec.loader:
                submodule = module_spec.loader.load_module(module_name)
                if is_pkg:
                    attributes.extend(find_attribute_by_name_recursively(submodule, attribute_name, match_module_name))
                elif not match_module_name or module_name == match_module_name:
                    for global_attr_name in dir(submodule):
                        if global_attr_name == attribute_name:
                            global_attr = getattr(submodule,global_attr_name)
                            if global_attr:
                                attributes.append(global_attr)
    return attributes


def find_attribute_by_type_recursively(module: ModuleType,
                                       attribute_type: type,
                                         match_module_name: str|None = None) -> list[Any]:
    """..."""
    attributes:List[Any] = []
    for loader, module_name, is_pkg in pkgutil.walk_packages(module.__path__):
        if isinstance(loader, MetaPathFinder):
            module_spec = loader.find_spec(module_name, module.__path__)
            if module_spec and module_spec.loader:
                submodule = module_spec.loader.load_module(module_name)
                if is_pkg:
                    attributes += find_attribute_by_type_recursively(submodule, attribute_type, match_module_name)
                elif not match_module_name or module_name == match_module_name:
                    for global_attr_name in dir(submodule):
                        global_attr = getattr(submodule,global_attr_name)
                        if global_attr and isinstance(global_attr, attribute_type):
                            attributes.append(global_attr)
    return attributes
