from unittest.mock import Mock
from app import extract_error


def test_extract_detail():
    """Should return the string inside the 'detail' key if it exists."""

    mock_response = Mock()
    mock_response.json.return_value = {"detail": "Error message"}
    mock_response.text = "raw body"

    result = extract_error(mock_response)
    
    assert result == "Error message"


def test_extract_error_detail_invalid_json():
    """
    Should return raw text when json() raises an exception (invalid JSON),
    even if the response has a 'detail' key.
    """

    mock_response = Mock()
    mock_response.json.side_effect = ValueError("No JSON")
    mock_response.text = "raw body"

    result = extract_error(mock_response)

    assert result == "raw body"


def test_extract_error_with_json_without_detail():
    """Should return the raw text if JSON is valid but has no 'detail' key."""

    mock_response = Mock()
    mock_response.json.return_value = {"message": "Something went wrong"}
    mock_response.text = "raw body"

    result = extract_error(mock_response)

    assert result == "raw body"

