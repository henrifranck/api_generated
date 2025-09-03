import os
import logging
from typing import List, Dict, Any, Optional, Set, Tuple

from schemas import ClassModel, AttributesModel
from model_type import preserve_custom_sections, camel_to_snake
from utils.generate_data_test import generate_data  # ← NEW import
import datetime, uuid
from datetime import datetime, date, time

# ---------------------------------------------------------------------------
# Configuration & logging
# ---------------------------------------------------------------------------
OUTPUT_DIR = "/tests"
TEST_LIST = ["create", "update", "get", "get_by_id", "delete"]

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers for code generation
# ---------------------------------------------------------------------------


def _literal_value(attr: AttributesModel) -> str:
    """
    Return Python *code* for a realistic value of the given column.
    No more hard-coded None!
    """
    # Give special-case values you hard-coded earlier
    if attr.name == "email":
        name = generate_data("Email", 8)
        domain = generate_data("Domain", 4)
        return f"'{name}@{domain.lower()}.com'"
    if attr.name == "hashed_password":
        password = generate_data("PASS", 12)
        return f"'{password}'"

    # Let your existing generator pick something appropriate
    value = generate_data(attr.type, attr.length or 5)

    # Turn the *runtime* value into source-code text
    if isinstance(value, str):
        return repr(value)  # adds quotes & escapes
    if isinstance(value, (bool, int, float)):
        return repr(value)
    if isinstance(value, (datetime, date, time)):
        # Return datetime constructor instead of string
        if isinstance(value, (datetime, date, time)):
            return f"'{str(value.isoformat())}'"
    if isinstance(value, uuid.UUID):
        return f"'{str(value)}'"

    # fallback – rarely needed
    return repr(value)


def _literal_name(name: str) -> str:
    if name == "hashed_password":
        return "password"
    return name


def _build_dependency_setup_lines(
        model: ClassModel,
        all_models: Dict[str, ClassModel],
        created: Set[str],
        indent: str = "    ",
) -> Tuple[List[str], str]:
    """
    Recursively create parent FK models and emit Python test code for the current model.
    Skips auto-increment `id` fields.
    """
    lines: List[str] = []
    model_var = camel_to_snake(model.name)
    data_var = f"{model_var}_data"

    # Recurse for foreign keys
    for attr in model.attributes:
        if attr.is_foreign and attr.foreign_key_class:
            fk_model = all_models[attr.foreign_key_class]
            if fk_model.name not in created:
                fk_lines, _ = _build_dependency_setup_lines(
                    fk_model, all_models, created, indent
                )
                lines.extend(fk_lines)

    # Build the test data
    lines.append(f"{indent}# Test data for {model.name}")
    lines.append(f"{indent}{data_var} = schemas.{model.name}Create(")
    for attr in model.attributes:
        if (attr.name == "id" and attr.is_auto_increment):
            continue  # ⛔️ Skip auto-incrementing primary key, TYPE DATETIME
        if attr.is_foreign and attr.foreign_key_class:
            fk_var = camel_to_snake(attr.foreign_key_class)
            lines.append(f"{indent}    {attr.name}={fk_var}.id,")
        else:
            lines.append(f"{indent}    {_literal_name(attr.name)}={_literal_value(attr)},")
    lines.append(f"{indent})\n")

    # Create the object using CRUD
    table_name = camel_to_snake(model.name)
    lines.append(f"{indent}{model_var} = crud.{table_name}.create(db=db, obj_in={data_var})\n")

    created.add(model.name)
    return lines, model_var


# ---------------------------------------------------------------------------
# Code-gen building blocks
# ---------------------------------------------------------------------------


def generate_import(_: ClassModel) -> str:
    """Imports that every generated test file needs."""
    return "\n".join(
        [
            "from fastapi import status",
            "from app import crud, schemas",
            "from sqlalchemy.orm import Session",
            "from typing import Any, Dict",
            "import pytest",
            "from datetime import datetime, date, time, timedelta",
            "import uuid",  # Add this if you're using UUID fields
        ]
    )


def generate_test_crud(
        model: ClassModel, table_name: str, all_models: Dict[str, ClassModel]
) -> str:
    """Emit the five CRUD test functions, with FK-aware setup."""
    test_name = camel_to_snake(model.name)
    out: List[str] = [f'"""Tests for CRUD operations on {model.name} model."""']
    for test_key in TEST_LIST:
        lines: List[str] = [f"\n\ndef test_{test_key}_{table_name}(db: Session):"]
        lines.append(f'    """Test {test_key} operation for {model.name}."""')

        # -------------------------------------------------------------------
        # Dependency chain (creates everything, *including* {model})
        # -------------------------------------------------------------------
        dep_lines, root_var = _build_dependency_setup_lines(model, all_models, set())
        lines.extend(dep_lines)
        data_var = f"{root_var}_data"  # created inside dependency builder
        schema_update = f"schemas.{model.name}Update"

        # -------------------------------------------------------------------
        # Specific CRUD scenarios
        # -------------------------------------------------------------------
        if test_key == "create":
            lines.extend(
                [
                    "    # Assertions",
                    f"    assert {root_var}.id is not None",
                    *[
                        f"    assert {root_var}.{a.name} == {data_var}.{a.name}"
                        for a in model.attributes
                        if a.name != "id" and a.name != 'hashed_password'
                    ],
                ]
            )

        elif test_key == "update":
            datetime_fields = [
                a.name for a in model.attributes
                if 'datetime' in a.type.lower()
            ]
            date_fields = [
                a.name for a in model.attributes
                if 'date' in a.type.lower() and 'datetime' not in a.type.lower()
            ]
            time_fields = [
                a.name for a in model.attributes
                if 'time' in a.type.lower() and 'datetime' not in a.type.lower()
            ]

            lines.extend(
                [
                    "    # Update data",
                    *[
                        f"    {a.name}_value = {root_var}.{a.name}"
                        for a in model.attributes
                        if (a.name != 'id' and not a.is_foreign and a.name != 'hashed_password')
                    ],
                    f"    update_data = {schema_update}(**{{",
                    "        k: (not v) if isinstance(v, bool) else",
                    "           (v + 1) if isinstance(v, (int, float)) else",
                    # Handle datetime fields - add 1 day
                    "           (datetime.fromisoformat(v) + timedelta(days=1)).isoformat() if k in " + str(
                        datetime_fields) + " and isinstance(v, str) else",
                    "           (v + timedelta(days=1)) if k in " + str(
                        datetime_fields) + " and isinstance(v, datetime) else",
                    # Handle date fields - add 1 day
                    "           (date.fromisoformat(v) + timedelta(days=1)).isoformat() if k in " + str(
                        date_fields) + " and isinstance(v, str) else",
                    "           (v + timedelta(days=1)) if k in " + str(date_fields) + " and isinstance(v, date) else",
                    # Handle time fields - add 1 hour
                    "           ((datetime.strptime(v, '%H:%M:%S') + timedelta(hours=1)).time().strftime('%H:%M:%S')) if k in " + str(
                        time_fields) + " and isinstance(v, str) else",
                    "           ((datetime.combine(date.today(), v) + timedelta(hours=1)).time()) if k in " + str(
                        time_fields) + " and isinstance(v, time) else",
                    "           f'updated_{v}'",
                    f"        for k, v in {data_var}.dict().items()",
                    "        if k not in ('id', 'hashed_password') and isinstance(v, dict) == False",
                    "    })",
                    f"    updated_{root_var} = crud.{table_name}.update("
                    f"db=db, db_obj={root_var}, obj_in=update_data)",
                    "",
                    "    # Assertions",
                    f"    assert updated_{root_var}.id == {root_var}.id",
                    *[
                        # For datetime fields - check date changed
                        f"    assert updated_{root_var}.{a.name}.date() != {a.name}_value.date()"
                        if a.name in datetime_fields else
                        # For date fields - check date changed
                        f"    assert updated_{root_var}.{a.name} != {a.name}_value"
                        if a.name in date_fields else
                        # For time fields - check time changed
                        f"    assert updated_{root_var}.{a.name}.strftime('%H:%M:%S') != {a.name}_value.strftime('%H:%M:%S')"
                        if a.name in time_fields else
                        # For all other fields
                        f"    assert updated_{root_var}.{a.name} != {a.name}_value"
                        for a in model.attributes
                        if a.name != 'id' and not a.is_foreign and a.name != 'hashed_password' and a.type.lower() != 'json'
                    ],
                ]
            )

        elif test_key == "get":
            lines.extend(
                [
                    "    # Get all records",
                    f"    records = crud.{table_name}.get_multi_where_array(db=db)",
                    "",
                    "    # Assertions",
                    "    assert len(records) > 0",
                    f"    assert any(r.id == {root_var}.id for r in records)",
                ]
            )

        elif test_key == "get_by_id":
            lines.extend(
                [
                    "    # Get by ID",
                    f"    retrieved_{root_var} = crud.{table_name}.get(db=db, id={root_var}.id)",
                    "",
                    "    # Assertions",
                    f"    assert retrieved_{root_var} is not None",
                    f"    assert retrieved_{root_var}.id == {root_var}.id",
                    *[
                        f"    assert retrieved_{root_var}.{a.name} == {root_var}.{a.name}"
                        for a in model.attributes
                        if a.name != 'id' and a.name != 'hashed_password'
                    ],
                ]
            )

        elif test_key == "delete":
            lines.extend(
                [
                    "    # Delete record",
                    f"    deleted_{root_var} = crud.{table_name}.remove(db=db, id={root_var}.id)",
                    "",
                    "    # Assertions",
                    f"    assert deleted_{root_var} is not None",
                    f"    assert deleted_{root_var}.id == {root_var}.id",
                    "",
                    "    # Verify deletion",
                    f"    assert crud.{table_name}.get(db=db, id={root_var}.id) is None",
                ]
            )

        out.extend(lines)

    return "\n".join(out)


def generate_full_schema(
        model: ClassModel, table_name: str, all_models: Dict[str, ClassModel]
) -> str:
    """Concatenate imports + helper tests for one model into a file."""
    return "\n".join(
        [generate_import(model), generate_test_crud(model, table_name, all_models)]
    )


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------


def write_test_crud(models: List[ClassModel], output_dir: str) -> None:
    """
    For every ClassModel in *models* write `tests/test_crud_<table>.py`,
    preserving any custom sections.
    """
    full_output_dir = os.path.join(output_dir, OUTPUT_DIR.lstrip("/"))
    os.makedirs(full_output_dir, exist_ok=True)

    # FIX: Normalize all models to ClassModel objects first
    normalized_models = [
        m if isinstance(m, ClassModel) else ClassModel(**m) for m in models
    ]
    all_models: Dict[str, ClassModel] = {m.name: m for m in normalized_models}

    print("all model ito an", all_models)

    for model in normalized_models:
        table_name = camel_to_snake(model.name)
        content = generate_full_schema(model, table_name, all_models)
        fname = f"test_crud_{table_name}.py"
        fpath = os.path.join(full_output_dir, fname)

        # Preserve custom section markers
        final_content = preserve_custom_sections(fpath, content)

        with open(fpath, "w", encoding="utf-8") as fp:
            fp.write(final_content)

        logger.info("Generated CRUD tests for %s", table_name)


def main(models: List[ClassModel], output_dir: str | None = None) -> None:
    """CLI entry point."""
    if output_dir is None:
        output_dir = os.getcwd()
    write_test_crud(models, output_dir)


if __name__ == "__main__":
    # Example usage (expects `models` already loaded):
    # main(models)
    pass
