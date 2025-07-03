from fastapi import status
from app.models import User
from app.core import security
from app import crud, schemas


def test_login_access_token(client, db):
    # Create a test user with hashed password
    password = "securepassword123"
    create_data = schemas.UserCreate(
        name='Test User',
        email='testlogin@example.com',
        password=password,
        is_active=True,
        is_superuser=False
    )
    user = crud.user.create(db=db, obj_in=create_data)

    # Verify user was created correctly
    assert user is not None
    assert user.email == 'testlogin@example.com'
    assert user.is_active is True  # Explicitly check active status
    assert security.verify_password(password, user.hashed_password)

    # Debug: Try authenticating directly
    authenticated_user = crud.user.authenticate(
        db, email='testlogin@example.com', password=password
    )
    assert authenticated_user is not None  # This might fail

    # Test login endpoint
    response = client.post(
        "/api/v1/login/access-token",
        data={
            "username": user.email,
            "password": password,
            "grant_type": "password"
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )

    assert response.status_code == status.HTTP_200_OK
    assert "access_token" in response.json()
