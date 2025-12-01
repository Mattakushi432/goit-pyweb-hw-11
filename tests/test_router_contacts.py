import pytest
from httpx import AsyncClient
from unittest.mock import AsyncMock, patch

from app.main import app
from app.models import User, Contact
from app.auth import auth_service
from app.database import get_db

test_user = User(id=1, email="test@example.com", username="tester")


async def override_get_current_user():
    return test_user


app.dependency_overrides[auth_service.get_current_user] = override_get_current_user



@pytest.mark.asyncio
async def test_read_contacts_success(mocker):
    mock_get_contacts = mocker.patch(
        "app.crud.get_contacts",
        new_callable=AsyncMock
    )

    mock_contacts_data = [
        Contact(id=1, first_name="John", last_name="Doe", email="johndoe@test.com", user_id=1),
        Contact(id=2, first_name="Jane", last_name="Smith", email="janesmith@test.com", user_id=1)
    ]
    mock_get_contacts.return_value = mock_contacts_data

    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/api/contacts/")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["first_name"] == "John"
    assert "user_id" not in data[0]

    mock_get_contacts.assert_called_once()



@pytest.mark.asyncio
async def test_create_contact_success(mocker):
    mocker.patch(
        "app.crud.get_contact_by_email_or_phone",
        new_callable=AsyncMock,
        return_value=None
    )

    mock_contact = Contact(
        id=3,
        first_name="New",
        last_name="One",
        email="new@test.com",
        user_id=1
    )
    mock_create_contact = mocker.patch(
        "app.crud.create_contact",
        new_callable=AsyncMock,
        return_value=mock_contact
    )

    contact_payload = {
        "first_name": "New",
        "last_name": "One",
        "email": "new@test.com",
        "phone": "9876543210",
        "birthday": "2023-01-01"
    }

    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.post("/api/contacts/", json=contact_payload)

    assert response.status_code == 201
    assert response.json()["email"] == "new@test.com"
    mock_create_contact.assert_called_once()