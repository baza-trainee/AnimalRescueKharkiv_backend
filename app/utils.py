import pkgutil
import src
from fastapi import APIRouter

def get_app_models():
    app_models = find_attribute_by_name_recursively(module=src, attribute_name="Base", match_module_name="models")
    return list(map(lambda model: model.metadata, app_models))

def get_app_routers():
    app_routers = find_attribute_by_type_recursively(module=src, attribute_type=APIRouter, match_module_name="routes")
    return app_routers

def find_attribute_by_name_recursively(module, attribute_name: str, match_module_name: str = None) -> set:
    attributes = []
    for loader, module_name, is_pkg in pkgutil.walk_packages(module.__path__):
        submodule = loader.find_spec(module_name, module.__path__).loader.load_module(module_name)
        if is_pkg:
            attributes += find_attribute_by_name_recursively(submodule, attribute_name, match_module_name)
        elif not match_module_name or module_name == match_module_name:
            for global_attr_name in dir(submodule):
                if global_attr_name == attribute_name:
                    global_attr = getattr(submodule,global_attr_name)
                    if global_attr:
                        attributes.append(global_attr)
    return attributes


def find_attribute_by_type_recursively(module, attribute_type: type, match_module_name: str = None) -> list:
    attributes = []
    for loader, module_name, is_pkg in pkgutil.walk_packages(module.__path__):
        submodule = loader.find_spec(module_name, module.__path__).loader.load_module(module_name)
        if is_pkg:
            attributes += find_attribute_by_type_recursively(submodule, attribute_type, match_module_name)
        elif not match_module_name or module_name == match_module_name:
            for global_attr_name in dir(submodule):
                global_attr = getattr(submodule,global_attr_name)                
                if global_attr and isinstance(global_attr, attribute_type):
                    attributes.append(global_attr)
    return attributes