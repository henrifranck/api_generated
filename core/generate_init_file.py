import os

from model_type import snake_to_camel, generate_class_name


def generate_init_file(folder, folder_type: str = "schemas"):
    """Generate an __init__.py file to import schema classes from each file."""
    lines = []
    for file_name in os.listdir(folder):
        if file_name.endswith(".py") and file_name != "__init__.py" and file_name != "base.py" and file_name != "base_copy.py":
            module_name = file_name.replace(".py", "")
            class_name = generate_class_name(module_name)
            if folder_type == "schemas":
                if module_name == 'msg':
                    lines.append(
                        f"from .{module_name} import {class_name}")
                elif module_name == "token":
                    lines.append(
                        f"from .{module_name} import  {class_name}, {class_name}Payload")
                else:
                    lines.append(
                        f"from .{module_name} import ( \n  {class_name},  \n  {class_name}Create,  \n  {class_name}Update,  \n  Response{class_name}\n)")
            elif folder_type == "models":
                lines.append(
                    f"from .{module_name} import {class_name}")
            else:
                module_name = file_name.replace(".py", "").replace("crud_", '')
                lines.append(
                    f"from .crud_{module_name} import {module_name}")

    # Join all import statements with a newline and add a final newline
    return "\n".join(lines) + "\n"


def write_init_files(output_dir: str):
    schema_folder = output_dir + "/app/schemas"
    models_folder = output_dir + "/app/models"
    crud_folder = output_dir + "/app/crud"

    # Generate __init__.py content
    init_content_schemas = generate_init_file(schema_folder, "schemas")

    # Write the content to __init__.py
    with open(os.path.join(schema_folder, "__init__.py"), "w") as init_file_schemas:
        init_file_schemas.write(init_content_schemas)

    init_content_models = generate_init_file(models_folder, "models")

    # Write the content to __init__.py
    with open(os.path.join(models_folder, "__init__.py"), "w") as init_file_models:
        init_file_models.write(init_content_models)

    init_content_crud = generate_init_file(crud_folder, "crud")

    # Write the content to __init__.py
    with open(os.path.join(crud_folder, "__init__.py"), "w") as init_file_crud:
        init_file_crud.write(init_content_crud)

    print("Successfully generated __init__.py!")
