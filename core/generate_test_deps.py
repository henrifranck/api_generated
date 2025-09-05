# -*- coding: utf-8 -*-
from __future__ import annotations

import logging
from typing import List, Dict, Optional

from schemas import ClassModel
from model_type import camel_to_snake
from utils.generate_data_test import generate_data

logger = logging.getLogger(__name__)


def generate_deps_tests(user_model_name: str, user_model: ClassModel, all_enums: Optional[List[Dict]] = None) -> str:
    """
    Generate tests for app.api.deps:
      - get_current_user
      - get_current_active_user
      - (optional) get_current_active_superuser if the model contains an is_superuser field

    The function builds user_data dicts dynamically from the model attributes,
    using generate_data(type, length, all_enums, column) for all required fields
    (except deterministic overrides: email, hashed_password, is_active / is_superuser).
    """

    user_table_name = camel_to_snake(user_model_name)

    # Canonical field names (discover from attributes)
    email_field = "email"
    hashed_password_field = "hashed_password"
    is_active_field = None
    is_superuser_field = None

    for attr in user_model.attributes:
        low = attr.name.lower()
        if low == "email":
            email_field = attr.name
        elif low == "hashed_password":
            hashed_password_field = attr.name
        elif low == "is_active":
            is_active_field = attr.name
        elif low == "is_superuser":
            is_superuser_field = attr.name

    # Helper: build a dict of "key=value" lines for user creation
    def _build_user_data_lines(
        required_email_value: str,
        force_is_active: Optional[bool] = None,
        force_is_superuser: Optional[bool] = None,
    ) -> List[str]:
        lines = []
        for attr in user_model.attributes:
            # skip auto-increment ID at creation time
            if attr.name == "id" and getattr(attr, "is_auto_increment", False):
                continue

            # Determine the value source:
            # - email => deterministic test email
            # - hashed_password => get_password_hash("testpassword")
            # - is_active / is_superuser => forced value when requested
            # - required fields => generate_data(...)
            # - optional fields => omit from minimal fixtures
            low = attr.name.lower()

            # email
            if low == email_field.lower():
                value = f"'{required_email_value}'"
                lines.append(f'        "{attr.name}": {value},')
                continue

            # hashed_password
            if low == hashed_password_field.lower():
                # hashed password must be created at runtime
                value = "security.get_password_hash('testpassword')"
                lines.append(f'        "{attr.name}": {value},')
                continue

            # is_active (only if forced)
            if is_active_field and low == is_active_field.lower() and force_is_active is not None:
                value = "True" if force_is_active else "False"
                lines.append(f'        "{attr.name}": {value},')
                continue

            # is_superuser (only if forced)
            if is_superuser_field and low == is_superuser_field.lower() and force_is_superuser is not None:
                value = "True" if force_is_superuser else "False"
                lines.append(f'        "{attr.name}": {value},')
                continue

            # Other required fields -> generate dynamically
            if getattr(attr, "is_required", False):
                gen = generate_data(
                    attr.type,
                    length=(attr.length or 5),
                    all_enums=all_enums,
                    column=attr,
                )
                # Quote plain strings when necessary (ENUMs already returned quoted in your generate_data)
                if isinstance(gen, str) and not gen.startswith("'"):
                    gen = f"'{gen}'"
                lines.append(f'        "{attr.name}": {gen},')

        return lines

    # Build the three blocks (superuser is conditional)
    # 1) get_current_user
    user_data_lines_current = "\n".join(_build_user_data_lines(required_email_value="testcurent@example.com"))

    # 2) get_current_active_user (force is_active True if field exists)
    user_data_lines_active = "\n".join(
        _build_user_data_lines(
            required_email_value="testactive@example.com",
            force_is_active=True if is_active_field else None,
        )
    )

    # 3) get_current_active_superuser (only if model has is_superuser)
    include_superuser = bool(is_superuser_field)
    user_data_lines_super = ""
    if include_superuser:
        user_data_lines_super = "\n".join(
            _build_user_data_lines(
                required_email_value="adminsupper@example.com",
                force_is_superuser=True,
            )
        )

    # Template
    superuser_test_block = (
        f"""
def test_get_current_active_superuser(db, client):
    # Create a test superuser
    user_data = {{
{user_data_lines_super}
    }}
    user = {user_model_name}(**user_data)
    db.add(user)
    db.commit()
    db.refresh(user)

    # Test get_current_active_superuser
    current_user = get_current_active_superuser(current_user=user)
    assert current_user.{is_superuser_field}
"""
        if include_superuser
        else
        # If not available on model, emit a commented template for clarity
        f"""
# def test_get_current_active_superuser(db, client):
#     # Skipped: your {user_model_name} model has no 'is_superuser' field.
#     pass
"""
    )

    return f'''# Auto-generated tests for app.api.deps (model: {user_model_name})
from fastapi import HTTPException
from jose import jwt
from app.api.deps import get_current_user, get_current_active_user, get_current_active_superuser
from app.core import security
from app.models import {user_model_name}


def test_get_current_user(db, client):
    # Create a test user
    user_data = {{
{user_data_lines_current}
    }}
    user = {user_model_name}(**user_data)
    db.add(user)
    db.commit()
    db.refresh(user)

    # Generate a token for the user
    token = security.create_access_token(sub={{"id": str(user.id), "email": user.{email_field}}})

    # Test get_current_user
    current_user = get_current_user(db=db, token=token)
    assert current_user.{email_field} == user.{email_field}


def test_get_current_active_user(db, client):
    # Create a test user
    user_data = {{
{user_data_lines_active}
    }}
    user = {user_model_name}(**user_data)
    db.add(user)
    db.commit()
    db.refresh(user)

    # Generate a token for the user
    token = security.create_access_token(sub={{"id": str(user.id), "email": user.{email_field}}})

    # Test get_current_active_user
    current_user = get_current_active_user(current_user=user)
    {'assert current_user.' + is_active_field if is_active_field else 'assert hasattr(current_user, "is_active") and current_user.is_active'}


{superuser_test_block}'''
