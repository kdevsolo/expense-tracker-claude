def test_terms_page_returns_200(client):
    response = client.get("/terms")
    assert response.status_code == 200


def test_terms_page_contains_heading(client):
    response = client.get("/terms")
    assert b"Terms" in response.data


def test_privacy_page_returns_200(client):
    response = client.get("/privacy")
    assert response.status_code == 200


def test_privacy_page_contains_heading(client):
    response = client.get("/privacy")
    assert b"Privacy" in response.data


def test_landing_page_has_footer_links_to_terms_and_privacy(client):
    response = client.get("/")
    assert b'href="/terms"' in response.data
    assert b'href="/privacy"' in response.data


def test_existing_routes_still_return_200(client):
    assert client.get("/").status_code == 200
    assert client.get("/login").status_code == 200
    assert client.get("/register").status_code == 200
