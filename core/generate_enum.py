import os
from typing import List, Any

from model_type import camel_to_snake

OUTPUT_DIR = "/app/enum"


def generate_import():
    """Generate the necessary imports for the enum."""
    imports = [
        "from enum import Enum",
        ""
    ]
    return "\n".join(imports)


def generate_enum(enum_data):
    """Generate an enum class from the enum data."""
    enum_name = enum_data["name"]
    values = enum_data["values"]

    enum_lines = [
        f"class {enum_name}(Enum):",
    ]

    for value in values:
        key = value["key"]
        enum_value = value["value"]
        enum_lines.append(f'    {key} = "{enum_value}"')

    enum_lines.append("")  # Add empty line at the end
    return "\n".join(enum_lines)


def generate_full_enum(enum_data):
    """Generate the full enum with imports."""
    enum_lines = [
        generate_import(),
        generate_enum(enum_data),
    ]
    return "\n".join(enum_lines)


def preserve_custom_sections(file_path, content):
    """Preserve custom sections in existing files (stub implementation)."""
    # This is a simplified implementation
    # In a real scenario, you would read the existing file and merge content
    return content


def write_enums(enums: List[Any], output_dir):
    """Write the generated enums to separate files."""
    full_output_dir = os.path.join(output_dir, OUTPUT_DIR.lstrip('/'))
    os.makedirs(full_output_dir, exist_ok=True)

    for enum in enums:
        model_name = camel_to_snake(enum["name"])
        enum_content = generate_full_enum(enum)
        file_name = f"{model_name}.py"
        file_path = os.path.join(full_output_dir, file_name)

        # Preserve custom sections if the function exists
        final_content = preserve_custom_sections(file_path, enum_content)

        with open(file_path, "w") as f:
            f.write(final_content)
        print(f"Generated enum for: {model_name}")
