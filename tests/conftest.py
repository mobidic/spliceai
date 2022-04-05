import pytest
from SpliceAiVisualApp import create_app


@pytest.fixture
def app():
    app = create_app({
        'TESTING': True,
        'SECRET_KEY': 'test',
        'WTF_CSRF_ENABLED': False,
    })
    yield app
