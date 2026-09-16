import re

import pytest
from werkzeug.security import check_password_hash

from database.db import get_db, get_user_by_email

VALID_FORM = {
    "name": "Nitish Kumar",
    "email": "nitish@example.com",
    "password": "supersecret",
}


def user_count():
    conn = get_db()
    try:
        return conn.execute("SELECT COUNT(*) AS c FROM users").fetchone()["c"]
    finally:
        conn.close()


def test_get_register_returns_200(client):
    response = client.get("/register")
    assert response.status_code == 200


def test_get_register_renders_form_with_empty_fields(client):
    response = client.get("/register")
    assert b'name="name"' in response.data
    assert b'name="email"' in response.data
    assert b'name="password"' in response.data
    assert b'value=""' in response.data
    assert b"auth-error" not in response.data


def test_get_register_form_action_uses_url_for(client):
    response = client.get("/register")
    assert b'action="/register"' in response.data


def test_login_form_action_uses_url_for(client):
    response = client.get("/login")
    assert b'action="/login"' in response.data


def test_valid_registration_redirects_to_login(client):
    response = client.post("/register", data=VALID_FORM)
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")


def test_valid_registration_creates_user_row(client):
    client.post("/register", data=VALID_FORM)
    user = get_user_by_email("nitish@example.com")
    assert user is not None
    assert user["name"] == "Nitish Kumar"


def test_password_is_hashed_not_plaintext(client):
    client.post("/register", data=VALID_FORM)
    user = get_user_by_email("nitish@example.com")
    assert user["password_hash"] != "supersecret"
    assert user["password_hash"].startswith(("scrypt:", "pbkdf2:"))
    assert check_password_hash(user["password_hash"], "supersecret")


def test_email_is_normalised_to_lowercase(client):
    client.post(
        "/register",
        data={**VALID_FORM, "email": "  NiTiSh@Example.COM  "},
    )
    assert get_user_by_email("nitish@example.com") is not None


def test_duplicate_email_is_rejected(client):
    client.post("/register", data=VALID_FORM)
    response = client.post("/register", data=VALID_FORM)
    assert response.status_code == 200
    assert b"An account with that email already exists." in response.data


def test_duplicate_email_does_not_create_second_row(client):
    client.post("/register", data=VALID_FORM)
    before = user_count()
    client.post("/register", data=VALID_FORM)
    assert user_count() == before


def test_seeded_demo_email_is_rejected(client):
    response = client.post(
        "/register", data={**VALID_FORM, "email": "demo@spendly.com"}
    )
    assert b"An account with that email already exists." in response.data


def test_empty_form_shows_required_error(client):
    response = client.post(
        "/register", data={"name": "", "email": "", "password": ""}
    )
    assert response.status_code == 200
    assert b"All fields are required." in response.data


def test_empty_form_creates_no_user(client):
    before = user_count()
    client.post("/register", data={"name": "", "email": "", "password": ""})
    assert user_count() == before


def test_short_password_is_rejected(client):
    response = client.post("/register", data={**VALID_FORM, "password": "short12"})
    assert b"Password must be at least 8 characters." in response.data
    assert get_user_by_email("nitish@example.com") is None


def test_password_of_exactly_eight_chars_is_accepted(client):
    response = client.post("/register", data={**VALID_FORM, "password": "12345678"})
    assert response.status_code == 302


def test_email_without_tld_is_rejected(client):
    response = client.post("/register", data={**VALID_FORM, "email": "nitish@example"})
    assert b"Please enter a valid email address." in response.data
    assert user_count() == 1


def test_email_with_dot_only_in_local_part_is_rejected(client):
    response = client.post(
        "/register", data={**VALID_FORM, "email": "nitish.kumar@example"}
    )
    assert b"Please enter a valid email address." in response.data


@pytest.mark.parametrize(
    "bad_email",
    [
        "a@@b.com",
        "@example.com",
        "nitish@.com",
        "nitish@example.",
        ".@.",
        "nitish@exa mple.com",
    ],
)
def test_malformed_emails_are_rejected(client, bad_email):
    response = client.post("/register", data={**VALID_FORM, "email": bad_email})
    assert b"Please enter a valid email address." in response.data
    assert user_count() == 1


@pytest.mark.parametrize("ok_email", ["a@b.co", "first.last@sub.example.com"])
def test_valid_emails_are_accepted(client, ok_email):
    response = client.post("/register", data={**VALID_FORM, "email": ok_email})
    assert response.status_code == 302


def test_failed_submit_repopulates_name_and_email(client):
    response = client.post("/register", data={**VALID_FORM, "password": "short12"})
    assert b'value="Nitish Kumar"' in response.data
    assert b'value="nitish@example.com"' in response.data


def test_failed_submit_does_not_repopulate_password(client):
    response = client.post("/register", data={**VALID_FORM, "password": "short12"})
    password_input = re.search(
        r'<input[^>]*name="password"[^>]*>', response.data.decode()
    )
    assert password_input is not None
    assert "value=" not in password_input.group(0)


def test_stub_routes_unchanged(client):
    assert b"Logout" in client.get("/logout").data
    assert b"Profile page" in client.get("/profile").data
    assert b"Add expense" in client.get("/expenses/add").data
    assert b"Edit expense" in client.get("/expenses/1/edit").data
    assert b"Delete expense" in client.get("/expenses/1/delete").data
