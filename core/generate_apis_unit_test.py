# -*- coding: utf-8 -*-
"""test_api_generator.py – v2 (modified)

Generate FastAPI integration tests (CRUD via HTTP) for every SQLAlchemy
ClassModel. FK‑aware, supports optional JWT auth. Now generates dict-based test data for the main model.
"""
from __future__ import annotations

import os
import logging
from typing import List, Dict, Optional, Set

import schemas
from core.generate_crud_unit_test import _literal_name, _literal_value
from schemas import ClassModel
from model_type import preserve_custom_sections, camel_to_snake
from utils.generate_data_test import generate_column, generate_data

# ---------------------------------------------------------------------------
# Configuration & logging
# ---------------------------------------------------------------------------
OUTPUT_DIR = "/tests"
TEST_LIST = ["create", "update", "get", "get_by_id", "delete"]

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helper generators (imports / auth / headers)
# ---------------------------------------------------------------------------

def _gen_imports(other_cfg: schemas.OtherConfigSchema) -> str:
    lines = [
        "from fastapi import status",
        "from app import crud, schemas",
        "from datetime import datetime, timedelta",
    ]
    if other_cfg.use_authentication:
        lines.append("from app.core import security")
    return "\n".join(lines)


def _gen_headers(other_cfg: schemas.OtherConfigSchema) -> str:
    return 'headers={"Authorization": f"Bearer {token}"}' if other_cfg.use_authentication else ""


def _gen_auth_setup(other_cfg: schemas.OtherConfigSchema) -> List[str]:
    if not other_cfg.use_authentication:
        return []
    name = generate_data("", 6)
    domain = generate_data("", 6)
    password = generate_data("", 6)
    return [
        "    # Auth setup",
        "    user_data = {",
        f"        'email': '{name}@{domain.lower()}.com',",
        f"        'password': '{password}',",
        "        'is_active': True,",
        "        'is_superuser': False,",
        "    }",
        "    user = crud.user.create(db, obj_in=schemas.UserCreate(**user_data))",
        "    db.commit()",
        "    token = security.create_access_token(sub={'id': str(user.id), 'email': user.email})",
        "",
    ]


# ---------------------------------------------------------------------------
# Dependency builder – only for FK parent models
# ---------------------------------------------------------------------------
def _build_dependency_setup_lines(
        model: ClassModel,
        all_models: Dict[str, ClassModel],
        created: Set[str],
        indent: str = "    ",
) -> List[str]:
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
                fk_lines = _build_dependency_setup_lines(
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
    return lines


# ---------------------------------------------------------------------------
# Test generation for a single model
# ---------------------------------------------------------------------------

def _gen_test_api(
    model: ClassModel,
    table_name: str,
    all_models: Dict[str, ClassModel],
    other_cfg: schemas.OtherConfigSchema,
) -> str:
    base_ep = f"/api/v1/{table_name}s"
    code_lines: List[str] = []

    hdrs_kwarg = _gen_headers(other_cfg)
    fk_fields = [attr.name for attr in model.attributes if attr.is_foreign]
    fk_fields_literal = repr(fk_fields)

    for op in TEST_LIST:
        tl: List[str] = [f"\n\ndef test_{op}_{table_name}_api(client, db):",
                         f'    """{op.capitalize()} {model.name} via API."""']

        # Auth setup
        tl.extend(_gen_auth_setup(other_cfg))

        # ✅ Build only FK dependencies, skip self
        created = set()
        for attr in model.attributes:
            if attr.is_foreign and attr.foreign_key_class:
                fk_model = all_models[attr.foreign_key_class]
                fk_lines = _build_dependency_setup_lines(fk_model, all_models, created)
                tl.extend(fk_lines)

        # ✅ Create test data dict for this model
        tl.append(f"    {table_name}_data = {{")
        for attr in model.attributes:
            column = attr.name if attr.name != "hashed_password" else "password"
            if column == "id" and attr.is_auto_increment:
                continue
            if attr.is_foreign and attr.foreign_key_class:
                parent_var = camel_to_snake(attr.foreign_key_class)
                tl.append(f"        '{column}': {parent_var}.id,")
            else:
                tl.append(f"        '{column}': {_literal_value(attr)},")
        tl.append("    }")
        tl.append("")

        # --------------------------------------------------------------------
        # CREATE test
        if op == "create":
            tl += [
                f"    resp = client.post('{base_ep}/', json={table_name}_data, {hdrs_kwarg})",
                "    assert resp.status_code == status.HTTP_200_OK, resp.text",
                "    created = resp.json()",
                "    assert created['id'] is not None",
            ] + [
                f"    assert created['{a.name}'] == {table_name}_data['{a.name}']"
                for a in model.attributes
                if a.name not in ("id", "hashed_password") and a.type.lower() != 'datetime'
            ]

        # --------------------------------------------------------------------
        # UPDATE test
        elif op == "update":
            datetime_fields = [a.name for a in model.attributes if 'datetime' in a.type.lower()]
            time_fields = [a.name for a in model.attributes if 'time' in a.type.lower() and 'datetime' not in a.type.lower()]

            tl += [
                f"    resp_c = client.post('{base_ep}/', json={table_name}_data, {hdrs_kwarg})",
                "    assert resp_c.status_code == status.HTTP_200_OK",
                "    created = resp_c.json()",
                f"    fk_fields = {fk_fields_literal}",
                "    update_data = {",
                "        k: (not v) if isinstance(v, bool) else",
                "           (v + 1) if isinstance(v, (int, float)) else",
                f"           (datetime.fromisoformat(v) + timedelta(days=1)).isoformat() if k in {datetime_fields} else",
                f"           (datetime.strptime(v, '%H:%M:%S').time().replace(hour=(datetime.strptime(v, '%H:%M:%S').hour + 1)%24).strftime('%H:%M:%S')) if k in {time_fields} else",
                "           f'updated_{v}'",
                f"        for k, v in {table_name}_data.items()",
                "        if k not in ('id', 'hashed_password') and k not in fk_fields and isinstance(v, dict) == False",
                "    }",
                f"    resp_u = client.put(f'{base_ep}/{{created[\"id\"]}}', json=update_data, {hdrs_kwarg})",
                "    assert resp_u.status_code == status.HTTP_200_OK",
                "    updated = resp_u.json()",
                "    assert updated['id'] == created['id']",
            ] + [
                f"    assert updated['{a.name}'] == update_data['{a.name}']"
                for a in model.attributes
                if a.name not in ("id", "hashed_password") and not a.is_foreign and a.type.lower() != 'json'
            ]

        # --------------------------------------------------------------------
        # GET test
        elif op == "get":
            tl += [
                f"    client.post('{base_ep}/', json={table_name}_data, {hdrs_kwarg})",
                f"    resp_g = client.get('{base_ep}/', {hdrs_kwarg})",
                "    assert resp_g.status_code == status.HTTP_200_OK",
                "    items = resp_g.json()['data']",
                "    assert any(item.get('id') for item in items)",
            ]

        # --------------------------------------------------------------------
        # GET_BY_ID test
        elif op == "get_by_id":
            tl += [
                f"    resp_c = client.post('{base_ep}/', json={table_name}_data, {hdrs_kwarg})",
                "    created = resp_c.json()",
                f"    resp_g = client.get(f'{base_ep}/{{created[\"id\"]}}', {hdrs_kwarg})",
                "    assert resp_g.status_code == status.HTTP_200_OK",
                "    retrieved = resp_g.json()",
                "    assert retrieved['id'] == created['id']",
            ]

        # --------------------------------------------------------------------
        # DELETE test
        elif op == "delete":
            tl += [
                f"    resp_c = client.post('{base_ep}/', json={table_name}_data, {hdrs_kwarg})",
                "    created = resp_c.json()",
                f"    resp_d = client.delete(f'{base_ep}/{{created[\"id\"]}}', {hdrs_kwarg})",
                "    assert resp_d.status_code == status.HTTP_200_OK",
                "    deleted = resp_d.json()",
                f"    assert deleted['msg'] == '{model.name} deleted successfully'",
                f"    resp_chk = client.get(f'{base_ep}/{{created[\"id\"]}}', {hdrs_kwarg})",
                "    assert resp_chk.status_code == status.HTTP_404_NOT_FOUND",
            ]

        # Add this test block to full output
        code_lines.extend(tl)

    return "\n".join(code_lines)


# ---------------------------------------------------------------------------
# File-level scaffold
# ---------------------------------------------------------------------------

def _gen_file(model: ClassModel, table_name: str, all_models: Dict[str, ClassModel],
              other_cfg: schemas.OtherConfigSchema) -> str:
    return "\n".join([
        _gen_imports(other_cfg),
        _gen_test_api(model, table_name, all_models, other_cfg),
    ])


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def write_test_apis(models: List[ClassModel], output_dir: str, other_cfg: schemas.OtherConfigSchema) -> None:
    out_dir = os.path.join(output_dir, OUTPUT_DIR.lstrip("/"))
    os.makedirs(out_dir, exist_ok=True)

    normalised = [m if isinstance(m, ClassModel) else ClassModel(**m) for m in models]
    all_models: Dict[str, ClassModel] = {m.name: m for m in normalised}

    for mdl in normalised:
        tbl = camel_to_snake(mdl.name)
        content = _gen_file(mdl, tbl, all_models, other_cfg)
        fname = f"test_{tbl}_api.py"
        fpath = os.path.join(out_dir, fname)
        final = preserve_custom_sections(fpath, content)
        with open(fpath, "w", encoding="utf-8") as fp:
            fp.write(final)
        logger.info("Generated test API for %s", tbl)


def main(models: List[ClassModel], other_cfg: schemas.OtherConfigSchema, output_dir: Optional[str] = None) -> None:
    if output_dir is None:
        output_dir = os.getcwd()
    write_test_apis(models, output_dir, other_cfg)
