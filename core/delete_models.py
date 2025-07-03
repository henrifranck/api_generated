import os

from model_type import camel_to_snake

LIST_DIRS = [
    {"name": "/app/models/", "prefix": "", "suffix": ""},
    {"name": "/app/schemas/", "prefix": "", "suffix": ""},
    {"name": "/app/schemas/", "prefix": "", "suffix": ""},
    {"name": "/app/crud/", "prefix": "crud_", "suffix": ""},
    {"name": "/app/api/api_v1/endpoints/", "prefix": "", "suffix": "s"},
    {"name": "/test/", "prefix": "test_apis_", "suffix": ""},
    {"name": "/test/", "prefix": "test_crud_", "suffix": ""},
]


def delete_files(model: str, output_dir: str):
    file_name = camel_to_snake(model)
    for dirs_ in LIST_DIRS:
        path_ = output_dir + dirs_["name"] + dirs_["prefix"]+file_name+dirs_["suffix"]
        if os.path.exists(path_):
            os.remove(path_)
