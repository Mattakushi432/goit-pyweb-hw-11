from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import or_, extract, and_
from datetime import date, timedelta
from typing import List, Optional

from app.models import Contact, User
from app.schemas import ContactCreate, ContactUpdate



async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
    """Отримує користувача за email."""
    result = await db.execute(select(User).where(User.email == email))
    return result.scalars().first()


async def create_user(db: AsyncSession, email: str, password: str) -> User:
    """Створює нового користувача."""
    db_user = User(email=email, hashed_password=password)
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    return db_user



async def get_contact_by_email_or_phone(db: AsyncSession, email: str, phone: str, user: User) -> Optional[Contact]:
    """Перевіряє, чи існує контакт з таким email або телефоном У ЦЬОГО КОРИСТУВАЧА."""
    result = await db.execute(
        select(Contact).where(
            and_(
                or_(Contact.email == email, Contact.phone == phone),
                Contact.user_id == user.id
            )
        )
    )
    return result.scalars().first()


async def create_contact(db: AsyncSession, contact: ContactCreate, user: User) -> Contact:
    """Створює новий контакт, прив'язаний до користувача."""
    db_contact = Contact(**contact.model_dump(), user_id=user.id)  # Прив'язка до user.id
    db.add(db_contact)
    await db.commit()
    await db.refresh(db_contact)
    return db_contact


async def get_contact(db: AsyncSession, contact_id: int, user: User) -> Optional[Contact]:
    """Отримує контакт за ID, але тільки якщо він належить користувачу."""
    result = await db.execute(
        select(Contact).where(
            and_(Contact.id == contact_id, Contact.user_id == user.id)
        )
    )
    return result.scalars().first()


async def get_contacts(db: AsyncSession, skip: int, limit: int, user: User) -> List[Contact]:
    """Отримує список всіх контактів, що належать користувачу."""
    result = await db.execute(
        select(Contact).where(Contact.user_id == user.id).offset(skip).limit(limit)
    )
    return result.scalars().all()


async def update_contact(
        db: AsyncSession, contact_id: int, contact_update: ContactUpdate, user: User
) -> Optional[Contact]:
    """Оновлює контакт, якщо він належить користувачу."""
    db_contact = await get_contact(db, contact_id, user)  # Використовує вже захищену функцію
    if db_contact:
        update_data = contact_update.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_contact, key, value)

        await db.commit()
        await db.refresh(db_contact)
    return db_contact


async def delete_contact(db: AsyncSession, contact_id: int, user: User) -> Optional[Contact]:
    """Видаляє контакт, якщо він належить користувачу."""
    db_contact = await get_contact(db, contact_id, user)  # Використовує вже захищену функцію
    if db_contact:
        await db.delete(db_contact)
        await db.commit()
    return db_contact


async def search_contacts(db: AsyncSession, query: str, user: User) -> List[Contact]:
    """Пошук серед контактів, що належать користувачу."""
    search = f"%{query}%"
    result = await db.execute(
        select(Contact).where(
            and_(
                Contact.user_id == user.id,
                or_(
                    Contact.first_name.ilike(search),
                    Contact.last_name.ilike(search),
                    Contact.email.ilike(search),
                )
            )
        )
    )
    return result.scalars().all()


async def get_upcoming_birthdays(db: AsyncSession, user: User) -> List[Contact]:
    """Дні народження серед контактів, що належать користувачу."""
    today = date.today()
    end_date = today + timedelta(days=7)

    birthday_month = extract('month', Contact.birthday)
    birthday_day = extract('day', Contact.birthday)

    if today.month == end_date.month:
        condition = and_(
            birthday_month == today.month,
            birthday_day >= today.day,
            birthday_day <= end_date.day
        )
    else:
        condition_this_month = and_(
            birthday_month == today.month,
            birthday_day >= today.day
        )
        condition_next_month = and_(
            birthday_month == end_date.month,
            birthday_day <= end_date.day
        )
        condition = or_(condition_this_month, condition_next_month)

    final_condition = and_(Contact.user_id == user.id, condition)

    result = await db.execute(select(Contact).where(final_condition))
    return result.scalars().all()

async def confirm_email(email: str, db: AsyncSession) -> None:
    """Підтверджує електронну пошту користувача, встановлюючи прапорець confirmed = True."""
    user = await get_user_by_email(db, email)
    if user:
        # Важливо: якщо ти не використовуєш Model.username, тобі, можливо, знадобиться перевірка user.confirmed
        # (хоча це робиться в роутері, краще додати тут перевірку на None)
        user.confirmed = True
        await db.commit()