from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app import schemas, crud
from app.auth import auth_service
from app.services.email import send_email  # Переконайся, що цей імпорт працює

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=schemas.UserResponse, status_code=status.HTTP_201_CREATED)
async def register_user(
        user_data: schemas.UserCreate,
        background_tasks: BackgroundTasks,  # <--- Додано для відправки пошти
        request: Request,  # <--- Додано для отримання URL
        db: AsyncSession = Depends(get_db)
):
    """
    Реєструє нового користувача та відправляє лист для підтвердження.
    """
    existing_user = await crud.get_user_by_email(db, email=user_data.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User with this email already exists"
        )

    hashed_password = auth_service.get_password_hash(user_data.password)
    new_user = await crud.create_user(db, email=user_data.email, password=hashed_password)

    # Відправка листа у фоні
    # Передаємо email як username, якщо у тебе немає окремого поля username
    background_tasks.add_task(send_email, new_user.email, new_user.email, str(request.base_url))

    return new_user


@router.post("/login", response_model=schemas.Token)
async def login_for_access_token(
        form_data: OAuth2PasswordRequestForm = Depends(),
        db: AsyncSession = Depends(get_db)
):
    """
    Аутентифікує користувача та повертає пару токенів.
    """
    user = await crud.get_user_by_email(db, email=form_data.username)

    if not user or not auth_service.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Перевірка, чи підтверджено email (опціонально, якщо хочеш заборонити вхід без підтвердження)
    if not user.confirmed:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Email not confirmed")

    data = {"sub": user.email}
    access_token = await auth_service.create_access_token(data)
    refresh_token = await auth_service.create_refresh_token(data)

    return schemas.Token(access_token=access_token, refresh_token=refresh_token)


@router.get("/refresh", response_model=schemas.Token)
async def refresh_access_token(
        refresh_token: str = Depends(auth_service.oauth2_scheme),  # Виправлено на auth_service.oauth2_scheme
        db: AsyncSession = Depends(get_db)
):
    """
    Оновлює access_token за допомогою refresh_token.
    """
    email = await auth_service.decode_refresh_token(
        refresh_token)  # Припускаю, що у тебе є такий метод або загальний decode
    user = await crud.get_user_by_email(db, email)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    data = {"sub": user.email}
    new_access_token = await auth_service.create_access_token(data)
    new_refresh_token = await auth_service.create_refresh_token(data)

    return schemas.Token(access_token=new_access_token, refresh_token=new_refresh_token)


# --- Новий маршрут для підтвердження пошти ---
@router.get('/confirmed_email/{token}')
async def confirmed_email(token: str, db: AsyncSession = Depends(get_db)):
    """
    Підтверджує електронну пошту користувача за токеном.
    """
    email = await auth_service.get_email_from_token(token)  # Тобі треба додати цю функцію в auth_service
    user = await crud.get_user_by_email(db, email)

    if user is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Verification error")

    if user.confirmed:
        return {"message": "Your email is already confirmed"}

    await crud.confirm_email(email, db)  # Тобі треба додати цю функцію в crud
    return {"message": "Email confirmed"}