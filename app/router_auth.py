from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Request, UploadFile, File
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app import schemas, crud
from app.auth import auth_service
from app.services.email import send_email, send_reset_password_email
import cloudinary
import cloudinary.uploader
from app.config import settings
from app.models import User

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=schemas.UserResponse, status_code=status.HTTP_201_CREATED)
async def register_user(
        user_data: schemas.UserCreate,
        background_tasks: BackgroundTasks,
        request: Request,
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

    if not user.confirmed:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Email not confirmed")

    data = {"sub": user.email}
    access_token = await auth_service.create_access_token(data)
    refresh_token = await auth_service.create_refresh_token(data)

    return schemas.Token(access_token=access_token, refresh_token=refresh_token)


@router.get("/refresh", response_model=schemas.Token)
async def refresh_access_token(
        refresh_token: str = Depends(auth_service.oauth2_scheme),
        db: AsyncSession = Depends(get_db)
):
    """
    Оновлює access_token за допомогою refresh_token.
    """
    email = await auth_service.decode_refresh_token(
        refresh_token)
    user = await crud.get_user_by_email(db, email)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    data = {"sub": user.email}
    new_access_token = await auth_service.create_access_token(data)
    new_refresh_token = await auth_service.create_refresh_token(data)

    return schemas.Token(access_token=new_access_token, refresh_token=new_refresh_token)


@router.get('/confirmed_email/{token}')
async def confirmed_email(token: str, db: AsyncSession = Depends(get_db)):
    """
    Підтверджує електронну пошту користувача за токеном.
    """
    email = await auth_service.get_email_from_token(token)
    user = await crud.get_user_by_email(db, email)

    if user is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Verification error")

    if user.confirmed:
        return {"message": "Your email is already confirmed"}

    await crud.confirm_email(email, db)
    return {"message": "Email confirmed"}


@router.patch("/avatar", response_model=schemas.UserResponse)
async def update_avatar_user(
        file: UploadFile = File(),
        current_user: User = Depends(auth_service.get_current_user),
        db: AsyncSession = Depends(get_db)
):
    """
    Оновлює аватар користувача, завантажуючи файл у Cloudinary.
    """
    cloudinary.config(
        cloud_name=settings.cloudinary_name,
        api_key=settings.cloudinary_api_key,
        api_secret=settings.cloudinary_api_secret,
        secure=True
    )

    public_id = f'goit-pyweb-hw-13/{current_user.email}'
    try:
        r = cloudinary.uploader.upload(
            file.file,
            public_id=public_id,
            overwrite=True,
            folder='goit-pyweb-hw-13'
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Cloudinary upload failed: {e}"
        )

    src_url = cloudinary.CloudinaryImage(r['public_id']).build_url(
        width=250,
        height=250,
        crop='fill',
        version=r.get('version')
    )
    user = await crud.update_avatar_url(current_user.email, src_url, db)


    user_key = f"user:{current_user.email}"
    await auth_service.redis_client.delete(user_key)

    return user


@router.post("/request_reset_password", status_code=status.HTTP_202_ACCEPTED)
async def request_reset_password(
        email_data: schemas.RequestReset,  
        background_tasks: BackgroundTasks,
        request: Request,
        db: AsyncSession = Depends(get_db)
):
    """
    Приймає email і надсилає лист для скидання паролю.
    """
    user = await crud.get_user_by_email(db, email=email_data.email)

    if user:
        reset_token = await auth_service.create_reset_token({"sub": user.email})

        background_tasks.add_task(
            send_reset_password_email,
            user.email,
            user.email,  
            reset_token,
            str(request.base_url)
        )


    return {"message": "If the user exists, a password reset email has been sent."}



@router.post("/reset_password/{token}", status_code=status.HTTP_200_OK)
async def reset_password(
        token: str,
        new_password_data: schemas.NewPassword,
        db: AsyncSession = Depends(get_db)
):
    """
    Встановлює новий пароль, використовуючи токен скидання.
    """
    try:
        email = await auth_service.get_email_from_token(token)  # Використовуємо існуючу функцію декодування
    except HTTPException:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired token")

    user = await crud.get_user_by_email(db, email=email)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    hashed_password = auth_service.get_password_hash(new_password_data.password)

    await crud.update_password(user, hashed_password, db)

    await auth_service.redis_client.delete(f"user:{user.email}")

    return {"message": "Password successfully reset."}
