from unittest.mock import MagicMock, patch

from sqlalchemy import create_engine, inspect
from sqlmodel import Session, SQLModel

from src.models import User
from src.models.database import init_db


class TestInitDB:
    def test_init_db_creates_tables(self):
        """Test that init_db creates all tables"""
        test_engine = create_engine("sqlite:///:memory:")

        with patch("src.models.database.engine", test_engine):
            init_db()

            inspector = inspect(test_engine)
            table_names = inspector.get_table_names()

            assert "user" in table_names
            assert "project" in table_names

    def test_init_db_calls_create_all(self):
        """Test that init_db calls SQLModel.metadata.create_all"""
        mock_engine = MagicMock()

        with patch("src.models.database.engine", mock_engine):
            with patch.object(SQLModel.metadata, "create_all") as mock_create_all:
                init_db()
                mock_create_all.assert_called_once_with(mock_engine)

    def test_init_db_idempotent(self):
        """Test that calling init_db multiple times works"""
        test_engine = create_engine("sqlite:///:memory:")

        with patch("src.models.database.engine", test_engine):
            init_db()
            init_db()  # Should not raise

            inspector = inspect(test_engine)
            assert len(inspector.get_table_names()) > 0

    def test_tables_functional_after_init(self):
        """Test that tables work after initialization"""
        import uuid

        test_engine = create_engine("sqlite:///:memory:")

        with patch("src.models.database.engine", test_engine):
            init_db()

            with Session(test_engine) as session:
                user_id = uuid.uuid4()
                user = User(user_id=user_id, name="Test", email="test@example.com")
                session.add(user)
                session.commit()

                retrieved = session.get(User, user_id)
                assert retrieved is not None
                assert retrieved.name == "Test"
