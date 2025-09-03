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
from core.generate_filename import generate_filename
from schemas import ClassModel
from model_type import preserve_custom_sections, camel_to_snake
from utils.generate_data_test import generate_data, generate_random_boolean, generate_random_integer, \
    generate_random_text

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

def generate_login_test(user_model_name: str, user_model: ClassModel, all_enums: List[Dict] = None) -> str:
    """Generate dynamic login test based on user model structure"""

    user_table_name = camel_to_snake(user_model_name)

    # Trouver les noms des champs email et password
    email_field = "email"
    password_field = "password"
    hashed_password_field = "hashed_password"

    for attr in user_model.attributes:
        if attr.name.lower() == "email":
            email_field = attr.name
        elif attr.name.lower() == "password":
            password_field = attr.name
        elif attr.name.lower() == "hashed_password":
            hashed_password_field = attr.name

    # Générer les données de test dynamiquement
    test_data_lines = []
    password_value = "securepassword123"

    for attr in user_model.attributes:
        if attr.is_required and not (attr.name == "id" and attr.is_auto_increment):
            if attr.name == email_field:
                test_data_lines.append(f"        {attr.name}='testlogin@example.com',")

            elif attr.name == password_field:
                test_data_lines.append(f"        {attr.name}='{password_value}',")

            elif attr.name.lower() == "is_active":
                test_data_lines.append(f"        {attr.name}=True,")

            elif attr.name.lower() == "is_superuser":
                test_data_lines.append(f"        {attr.name}=False,")

            elif attr.name.lower() == "name":
                test_data_lines.append(f"        {attr.name}='Test User',")

            elif attr.type.lower() == "boolean":
                test_data_lines.append(f"        {attr.name}={generate_random_boolean()},")

            elif attr.type.lower() in ["integer", "int"]:
                test_data_lines.append(f"        {attr.name}={generate_random_integer(100)},")

            elif attr.type.lower() == "string":
                length = attr.length or 10
                test_data_lines.append(f"        {attr.name}='{generate_random_text(length)}',")

            elif attr.type.lower() == "enum" and attr.enum_name:
                enum_value = generate_data("enum", all_enums=all_enums, column=attr)
                test_data_lines.append(f"        {attr.name}={enum_value},")

            else:
                default_value = generate_data(attr.type, attr.length or 5)
                if isinstance(default_value, str):
                    test_data_lines.append(f"        {attr.name}='{default_value}',")
                else:
                    test_data_lines.append(f"        {attr.name}={default_value},")

    test_data_str = "\n".join(test_data_lines)

    return f"""
def test_login_access_token(client, db):
    # Create a test user with hashed password
    password = "{password_value}"
    create_data = schemas.{user_model_name}Create(
{test_data_str}
    )
    user = crud.{user_table_name}.create(db=db, obj_in=create_data)

    # Verify user was created correctly
    assert user is not None
    assert user.{email_field} == 'testlogin@example.com'
    assert user.is_active is True  # Explicitly check active status
    assert security.verify_password(password, user.{hashed_password_field})

    # Debug: Try authenticating directly
    authenticated_user = crud.{user_table_name}.authenticate(
        db, {email_field}='testlogin@example.com', password=password
    )
    assert authenticated_user is not None  # This might fail

    # Test login endpoint
    response = client.post(
        "/api/v1/login/access-token",
        data={{
            "username": user.{email_field},
            "password": password,
            "grant_type": "password"
        }},
        headers={{"Content-Type": "application/x-www-form-urlencoded"}},
    )

    assert response.status_code == status.HTTP_200_OK
    assert "access_token" in response.json()
"""


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


def _gen_auth_setup(other_cfg: schemas.OtherConfigSchema, all_models: Dict[str, ClassModel] = None, all_enums=None) -> \
List[str]:
    if not other_cfg.use_authentication:
        return []

    # Trouver automatiquement le modèle utilisateur
    user_model_name = "User"  # valeur par défaut
    user_model = None

    if all_models:
        # Chercher des modèles qui pourraient être des utilisateurs
        user_candidates = []
        for model_name, model in all_models.items():
            # Vérifier les attributs typiques d'un modèle utilisateur
            has_email = any(attr.name.lower() == "email" for attr in model.attributes)
            has_password = any(attr.name.lower() in ["password", "hashed_password"] for attr in model.attributes)

            if has_email and has_password:
                user_candidates.append((model_name, model))

        # Prendre le premier candidat ou utiliser "User"
        if user_candidates:
            user_model_name, user_model = user_candidates[0]
            print(f"Using {user_model_name} as user model for authentication")

    # Générer les données dynamiquement basées sur les colonnes requises
    user_data_lines = ["    user_data = {"]

    if user_model:
        # Générer des données pour chaque colonne requise (sauf id auto-incrémenté)
        for attr in user_model.attributes:
            if attr.is_required and not (attr.name == "id" and attr.is_auto_increment):
                if attr.name.lower() == "email":
                    name = generate_data("", 6)
                    domain = generate_data("", 6)
                    user_data_lines.append(f"        'email': '{name}@{domain.lower()}.com',")

                elif attr.name.lower() in ["password", "hashed_password"]:
                    password = generate_data("", 12)
                    user_data_lines.append(f"        'password': '{password}',")

                elif attr.name.lower() == "is_active":
                    user_data_lines.append("        'is_active': True,")

                elif attr.name.lower() == "is_superuser":
                    user_data_lines.append("        'is_superuser': False,")

                elif attr.type.lower() == "boolean":
                    user_data_lines.append(f"        '{attr.name}': {generate_random_boolean()},")

                elif attr.type.lower() in ["integer", "int"]:
                    user_data_lines.append(f"        '{attr.name}': {generate_random_integer(100)},")

                elif attr.type.lower() == "string":
                    length = attr.length or 10
                    user_data_lines.append(f"        '{attr.name}': '{generate_random_text(length)}',")

                elif attr.type.lower() == "enum" and attr.enum_name:
                    # Gérer les enums
                    enum_value = generate_data("enum", all_enums=all_enums, column=attr)
                    user_data_lines.append(f"        '{attr.name}': {enum_value},")

                else:
                    # Valeur par défaut pour les autres types
                    default_value = generate_data(attr.type, attr.length or 5)
                    if isinstance(default_value, str):
                        user_data_lines.append(f"        '{attr.name}': '{default_value}',")
                    else:
                        user_data_lines.append(f"        '{attr.name}': {default_value},")
    else:
        # Fallback si aucun modèle utilisateur n'est trouvé
        name = generate_data("", 6)
        domain = generate_data("", 6)
        password = generate_data("", 12)
        user_data_lines.extend([
            f"        'email': '{name}@{domain.lower()}.com',",
            f"        'password': '{password}',",
            "        'is_active': True,",
            "        'is_superuser': False,",
        ])

    user_data_lines.append("    }")

    # Convertir le nom du modèle en nom de table pour CRUD
    user_table_name = camel_to_snake(user_model_name)

    return [
        "    # Auth setup",
        *user_data_lines,
        f"    user = crud.{user_table_name}.create(db, obj_in=schemas.{user_model_name}Create(**user_data))",
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
        all_enums=None
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
                    fk_model, all_models, created, indent, all_enums
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
            lines.append(f"{indent}    {_literal_name(attr.name)}={_literal_value(attr, all_enums)},")
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
        all_enums=None
) -> str:
    base_ep = f"/api/v1/{generate_filename(table_name)}"
    code_lines: List[str] = []

    hdrs_kwarg = _gen_headers(other_cfg)
    fk_fields = [attr.name for attr in model.attributes if attr.is_foreign]
    fk_fields_literal = repr(fk_fields)

    for op in TEST_LIST:
        tl: List[str] = [f"\n\ndef test_{op}_{table_name}_api(client, db):",
                         f'    """{op.capitalize()} {model.name} via API."""']

        # Auth setup
        tl.extend(_gen_auth_setup(other_cfg, all_models=all_models, all_enums=all_enums))

        # ✅ Build only FK dependencies, skip self
        created = set()
        for attr in model.attributes:
            if attr.is_foreign and attr.foreign_key_class:
                fk_model = all_models[attr.foreign_key_class]
                fk_lines = _build_dependency_setup_lines(fk_model, all_models, created, all_enums=all_enums)
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
                tl.append(f"        '{column}': {_literal_value(attr, all_enums)},")
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
            time_fields = [a.name for a in model.attributes if
                           'time' in a.type.lower() and 'datetime' not in a.type.lower()]

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
              other_cfg: schemas.OtherConfigSchema, all_enums=None) -> str:
    return "\n".join([
        _gen_imports(other_cfg),
        _gen_test_api(model, table_name, all_models, other_cfg, all_enums),
    ])


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def write_test_apis(models: List[ClassModel], output_dir: str, other_cfg: schemas.OtherConfigSchema,
                    all_enums=None) -> None:
    out_dir = os.path.join(output_dir, OUTPUT_DIR.lstrip("/"))
    os.makedirs(out_dir, exist_ok=True)

    normalised = [m if isinstance(m, ClassModel) else ClassModel(**m) for m in models]
    all_models: Dict[str, ClassModel] = {m.name: m for m in normalised}

    # Trouver le modèle utilisateur pour le test de login
    user_model_name = None
    user_model = None

    for model_name, model in all_models.items():
        has_email = any(attr.name.lower() == "email" for attr in model.attributes)
        has_password = any(attr.name.lower() in ["password", "hashed_password"] for attr in model.attributes)

        if has_email and has_password:
            user_model_name = model_name
            user_model = model
            break

    if user_model_name and other_cfg.use_authentication:

        fname = f"test_login.py"
        fpath = os.path.join(out_dir, fname)
        content = generate_login_test(user_model_name, user_model, all_enums)
        final = preserve_custom_sections(fpath, content)
        with open(fpath, "w", encoding="utf-8") as fp:
            fp.write(final)
        logger.info("Generated authentication tests")

    for mdl in normalised:
        tbl = camel_to_snake(mdl.name)
        content = _gen_file(mdl, tbl, all_models, other_cfg, all_enums)
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
