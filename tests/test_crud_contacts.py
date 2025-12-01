import unittest
from unittest.mock import AsyncMock, MagicMock

from sqlalchemy.ext.asyncio import AsyncSession

from app import crud
from app.schemas import ContactCreate
from app.models import User, Contact


class TestContactsCRUD(unittest.IsolatedAsyncioTestCase):

    def setUp(self):
        self.session = MagicMock(spec=AsyncSession)

        self.user = User(id=1, email="test@example.com")

        self.contact_data = ContactCreate(
            first_name="Test",
            last_name="User",
            email="contact@example.com",
            phone="1234567890",
            birthday="2000-01-01",
            notes="Test contact"
        )


    async def test_create_contact_success(self):
        mock_contact = Contact(
            id=1,
            **self.contact_data.model_dump(),
            user_id=self.user.id
        )

        self.session.refresh = AsyncMock(return_value=None)

        self.session.commit = AsyncMock()

        result = await crud.create_contact(self.session, self.contact_data, self.user)

        self.session.commit.assert_called_once()

        self.assertEqual(result.email, "contact@example.com")
        self.assertEqual(result.user_id, self.user.id)


    async def test_get_contacts(self):
        contacts = [
            Contact(id=1, email="a@a.com", user_id=self.user.id),
            Contact(id=2, email="b@b.com", user_id=self.user.id),
        ]

        mock_result = MagicMock()
        mock_result.scalars.return_value.all = AsyncMock(return_value=contacts)
        self.session.execute = AsyncMock(return_value=mock_result)

        result = await crud.get_contacts(self.session, user=self.user, skip=0, limit=10)

        self.assertEqual(len(result), 2)
        self.assertEqual(result[0].email, "a@a.com")


if __name__ == '__main__':
    unittest.main()