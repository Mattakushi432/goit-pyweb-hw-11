from sqlalchemy import Column, Integer, String, Date, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from app.database import Base


class User(Base):
    """
    Модель SQLAlchemy для користувача.
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)

    contacts = relationship("Contact", back_populates="user")

    confirmed = Column(Boolean, nullable=False, default=False)
    avatar = Column(String(255), nullable=True)


class Contact(Base):
    """
    Модель SQLAlchemy для контакту.
    """
    __tablename__ = "contacts"

    id = Column(Integer, primary_key=True, index=True)
    first_name = Column(String, index=True)
    last_name = Column(String, index=True)
    email = Column(String, index=True)
    phone = Column(String, index=True)
    birthday = Column(Date)
    additional_data = Column(String, nullable=True)

    # --- Нове поле ---
    # Зовнішній ключ, що посилається на 'users.id'
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Зв'язок: контакт належить одному користувачеві
    user = relationship("User", back_populates="contacts")