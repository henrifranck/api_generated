import os
import re
from typing import List

from model_type import preserve_custom_sections, camel_to_snake, snake_to_camel, generate_class_name
from schemas import ClassModel, AttributesModel
from utils.generate_data_test import get_comumn_type_msql

OUTPUT_DIR = "/app/models"


def generate_import(model: ClassModel):
    """Generate the necessary imports for the model."""
    imports = [
        "from app.db.base_class import Base",
        "from sqlalchemy import Column, ForeignKey, DateTime, func, select, case, or_, and_",
        "from sqlalchemy.orm import relationship, column_property, aliased",
        f"from sqlalchemy import {model.column_type_list}"
    ]
    return "\n".join(imports)


def generate_models(model: ClassModel):
    """Generate the SQLAlchemy model class."""
    table_name = camel_to_snake(model.name)
    model_name = generate_class_name(model.name)
    models_lines = [f"\n\nclass {model_name}(Base):", f"    __tablename__ = '{table_name}'"]

    # Add default columns: created_at, updated_at, deleted_at
    default_columns = [
        AttributesModel(name="created_at", type="DateTime", is_required=True),
        AttributesModel(name="updated_at", type="DateTime", is_required=False),
        AttributesModel(name="deleted_at", type="DateTime", is_required=False)
    ]

    # Combine model attributes with default columns
    all_columns = model.attributes + default_columns

    for column in all_columns:
        column_def = f"    {column.name} = Column({get_comumn_type_msql(column.type)}"
        if column.type == "String" and column.length:
            column_def += f"({column.length})"

        # Conditionally add primary_key and autoincrement
        column_options = []
        if column.is_primary:
            column_options.append("primary_key=True")
        if column.is_auto_increment:
            column_options.append("autoincrement=True")
        if column.is_required:
            column_options.append("nullable=False")
        if column.is_unique:
            column_options.append("unique=True")
        if column.is_indexed:
            column_options.append("index=True")

        if column.is_foreign:
            column_options = [f"ForeignKey('{camel_to_snake(column.foreign_key_class)}.{column.foreign_key}')"]

        # Add default values for created_at and updated_at
        if column.name == "created_at":
            models_lines.append("")
            models_lines.append("    # default column")
            column_options.append("default=func.now()")
        elif column.name == "updated_at":
            column_options.append("default=func.now()")
            column_options.append("onupdate=func.now()")

        column_def += ", " + ", ".join(column_options) if len(column_options) > 0 else ", ".join(column_options)
        column_def += ")"
        models_lines.append(column_def)
    models_lines.append("")
    models_lines.append("    # Relations")
    for column in model.attributes:
        if column.is_foreign:
            column_def = f"    {camel_to_snake(column.foreign_key_class)} = relationship('{column.foreign_key_class}', " \
                         f"foreign_keys=[{column.name}])"
            models_lines.append(column_def)

    models_lines.append("")
    return "\n".join(models_lines)


def generate_full_models(model):
    """Generate the full SQLAlchemy model with imports."""
    schema_lines = [
        generate_import(model),
        generate_models(model),
    ]
    return "\n".join(schema_lines)


def write_models(models: List[ClassModel], output_dir):
    """Write the generated models to files."""
    output_dir += OUTPUT_DIR
    """Write the generated models to files, preserving custom sections."""
    os.makedirs(output_dir, exist_ok=True)
    for model in models:
        model = ClassModel(**model)
        model_name = camel_to_snake(model.name)
        models_content = generate_full_models(model)
        file_name = f"{model_name}.py"
        file_path = os.path.join(output_dir, file_name)

        # Preserve custom sections in the file
        final_content = preserve_custom_sections(file_path, models_content)

        with open(file_path, "w") as f:
            f.write(final_content)
        print(f"Generated model for: {model_name}")
