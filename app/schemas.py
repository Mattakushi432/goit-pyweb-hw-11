from pydantic import BaseModel, EmailStr
from datetime import date
from typing import Optional


class ContactBase(BaseModel):
    """
    Базовая схема Pydantic для контакта.
    """
    first_name: str
    last_name: str
    email: EmailStr
    phone: str
    birthday: date
    additional_data: Optional[str] = None


class ContactCreate(ContactBase):
    """
    Схема для создания нового контакта (используется в POST).
    """
    pass


class ContactUpdate(BaseModel):
    """
    Схема для обновления контакта (используется в PUT/PATCH).
    Все поля опциональны.
    """
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    birthday: Optional[date] = None
    additional_data: Optional[str] = None


class ContactResponse(ContactBase):
    """
    Схема для возврата данных о контакте (используется в GET).
    Включает id.
    """
    id: int

    class Config:
        from_attributes = True  # Pydantic v2
        # orm_mode = True # Pydantic v1