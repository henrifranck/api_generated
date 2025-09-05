# -*- coding: utf-8 -*-
"""test_api_generator.py – v2 (modified)

Generate FastAPI integration tests (CRUD via HTTP) for every SQLAlchemy
ClassModel. FK‑aware, supports optional JWT auth. Now generates dict-based test data for the main model.
"""
from __future__ import annotations

import logging
from typing import List, Dict

from schemas import ClassModel
from model_type import  camel_to_snake
from utils.generate_data_test import generate_data


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helper generators (imports / auth / headers)
# ---------------------------------------------------------------------------

def generate_login_test(user_model_name: str, user_model: ClassModel, all_enums: List[Dict] = None) -> str:
    """Generate dynamic login test based on user model structure"""
    print("generate Login test", all_enums)
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

    # Build asserts for required fields
    required_asserts = []
    for attr in user_model.attributes:
        # Skip auto IDs
        if attr.name == "id" and attr.is_auto_increment:
            continue
        value = None
        # Special cases
        if attr.name.lower() == email_field:
            value = "'testlogin@example.com'"
        elif attr.name.lower() in [password_field, hashed_password_field]:
            value = f"'{password_value}'"
        else:
            # Always fill if required
            if attr.is_required:
                # Delegate to your dynamic generator
                value = generate_data(
                    attr.type,
                    length=attr.length or 5,
                    all_enums=all_enums,
                    column=attr,
                )

                # Ensure string-like values are quoted
                if isinstance(value, str) and not value.startswith("'"):
                    value = f"'{value}'"

                required_asserts.append(f"    assert user.{attr.name} == {value}")
            else:
                continue
        if attr.name.lower() == "hashed_password":
            test_data_lines.append(f"        password={value},")
        else:
            test_data_lines.append(f"        {attr.name}={value},")

    test_data_str = "\n".join(test_data_lines)
    required_asserts_str = "\n".join(required_asserts)

    return f"""
from app import crud
from app import schemas
from app.core import security
from fastapi import status


def test_login_access_token(client, db):
    # Create a test user with hashed password
    password = "{password_value}"
    create_data = schemas.{user_model_name}Create(
{test_data_str}
    )
    user = crud.{user_table_name}.create(db=db, obj_in=create_data)

    # Verify user was created correctly
    assert user is not None
{required_asserts_str}
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
