"""
Integration tests — full HTTP request cycle through FastAPI endpoints.

Strategy:
  - FastAPI TestClient (sync) with two dependency overrides:
      1. get_current_user  → returns a canned test user (no JWT required)
      2. get_db            → yields a SQLite in-memory session (no Postgres required)
  - ML engine factories (lru_cache) overridden per-test via app.dependency_overrides.
  - Redis is already mocked at module level by conftest.py.

Run:
  pytest tests/test_api_integration.py -m integration -v
"""

import os
# Must be set BEFORE any app code imports app.Db.connections (which calls create_engine)
os.environ.setdefault("DATABASE_URL", "sqlite://")

import pytest
from unittest.mock import MagicMock
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


# ── In-memory SQLite DB ───────────────────────────────────────────────────────

_engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
_TestSession = sessionmaker(autocommit=False, autoflush=False, bind=_engine)


def _get_test_db():
    db = _TestSession()
    try:
        yield db
    finally:
        db.close()


def _init_tables():
    """Create DW tables in the in-memory SQLite DB (best-effort)."""
    try:
        from setup_db import Base
        Base.metadata.create_all(bind=_engine)
    except Exception:
        pass


# ── Test user (replaces JWT) ──────────────────────────────────────────────────

_TEST_USER = {
    "user_id": "test-user-1",
    "tenant_id": "test_tenant",
    "profile_name": "Admin",
}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _mock_model(batch_return, **extra_attrs):
    """Return a MagicMock whose compute_batch() returns [batch_return]."""
    m = MagicMock()
    m.compute_batch.return_value = [batch_return]
    for k, v in extra_attrs.items():
        setattr(m, k, v)
    return m


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def client():
    """
    Function-scoped TestClient with auth + DB wired to safe test doubles.
    Clears all dependency_overrides on teardown so tests can't pollute each other.
    """
    from app.main import app
    from app.financial_system.dependencies import get_current_user
    from app.Db.connections import get_db

    _init_tables()
    app.dependency_overrides[get_current_user] = lambda: _TEST_USER
    app.dependency_overrides[get_db] = _get_test_db

    with TestClient(app, raise_server_exceptions=False) as c:
        yield c

    app.dependency_overrides.clear()


# ── GET /health ───────────────────────────────────────────────────────────────

class TestHealth:

    @pytest.mark.integration
    def test_returns_200_and_healthy_status(self, client):
        r = client.get("/health")
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "healthy"
        assert "service" in body


# ── Unauthenticated access ────────────────────────────────────────────────────

class TestUnauthorizedAccess:
    """Protected endpoints must reject requests with no Bearer token."""

    def _bare_client(self):
        """TestClient with NO dependency overrides — real auth is enforced."""
        from app.main import app
        return TestClient(app, raise_server_exceptions=False)

    @pytest.mark.integration
    def test_predict_delay_rejects_missing_token(self):
        r = self._bare_client().post(
            "/api/v1/predict/delay",
            json=[{"shipment_id": "SHP-001"}],
        )
        assert r.status_code in (401, 403, 422)

    @pytest.mark.integration
    def test_financial_demand_rejects_missing_token(self):
        r = self._bare_client().post(
            "/api/v1/financial/demand",
            json=[{"shipment_id": "SHP-001"}],
        )
        assert r.status_code in (401, 403, 422)

    @pytest.mark.integration
    def test_financial_tariff_rejects_missing_token(self):
        r = self._bare_client().post(
            "/api/v1/financial/tariff",
            json=[{"shipment_id": "SHP-001"}],
        )
        assert r.status_code in (401, 403, 422)

    @pytest.mark.integration
    def test_financial_fx_rejects_missing_token(self):
        r = self._bare_client().post(
            "/api/v1/financial/fx",
            json=[{"shipment_id": "SHP-001"}],
        )
        assert r.status_code in (401, 403, 422)


# ── POST /api/v1/predict/delay ────────────────────────────────────────────────

_PREDICT_PAYLOAD = [
    {
        "shipment_id": "SHP-100",
        "route": "CN-EU",
        "carrier": "maersk",
        "order_value": 100_000,
        "shipment_cost": 12_000,
    }
]


class TestPredictDelay:

    @pytest.mark.integration
    def test_single_shipment_returns_prediction(self, client):
        from app.api.v1.endpoints.predict import get_delay_model
        client.app.dependency_overrides[get_delay_model] = lambda: _mock_model(3.5)

        r = client.post("/api/v1/predict/delay", json=_PREDICT_PAYLOAD)
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "success"
        assert len(body["predictions"]) == 1
        pred = body["predictions"][0]
        assert pred["shipment_id"] == "SHP-100"
        assert pred["predicted_delay_days"] == pytest.approx(3.5)

    @pytest.mark.integration
    def test_model_version_field_present(self, client):
        from app.api.v1.endpoints.predict import get_delay_model
        client.app.dependency_overrides[get_delay_model] = lambda: _mock_model(2.0)

        r = client.post("/api/v1/predict/delay", json=_PREDICT_PAYLOAD)
        assert "model_version" in r.json()

    @pytest.mark.integration
    def test_empty_payload_returns_empty_predictions(self, client):
        from app.api.v1.endpoints.predict import get_delay_model
        mock = MagicMock()
        mock.compute_batch.return_value = []
        client.app.dependency_overrides[get_delay_model] = lambda: mock

        r = client.post("/api/v1/predict/delay", json=[])
        assert r.status_code == 200
        assert r.json()["predictions"] == []

    @pytest.mark.integration
    def test_batch_of_three_returns_three_predictions(self, client):
        from app.api.v1.endpoints.predict import get_delay_model
        mock = MagicMock()
        mock.compute_batch.return_value = [1.0, 5.5, 10.2]
        client.app.dependency_overrides[get_delay_model] = lambda: mock

        payload = [
            {"shipment_id": "A", "route": "CN-EU"},
            {"shipment_id": "B", "route": "US-IN"},
            {"shipment_id": "C", "route": "LOCAL"},
        ]
        r = client.post("/api/v1/predict/delay", json=payload)
        assert r.status_code == 200
        preds = r.json()["predictions"]
        assert len(preds) == 3
        assert [p["shipment_id"] for p in preds] == ["A", "B", "C"]
        assert preds[1]["predicted_delay_days"] == pytest.approx(5.5)


# ── POST /api/v1/financial/demand ─────────────────────────────────────────────

_DEMAND_PAYLOAD = [
    {
        "shipment_id": "SHP-200",
        "route": "CN-EU",
        "order_value": 80_000,
        "total_cost": 10_000,
        "credit_days": 30,
        "industry_vertical": "electronics",
        "order_month": 6,
    }
]


class TestFinancialDemand:

    @pytest.mark.integration
    def test_returns_predicted_clv_and_vertical(self, client):
        from app.api.v1.endpoints.financial_analytics import get_demand_model
        client.app.dependency_overrides[get_demand_model] = lambda: _mock_model(72_000.0)

        r = client.post("/api/v1/financial/demand", json=_DEMAND_PAYLOAD)
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "success"
        row = body["demand_forecast"][0]
        assert row["shipment_id"] == "SHP-200"
        assert row["predicted_clv"] == pytest.approx(72_000.0)
        assert row["industry_vertical"] == "electronics"

    @pytest.mark.integration
    def test_missing_shipment_id_returns_null(self, client):
        from app.api.v1.endpoints.financial_analytics import get_demand_model
        client.app.dependency_overrides[get_demand_model] = lambda: _mock_model(50_000.0)

        r = client.post("/api/v1/financial/demand", json=[{"order_value": 10_000}])
        assert r.status_code == 200
        assert r.json()["demand_forecast"][0]["shipment_id"] is None

    @pytest.mark.integration
    def test_industry_vertical_defaults_to_default(self, client):
        from app.api.v1.endpoints.financial_analytics import get_demand_model
        client.app.dependency_overrides[get_demand_model] = lambda: _mock_model(10_000.0)

        r = client.post("/api/v1/financial/demand", json=[{"order_value": 10_000}])
        assert r.json()["demand_forecast"][0]["industry_vertical"] == "default"


# ── POST /api/v1/financial/tariff ─────────────────────────────────────────────

_TARIFF_PAYLOAD = [
    {
        "shipment_id": "SHP-300",
        "route": "US-CN",
        "order_value": 50_000,
        "hs_code": "8471",
    }
]


class TestFinancialTariff:

    @pytest.mark.integration
    def test_cross_border_returns_positive_tariff(self, client):
        from app.api.v1.endpoints.financial_analytics import get_tariff_model
        mock = _mock_model(1_250.0)
        mock._is_cross_border = lambda r: True
        client.app.dependency_overrides[get_tariff_model] = lambda: mock

        r = client.post("/api/v1/financial/tariff", json=_TARIFF_PAYLOAD)
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "success"
        row = body["tariff_analysis"][0]
        assert row["shipment_id"] == "SHP-300"
        assert row["tariff_cost"] == pytest.approx(1_250.0)
        assert row["is_cross_border"] is True
        assert row["hs_code_used"] == "8471"

    @pytest.mark.integration
    def test_domestic_route_zero_tariff(self, client):
        from app.api.v1.endpoints.financial_analytics import get_tariff_model
        mock = _mock_model(0.0)
        mock._is_cross_border = lambda r: False
        client.app.dependency_overrides[get_tariff_model] = lambda: mock

        r = client.post(
            "/api/v1/financial/tariff",
            json=[{"route": "LOCAL", "order_value": 25_000}],
        )
        assert r.status_code == 200
        row = r.json()["tariff_analysis"][0]
        assert row["tariff_cost"] == pytest.approx(0.0)
        assert row["is_cross_border"] is False

    @pytest.mark.integration
    def test_route_field_echoed_in_response(self, client):
        from app.api.v1.endpoints.financial_analytics import get_tariff_model
        mock = _mock_model(500.0)
        mock._is_cross_border = lambda r: True
        client.app.dependency_overrides[get_tariff_model] = lambda: mock

        r = client.post(
            "/api/v1/financial/tariff",
            json=[{"route": "IN-EU", "order_value": 30_000}],
        )
        assert r.json()["tariff_analysis"][0]["route"] == "IN-EU"


# ── POST /api/v1/financial/fx ─────────────────────────────────────────────────

_FX_PAYLOAD = [
    {
        "shipment_id": "SHP-400",
        "route": "CN-EU",
        "order_value": 100_000,
        "credit_days": 45,
        "predicted_delay": 7.0,
    }
]


class TestFinancialFX:

    @pytest.mark.integration
    def test_returns_fx_cost_and_echoes_delay(self, client):
        from app.api.v1.endpoints.financial_analytics import get_fx_model
        client.app.dependency_overrides[get_fx_model] = lambda: _mock_model(380.0)

        r = client.post("/api/v1/financial/fx", json=_FX_PAYLOAD)
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "success"
        row = body["fx_exposure"][0]
        assert row["shipment_id"] == "SHP-400"
        assert row["fx_cost"] == pytest.approx(380.0)
        assert row["predicted_delay_days"] == pytest.approx(7.0)

    @pytest.mark.integration
    def test_missing_predicted_delay_defaults_to_zero(self, client):
        from app.api.v1.endpoints.financial_analytics import get_fx_model
        client.app.dependency_overrides[get_fx_model] = lambda: _mock_model(0.0)

        r = client.post(
            "/api/v1/financial/fx",
            json=[{"route": "LOCAL", "order_value": 50_000}],
        )
        assert r.status_code == 200
        assert r.json()["fx_exposure"][0]["predicted_delay_days"] == pytest.approx(0.0)

    @pytest.mark.integration
    def test_route_field_echoed(self, client):
        from app.api.v1.endpoints.financial_analytics import get_fx_model
        client.app.dependency_overrides[get_fx_model] = lambda: _mock_model(100.0)

        r = client.post(
            "/api/v1/financial/fx",
            json=[{"route": "US-IN", "order_value": 60_000, "predicted_delay": 3.0}],
        )
        assert r.json()["fx_exposure"][0]["route"] == "US-IN"
