from unittest.mock import Mock

import pytest


@pytest.fixture
def mock_mqtt_client() -> Mock:
    mock = Mock(spec="mqtt.Client")
    return mock
