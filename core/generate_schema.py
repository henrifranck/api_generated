import os
import re
from typing import List, Optional

from schemas import ClassModel
from sqlalchemy.ext.declarative import DeclarativeMeta
from sqlalchemy import inspect
from pydantic import BaseModel

from model_type import preserve_custom_sections, \
    camel_to_snake, snake_to_camel  # Import your model definitions
from utils.generate_data_test import get_column_type, generate_comumn_name

OUTPUT_DIR = "/app/schemas"


def generate_field_validators(model: ClassModel) -> str:
    """Generate field validators for datetime, date, and time fields."""
    datetime_fields = []
    time_fields = []
    date_fields = []

    for column in model.attributes:
        column_type = column.type.lower()
        if 'datetime' in column_type:
            datetime_fields.append(column.name)
        elif 'time' in column_type and 'datetime' not in column_type:
            time_fields.append(column.name)
        elif 'date' in column_type and 'datetime' not in column_type:
            date_fields.append(column.name)

    validators = []

    if datetime_fields:
        fields_str = ', '.join([f"'{field}'" for field in datetime_fields])
        validators.append(f"""
    @field_validator({fields_str}, mode='before')
    def parse_datetime(cls, value):
        if value is None:
            return None
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value.replace('Z', '+00:00'))
            except ValueError:
                raise ValueError("Invalid datetime format")
        return value
""")

    if time_fields:
        fields_str = ', '.join([f"'{field}'" for field in time_fields])
        validators.append(f"""
    @field_validator({fields_str}, mode='before')
    def parse_time(cls, value):
        if value is None:
            return None
        if isinstance(value, str):
            try:
                # Handle both "HH:MM:SS" and "HH:MM" formats
                parts = value.split(':')
                if len(parts) == 2:
                    return time.fromisoformat(value + ':00')
                return time.fromisoformat(value)
            except ValueError:
                raise ValueError("Invalid time format, expected HH:MM:SS")
        return value
""")

    if date_fields:
        fields_str = ', '.join([f"'{field}'" for field in date_fields])
        validators.append(f"""
    @field_validator({fields_str}, mode='before')
    def parse_date(cls, value):
        if value is None:
            return None
        if isinstance(value, str):
            try:
                return date.fromisoformat(value)
            except ValueError:
                raise ValueError("Invalid date format, expected YYYY-MM-DD")
        return value
""")

    return '\n'.join(validators) if validators else ""


def generate_import(model: ClassModel) -> str:
    """Generate the necessary imports for the schema."""
    schema_lines = [
        "from datetime import datetime, time, date",
        "from typing import Any",
        "from typing import List, Optional",
        "from pydantic import BaseModel, ConfigDict, field_validator",
    ]

    # Check if we need field validators
    needs_validators = any(
        'datetime' in col.type.lower() or
        ('time' in col.type.lower() and 'datetime' not in col.type.lower()) or
        ('date' in col.type.lower() and 'datetime' not in col.type.lower())
        for col in model.attributes
    )

    if needs_validators:
        schema_lines.append("from pydantic import field_validator")

    # Inspect relationships in the model
    for attr in model.attributes:
        if attr.is_foreign:
            schema_lines.append(f"from .{camel_to_snake(attr.foreign_key_class)} import {attr.foreign_key_class}")

    schema_lines.append("")  # Add a blank line at the end
    return "\n".join(schema_lines)


def generate_base_schema(model: ClassModel, table_name: str) -> str:
    """Generate the base schema class."""
    schema_name = f"{snake_to_camel(table_name)}Base"
    schema_lines = [f"\nclass {schema_name}(BaseModel):"]

    for column in model.attributes:
        if column.name != 'id':
            column_name = generate_comumn_name(column.name, not column.is_required)
            column_type = get_column_type(column.type)

            default_value = " = None"
            schema_lines.append(f"    {column_name['name']}: Optional[{column_type}]{default_value}")

    # Add field validators if needed
    validators = generate_field_validators(model)
    if validators:
        schema_lines.append(validators)

    schema_lines.append("")
    return "\n".join(schema_lines)


def generate_create_schema(model: ClassModel, base_schema: str, table_name: str) -> str:
    """Generate the create schema class."""
    schema_name = f"{snake_to_camel(table_name)}Create"
    schema_lines = [f"\nclass {schema_name}({base_schema}):"]

    # Add required fields (nullable=False and no default value)
    for column in model.attributes:
        if column.is_required and not column.is_primary:
            column_name = generate_comumn_name(column.name)
            column_type = get_column_type(column.type)
            schema_lines.append(f"    {column_name['name']}: {column_type}")
    if len(schema_lines) == 1:
        schema_lines.append("    pass")

    schema_lines.append("")  # Add a blank line at the end
    return "\n".join(schema_lines)


def generate_update_schema(base_schema: str, table_name: str) -> str:
    """Generate the update schema class."""
    schema_name = f"{snake_to_camel(table_name)}Update"
    schema_lines = [
        f"\nclass {schema_name}({base_schema}):",
        "    pass",
        "",
    ]
    return "\n".join(schema_lines)


def generate_in_db_base_schema(model: ClassModel, base_schema: str, table_name: str) -> str:
    """Generate the InDBBase schema class with all foreign keys."""
    schema_name = f"{snake_to_camel(table_name)}InDBBase"
    schema_lines = [f"\nclass {schema_name}({base_schema}):"]

    # Add primary key field
    schema_lines.append("    id: Optional[int]")

    # Inspect columns for foreign keys
    for column in model.attributes:
        if column.is_foreign:  # Check if the column has foreign key constraints
            column_type = get_column_type(column.type)
            schema_lines.append(f"    {column.name}: Optional[{column_type}]")

    schema_lines.append("")
    schema_lines.append("    model_config = ConfigDict(from_attributes=True)")
    schema_lines.append("")

    return "\n".join(schema_lines)


def generate_model_class(model: ClassModel, in_db_base_schema: str, table_name: str) -> str:
    """Generate the User schema class with all relationships."""
    schema_name = snake_to_camel(table_name)
    schema_lines = [f"\nclass {schema_name}({in_db_base_schema}):"]

    i = 0
    # Inspect relationships in the model
    for column in model.attributes:
        if column.is_foreign:
            i += 1
            related_model = column.foreign_key_class
            relationship_name = camel_to_snake(related_model)
            schema_lines.append(f"    {relationship_name}: Optional[{related_model}] = None")
    if i == 0:
        schema_lines.append(f"    pass")

    schema_lines.append("")  # Add a blank line at the end
    return "\n".join(schema_lines)


def generate_in_db_class(in_db_base_schema: str, table_name: str) -> str:
    """Generate the UserInDB schema class."""
    schema_name = f"{snake_to_camel(table_name)}InDB"
    schema_lines = [
        f"\nclass {schema_name}({in_db_base_schema}):",
        "    pass",
        "",
    ]
    return "\n".join(schema_lines)


def generate_response_class(class_name: str, table_name: str) -> str:
    """Generate the Response schema class."""
    schema_name = f"Response{snake_to_camel(table_name)}"
    schema_lines = [
        f"\nclass {schema_name}(BaseModel):",
        "    count: int",
        f"    data: Optional[List[{class_name}]]",
        "",
    ]
    return "\n".join(schema_lines)


def generate_full_schema(model: ClassModel, table_name: str) -> str:
    """Generate the full schema for a model."""
    base_schema = f"{snake_to_camel(table_name)}Base"
    in_db_base_schema = f"{snake_to_camel(table_name)}InDBBase"
    class_name = f"{snake_to_camel(table_name)}"

    schema_lines = [
        generate_import(model),
        generate_base_schema(model, table_name),
        generate_create_schema(model, base_schema, table_name),
        generate_update_schema(base_schema, table_name),
        generate_in_db_base_schema(model, base_schema, table_name),
        generate_model_class(model, in_db_base_schema, table_name),
        generate_in_db_class(in_db_base_schema, table_name),
        generate_response_class(class_name, table_name),
    ]
    return "\n".join(schema_lines)


def write_schemas(models: List[ClassModel], output_dir: str):
    """Write the generated schemas to files, preserving custom sections."""
    output_dir += OUTPUT_DIR
    os.makedirs(output_dir, exist_ok=True)
    for model in models:
        model = ClassModel(**model)
        table_name = camel_to_snake(model.name)
        schemas = generate_full_schema(model, table_name)
        file_name = f"{table_name}.py"
        file_path = os.path.join(output_dir, file_name)

        # Preserve custom sections in the file
        final_content = preserve_custom_sections(file_path, schemas)

        with open(file_path, "w") as f:
            f.write(final_content)
        print(f"Generated schemas for: {table_name}")
