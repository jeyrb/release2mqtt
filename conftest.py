import pytest
from unittest.mock import patch, Mock


@pytest.fixture
def mock_mqtt_client():
    mock = Mock(spec="mqtt.Client")
    return mock
