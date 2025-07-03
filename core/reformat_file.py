import os


def reformate_code(output_dir: str):
    list_dirs = [
        {"name": "/app/api/deps"},
        {"name": "/app/api/api_v1/endpoints/login"},
        {"name": "/app/core/security"},
        {"name": "/tests/test_login"},
        {"name": "/tests/test_deps"},

    ]
    for dirs_ in list_dirs:
        path_ = output_dir + dirs_["name"]
        if os.path.exists(path_):
            os.remove(path_)
