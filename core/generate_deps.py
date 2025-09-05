from model_type import camel_to_snake


def generate_deps_module(user_model_name: str = "User") -> str:
    """
    Generate the FastAPI deps module for authentication and user retrieval.

    Args:
        user_model_name: Name of the SQLAlchemy model for users (default: "User")
    """
    user_table_name = camel_to_snake(user_model_name)
    return f'''from typing import Generator

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app import crud, models, schemas
from app.core import security
from app.core.config import settings
from app.db.session import SessionLocal


reusable_oauth2 = OAuth2PasswordBearer(
    tokenUrl=f"{{settings.API_V1_STR}}/login/access-token"
)


def get_db() -> Generator:
    try:
        db = SessionLocal()
        yield db
    finally:
        db.close()


def get_current_user(
    db: Session = Depends(get_db),
    token: str = Depends(reusable_oauth2)
) -> models.{user_model_name}:
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[security.ALGORITHM]
        )
        token_data = schemas.TokenPayload(**payload)
    except (jwt.JWTError, ValidationError):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Could not validate credentials",
        )

    user = crud.{user_table_name}.get(db, id=token_data.id)
    if not user:
        raise HTTPException(status_code=403, detail="User not found")
    return user


def get_user(token: str) -> models.{user_model_name}:
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[security.ALGORITHM]
        )
        token_data = schemas.TokenPayload(**payload)
    except (jwt.JWTError, ValidationError):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Could not validate credentials",
        )
    return token_data


def get_token_info(token: str = Depends(reusable_oauth2)):
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[security.ALGORITHM]
        )
        token_data = schemas.TokenPayload(**payload)
    except (jwt.JWTError, ValidationError):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Could not validate credentials",
        )
    return token_data


def get_current_active_user(
    current_user: models.{user_model_name} = Depends(get_current_user),
) -> models.{user_model_name}:
    if not crud.{user_table_name}.is_active(current_user):
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


def get_current_active_superuser(
    current_user: models.{user_model_name} = Depends(get_current_user),
) -> models.{user_model_name}:
    if not crud.{user_table_name}.is_superuser(current_user):
        raise HTTPException(
            status_code=400, detail="The user doesn't have enough privileges"
        )
    return current_user
'''
