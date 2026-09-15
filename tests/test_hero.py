def test_landing_page_returns_200(client):
    response = client.get("/")
    assert response.status_code == 200


def test_landing_page_has_hero_section(client):
    response = client.get("/")
    assert b'<section class="hero">' in response.data


def test_hero_has_cta_links_to_register_and_login(client):
    response = client.get("/")
    assert b'href="/register"' in response.data
    assert b'href="/login"' in response.data


def test_login_and_register_pages_still_return_200(client):
    assert client.get("/login").status_code == 200
    assert client.get("/register").status_code == 200
