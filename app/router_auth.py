from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app import schemas, crud
from app.auth import auth_service

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=schemas.UserResponse, status_code=status.HTTP_201_CREATED)
async def register_user(
        user_data: schemas.UserCreate, db: AsyncSession = Depends(get_db)
):
    """
    Реєструє нового користувача.
    Перевіряє, чи email вже існує (помилка 409).
    """
    existing_user = await crud.get_user_by_email(db, email=user_data.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User with this email already exists"
        )

    hashed_password = auth_service.get_password_hash(user_data.password)
    new_user = await crud.create_user(db, email=user_data.email, password=hashed_password)
    return new_user


@router.post("/login", response_model=schemas.Token)
async def login_for_access_token(
        form_data: OAuth2PasswordRequestForm = Depends(),
        db: AsyncSession = Depends(get_db)
):
    """
    Аутентифікує користувача та повертає пару токенів (access та refresh).
    """
    # form_data.username - це email, так вимагає OAuth2
    user = await crud.get_user_by_email(db, email=form_data.username)

    if not user or not auth_service.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Створюємо токени
    data = {"sub": user.email}
    access_token = await auth_service.create_access_token(data)
    refresh_token = await auth_service.create_refresh_token(data)

    return schemas.Token(access_token=access_token, refresh_token=refresh_token)


@router.get("/refresh", response_model=schemas.Token)
async def refresh_access_token(
        refresh_token: str = Depends(oauth2_scheme),  # Очікуємо refresh токен в хедері
        db: AsyncSession = Depends(get_db)
):
    """
    Оновлює access_token за допомогою refresh_token.
    """
    email = await auth_service.decode_token(refresh_token)  # Перевіряємо refresh токен
    user = await crud.get_user_by_email(db, email)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    # Створюємо нову пару токенів
    data = {"sub": user.email}
    new_access_token = await auth_service.create_access_token(data)
    new_refresh_token = await auth_service.create_refresh_token(data)

    return schemas.Token(access_token=new_access_token, refresh_token=new_refresh_token)