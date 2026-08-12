import pytest

from app import create_app
from app.config import TestConfig


@pytest.fixture()
def client():
    return create_app(TestConfig).test_client()
