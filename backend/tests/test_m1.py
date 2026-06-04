import pytest
from fastapi.testclient import TestClient
from sqlmodel import SQLModel, create_engine, Session
from sqlmodel.pool import StaticPool

from app.main import app
from app.database import get_session


@pytest.fixture(name="session")
def session_fixture():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


@pytest.fixture(name="client")
def client_fixture(session: Session):
    def get_session_override():
        return session

    app.dependency_overrides[get_session] = get_session_override
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


# ─── Healthcheck ────────────────────────────────────────────────────────────

def test_healthcheck(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


# ─── Account CRUD ────────────────────────────────────────────────────────────

def test_create_account(client):
    response = client.post("/api/v1/accounts", json={"name": "Zerodha"})
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Zerodha"
    assert data["cash_balance"] == 0.0
    assert "id" in data


def test_create_account_duplicate(client):
    client.post("/api/v1/accounts", json={"name": "Zerodha"})
    response = client.post("/api/v1/accounts", json={"name": "Zerodha"})
    assert response.status_code == 409


def test_list_accounts(client):
    client.post("/api/v1/accounts", json={"name": "Zerodha"})
    client.post("/api/v1/accounts", json={"name": "Groww"})
    response = client.get("/api/v1/accounts")
    assert response.status_code == 200
    assert len(response.json()) == 2


def test_get_account(client):
    create_resp = client.post("/api/v1/accounts", json={"name": "Zerodha"})
    account_id = create_resp.json()["id"]
    response = client.get(f"/api/v1/accounts/{account_id}")
    assert response.status_code == 200
    assert response.json()["name"] == "Zerodha"


def test_get_account_not_found(client):
    response = client.get("/api/v1/accounts/999")
    assert response.status_code == 404


def test_update_account(client):
    create_resp = client.post("/api/v1/accounts", json={"name": "OldName"})
    account_id = create_resp.json()["id"]
    response = client.put(f"/api/v1/accounts/{account_id}", json={"name": "NewName"})
    assert response.status_code == 200
    assert response.json()["name"] == "NewName"


def test_update_account_duplicate_name(client):
    client.post("/api/v1/accounts", json={"name": "Zerodha"})
    create_resp = client.post("/api/v1/accounts", json={"name": "Groww"})
    account_id = create_resp.json()["id"]
    response = client.put(f"/api/v1/accounts/{account_id}", json={"name": "Zerodha"})
    assert response.status_code == 409


def test_delete_account(client):
    create_resp = client.post("/api/v1/accounts", json={"name": "Zerodha"})
    account_id = create_resp.json()["id"]
    response = client.delete(f"/api/v1/accounts/{account_id}")
    assert response.status_code == 204
    # Verify it's gone
    get_resp = client.get(f"/api/v1/accounts/{account_id}")
    assert get_resp.status_code == 404


def test_delete_account_not_found(client):
    response = client.delete("/api/v1/accounts/999")
    assert response.status_code == 404


# ─── Asset CRUD ──────────────────────────────────────────────────────────────

def test_create_asset_uppercase(client):
    response = client.post("/api/v1/assets", json={"ticker": "aapl", "name": "Apple Inc."})
    assert response.status_code == 201
    data = response.json()
    assert data["ticker"] == "AAPL"
    assert data["name"] == "Apple Inc."


def test_create_asset_duplicate(client):
    client.post("/api/v1/assets", json={"ticker": "AAPL", "name": "Apple Inc."})
    response = client.post("/api/v1/assets", json={"ticker": "aapl", "name": "Apple"})
    assert response.status_code == 409


def test_list_assets(client):
    client.post("/api/v1/assets", json={"ticker": "AAPL", "name": "Apple Inc."})
    client.post("/api/v1/assets", json={"ticker": "MSFT", "name": "Microsoft"})
    response = client.get("/api/v1/assets")
    assert response.status_code == 200
    assert len(response.json()) == 2


def test_get_asset(client):
    create_resp = client.post("/api/v1/assets", json={"ticker": "AAPL", "name": "Apple Inc."})
    asset_id = create_resp.json()["id"]
    response = client.get(f"/api/v1/assets/{asset_id}")
    assert response.status_code == 200
    assert response.json()["ticker"] == "AAPL"


def test_get_asset_not_found(client):
    response = client.get("/api/v1/assets/999")
    assert response.status_code == 404


def test_delete_asset(client):
    create_resp = client.post("/api/v1/assets", json={"ticker": "AAPL", "name": "Apple Inc."})
    asset_id = create_resp.json()["id"]
    response = client.delete(f"/api/v1/assets/{asset_id}")
    assert response.status_code == 204
    get_resp = client.get(f"/api/v1/assets/{asset_id}")
    assert get_resp.status_code == 404


def test_delete_asset_not_found(client):
    response = client.delete("/api/v1/assets/999")
    assert response.status_code == 404
