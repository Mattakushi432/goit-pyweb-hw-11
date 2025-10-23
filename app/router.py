from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app import crud, schemas
from app.database import get_db

router = APIRouter(prefix="/contacts", tags=["Contacts"])


@router.post("/", response_model=schemas.ContactResponse, status_code=status.HTTP_201_CREATED)
async def create_contact(
    contact: schemas.ContactCreate, db: AsyncSession = Depends(get_db)
):
    """
    Создать новый контакт.
    """
    db_contact = await crud.get_contact_by_email_or_phone(db, email=contact.email, phone=contact.phone)
    if db_contact:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email or phone number already registered"
        )
    return await crud.create_contact(db=db, contact=contact)


@router.get("/", response_model=List[schemas.ContactResponse])
async def read_contacts(
    skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)
):
    """
    Получить список всех контактов.
    """
    contacts = await crud.get_contacts(db, skip=skip, limit=limit)
    return contacts


@router.get("/search", response_model=List[schemas.ContactResponse])
async def search_contacts(
    query: str = Query(..., min_length=1), db: AsyncSession = Depends(get_db)
):
    """
    Поиск контактов по имени, фамилии или email.
    """
    contacts = await crud.search_contacts(db, query=query)
    return contacts


@router.get("/birthdays", response_model=List[schemas.ContactResponse])
async def get_upcoming_birthdays(db: AsyncSession = Depends(get_db)):
    """
    Получить список контактов с днями рождения в ближайшие 7 дней.
    """
    contacts = await crud.get_upcoming_birthdays(db)
    return contacts


@router.get("/{contact_id}", response_model=schemas.ContactResponse)
async def read_contact(contact_id: int, db: AsyncSession = Depends(get_db)):
    """
    Получить один контакт по ID.
    """
    db_contact = await crud.get_contact(db, contact_id=contact_id)
    if db_contact is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Contact not found"
        )
    return db_contact


@router.put("/{contact_id}", response_model=schemas.ContactResponse)
async def update_contact(
    contact_id: int,
    contact: schemas.ContactUpdate,
    db: AsyncSession = Depends(get_db),
):
    """
    Обновить существующий контакт.
    """
    db_contact = await crud.update_contact(db, contact_id=contact_id, contact_update=contact)
    if db_contact is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Contact not found"
        )
    return db_contact


@router.delete("/{contact_id}", response_model=schemas.ContactResponse)
async def delete_contact(contact_id: int, db: AsyncSession = Depends(get_db)):
    """
    Удалить контакт.
    """
    db_contact = await crud.delete_contact(db, contact_id=contact_id)
    if db_contact is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Contact not found"
        )
    return db_contact