from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import or_, extract, and_
from datetime import date, timedelta
from typing import List, Optional

from app.models import Contact
from app.schemas import ContactCreate, ContactUpdate


async def get_contact_by_email_or_phone(db: AsyncSession, email: str, phone: str) -> Optional[Contact]:
    """
    Проверяет, существует ли контакт с таким email или телефоном.
    """
    result = await db.execute(
        select(Contact).where(or_(Contact.email == email, Contact.phone == phone))
    )
    return result.scalars().first()


async def create_contact(db: AsyncSession, contact: ContactCreate) -> Contact:
    """
    Создает новый контакт.
    """
    db_contact = Contact(**contact.model_dump())
    db.add(db_contact)
    await db.commit()
    await db.refresh(db_contact)
    return db_contact


async def get_contact(db: AsyncSession, contact_id: int) -> Optional[Contact]:
    """
    Получает контакт по ID.
    """
    result = await db.execute(select(Contact).where(Contact.id == contact_id))
    return result.scalars().first()


async def get_contacts(db: AsyncSession, skip: int = 0, limit: int = 100) -> List[Contact]:
    """
    Получает список всех контактов с пагинацией.
    """
    result = await db.execute(select(Contact).offset(skip).limit(limit))
    return result.scalars().all()


async def update_contact(
        db: AsyncSession, contact_id: int, contact_update: ContactUpdate
) -> Optional[Contact]:
    """
    Обновляет существующий контакт.
    """
    db_contact = await get_contact(db, contact_id)
    if db_contact:
        # Используем model_dump с exclude_unset=True для PATCH-поведения
        update_data = contact_update.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_contact, key, value)

        await db.commit()
        await db.refresh(db_contact)
    return db_contact


async def delete_contact(db: AsyncSession, contact_id: int) -> Optional[Contact]:
    """
    Удаляет контакт.
    """
    db_contact = await get_contact(db, contact_id)
    if db_contact:
        await db.delete(db_contact)
        await db.commit()
    return db_contact


async def search_contacts(db: AsyncSession, query: str) -> List[Contact]:
    """
    Ищет контакты по имени, фамилии или email.
    """
    search = f"%{query}%"
    result = await db.execute(
        select(Contact).where(
            or_(
                Contact.first_name.ilike(search),
                Contact.last_name.ilike(search),
                Contact.email.ilike(search),
            )
        )
    )
    return result.scalars().all()


async def get_upcoming_birthdays(db: AsyncSession) -> List[Contact]:
    """
    Получает список контактов с днями рождения в ближайшие 7 дней.
    """
    today = date.today()
    end_date = today + timedelta(days=7)

    # Извлекаем месяц и день из даты рождения
    birthday_month = extract('month', Contact.birthday)
    birthday_day = extract('day', Contact.birthday)

    # Условие для контактов
    if today.month == end_date.month:
        # Если 7 дней не выходят за рамки текущего месяца
        condition = and_(
            birthday_month == today.month,
            birthday_day >= today.day,
            birthday_day <= end_date.day
        )
    else:
        # Если 7 дней захватывают следующий месяц (или год)
        condition_this_month = and_(
            birthday_month == today.month,
            birthday_day >= today.day
        )
        condition_next_month = and_(
            birthday_month == end_date.month,
            birthday_day <= end_date.day
        )
        condition = or_(condition_this_month, condition_next_month)

    result = await db.execute(select(Contact).where(condition))
    return result.scalars().all()