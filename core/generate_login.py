from model_type import camel_to_snake


def generate_auth_router_module(
    user_model_name: str = "User",
    user_id_claim: str = "id",                 # what goes into the JWT sub: {"id": str(user.<user_id_claim>)}
    lookup_field_for_test_token: str = "id",   # which field to query in /test-token (e.g., "uuid" or "id")
    include_inactive_checks: bool = False,
) -> str:
    """
    Generate a FastAPI router module that provides:
      - POST /access-token
      - POST /test-token/{token}
      - POST /decode_token
      - POST /password-recovery/
      - POST /reset-password/

    The code mirrors the structure you provided, with small parametrizations.
    """

    user_table_name = camel_to_snake(user_model_name)
    inactive_check_login = (
        f"    elif not crud.{user_table_name}.is_active(user):\n"
        "        raise HTTPException(status_code=400, detail=\"Inactive user\")\n"
        if include_inactive_checks else
        f"    # elif not crud.{user_table_name}.is_active(user):\n"
        "    #     raise HTTPException(status_code=400, detail=\"Inactive user\")\n"
    )

    inactive_check_reset = (
        f"    elif not crud.{user_table_name}.is_active(user):\n"
        "        raise HTTPException(status_code=400, detail=\"Inactive user\")\n"
        if include_inactive_checks else
        f"    # elif not crud.{user_table_name}.is_active(user):\n"
        "    #     raise HTTPException(status_code=400, detail=\"Inactive user\")\n"
    )

    # f-string braces are doubled to render literal braces in the output file.
    return f'''from datetime import timedelta, datetime
from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app import crud, models, schemas
from app.api import deps
from app.core import security
from app.core.config import settings
from app.core.security import get_password_hash
from app.utils import (
    generate_password_reset_token,
    send_reset_password_email,
    verify_password_reset_token,
)

router = APIRouter()


@router.post("/access-token", response_model=schemas.Token)
def login_access_token(
    db: Session = Depends(deps.get_db), 
    form_data: OAuth2PasswordRequestForm = Depends()
) -> Any:
    """
    OAuth2 compatible token login, get an access token for future requests
    """
    user = crud.{user_table_name}.authenticate(
        db, email=form_data.username, password=form_data.password
    )
    if not user:
        raise HTTPException(status_code=400, detail="Incorrect email or password")
{inactive_check_login.rstrip()}
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    token = security.create_access_token(
        sub={{"id": str(getattr(user, "{user_id_claim}")), "email": form_data.username}},
        expires_delta=access_token_expires,
    )
    token_data = deps.get_user(token)
    user = crud.{user_table_name}.get(db=db, {lookup_field_for_test_token}=token_data.id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return {{"access_token": token, "token_type": "Bearer"}}


@router.post("/test-token/{{token}}", response_model=schemas.{user_model_name})
def test_token(token: str, db: Session = Depends(deps.get_db)) -> Any:
    """
    Test access token
    """
    token_data = deps.get_user(token)
    user = crud.{user_table_name}.get(db=db, {lookup_field_for_test_token}=token_data.id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.post("/decode_token", response_model=schemas.TokenPayload)
def test_token_decode(token_info=Depends(deps.get_token_info)) -> Any:
    """
    Decode access token
    """
    return token_info


@router.post("/password-recovery/", response_model=schemas.Msg)
def recover_password(email: str, db: Session = Depends(deps.get_db)) -> Any:
    """
    Password Recovery
    """
    user = crud.{user_table_name}.get_by_email(db, email=email)

    if not user:
        raise HTTPException(
            status_code=404,
            detail="The user with this username does not exist in the system.",
        )
    password_reset_token = generate_password_reset_token(email=email)
    send_reset_password_email(
        email_to=user.email, email=email, token=password_reset_token
    )
    return {{"msg": "Password recovery email sent"}}


@router.post("/reset-password/", response_model=schemas.Msg)
def reset_password(
    token: str = Body(...),
    new_password: str = Body(...),
    db: Session = Depends(deps.get_db),
) -> Any:
    """
    Reset password
    """
    email = verify_password_reset_token(token)
    if not email:
        raise HTTPException(status_code=400, detail="Invalid token")
    user = crud.{user_table_name}.get_by_email(db, email=email)
    if not user:
        raise HTTPException(
            status_code=404,
            detail="The user with this username does not exist in the system.",
        )
{inactive_check_reset.rstrip()}
    hashed_password = get_password_hash(new_password)
    user.hashed_password = hashed_password
    db.add(user)
    db.commit()
    return {{"msg": "Password updated successfully"}}
'''

# Example usage:
# code = generate_auth_router_module(user_model_name="User", user_id_claim="id", lookup_field_for_test_token="uuid", include_inactive_checks=False)
# with open("app/api/api_v1/endpoints/login.py", "w", encoding="utf-8") as f:
#     f.write(code)
