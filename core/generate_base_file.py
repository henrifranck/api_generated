import os
from typing import List

from model_type import snake_to_camel, camel_to_snake, generate_class_name
from schemas import ClassModel


def generate_base_file(models: List[ClassModel]):
    """Generate an __init__.py file to import schema classes from each file."""
    lines = [
        f"# Import all the models, so that Base has them before being",
        f"# imported by Alembic",
        f"from app.db.base_class import Base # noqa"
    ]
    for model in models:
        model = ClassModel(**model)
        model_name = generate_class_name(model.name)
        module_name = camel_to_snake(model.name)
        lines.append(
            f"from app.models.{module_name} import {model_name} # noqa")

    # Join all import statements with a newline and add a final newline
    return "\n".join(lines) + "\n"


def write_base_files(models: List[ClassModel], output_dir: str):
    schema_folder = output_dir + "/app/db"

    # Generate __init__.py content
    init_content_schemas = generate_base_file(models)

    # Write the content to __init__.py
    with open(os.path.join(schema_folder, "base.py"), "w") as init_file_schemas:
        init_file_schemas.write(init_content_schemas)
    print("Successfully generated base.py!")
