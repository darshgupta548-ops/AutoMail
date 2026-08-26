"""Minimal validation tests for the Flask scaffold."""

from app import app


def test_root_responds_successfully():
    response = app.test_client().get("/")
    assert response.status_code == 200
    assert response.get_data(as_text=True) == "AUTO-MAIL is running."
