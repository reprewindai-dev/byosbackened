"""Test multi-tenant isolation - workspace A cannot access workspace B data."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from db.session import SessionLocal, engine, Base
from db.models import Workspace, User, RoutingStrategy, TrafficPattern, Anomaly, SavingsReport
from apps.api.main import app
from core.security import create_access_token
from datetime import datetime, timedelta
from decimal import Decimal
import uuid

# Create test database
Base.metadata.create_all(bind=engine)


@pytest.fixture
def db():
    """Create test database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def workspace_a(db: Session):
    """Create workspace A."""
    workspace = Workspace(
        id=str(uuid.uuid4()),
        name="Workspace A",
        slug="workspace-a",
        is_active=True,
    )
    db.add(workspace)
    db.commit()
    db.refresh(workspace)
    return workspace


@pytest.fixture
def workspace_b(db: Session):
    """Create workspace B."""
    workspace = Workspace(
        id=str(uuid.uuid4()),
        name="Workspace B",
        slug="workspace-b",
        is_active=True,
    )
    db.add(workspace)
    db.commit()
    db.refresh(workspace)
    return workspace


@pytest.fixture
def user_a(db: Session, workspace_a: Workspace):
    """Create user A in workspace A."""
    user = User(
        id=str(uuid.uuid4()),
        workspace_id=workspace_a.id,
        email="user_a@test.com",
        hashed_password="hashed",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def user_b(db: Session, workspace_b: Workspace):
    """Create user B in workspace B."""
    user = User(
        id=str(uuid.uuid4()),
        workspace_id=workspace_b.id,
        email="user_b@test.com",
        hashed_password="hashed",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def token_a(workspace_a: Workspace, user_a: User):
    """Create access token for workspace A."""
    return create_access_token(data={"sub": user_a.email, "workspace_id": workspace_a.id})


@pytest.fixture
def token_b(workspace_b: Workspace, user_b: User):
    """Create access token for workspace B."""
    return create_access_token(data={"sub": user_b.email, "workspace_id": workspace_b.id})


@pytest.fixture
def routing_strategy_a(db: Session, workspace_a: Workspace):
    """Create routing strategy for workspace A."""
    strategy = RoutingStrategy(
        id=str(uuid.uuid4()),
        workspace_id=workspace_a.id,
        operation_type="transcribe",
        preferred_provider="openai",
        exploration_rate=Decimal("0.1"),
        strategy_type="cost_optimized",
        total_samples=100,
        learning_samples=50,
    )
    db.add(strategy)
    db.commit()
    db.refresh(strategy)
    return strategy


@pytest.fixture
def traffic_pattern_a(db: Session, workspace_a: Workspace):
    """Create traffic pattern for workspace A."""
    pattern = TrafficPattern(
        id=str(uuid.uuid4()),
        workspace_id=workspace_a.id,
        pattern_type="daily",
        operation_type="transcribe",
        pattern_data={"hour": 10, "count": 50},
        avg_requests_per_hour=Decimal("10.5"),
        samples_used=100,
    )
    db.add(pattern)
    db.commit()
    db.refresh(pattern)
    return pattern


@pytest.fixture
def anomaly_a(db: Session, workspace_a: Workspace):
    """Create anomaly for workspace A."""
    from db.models.anomaly import AnomalyType, AnomalySeverity, AnomalyStatus

    anomaly = Anomaly(
        id=str(uuid.uuid4()),
        workspace_id=workspace_a.id,
        anomaly_type=AnomalyType.COST_SPIKE,
        severity=AnomalySeverity.HIGH,
        status=AnomalyStatus.DETECTED,
        description="Cost spike detected",
        baseline_value="0.001",
        actual_value="0.005",
    )
    db.add(anomaly)
    db.commit()
    db.refresh(anomaly)
    return anomaly


@pytest.fixture
def savings_report_a(db: Session, workspace_a: Workspace):
    """Create savings report for workspace A."""
    report = SavingsReport(
        id=str(uuid.uuid4()),
        workspace_id=workspace_a.id,
        period_start=datetime.utcnow() - timedelta(days=30),
        period_end=datetime.utcnow(),
        report_type="monthly",
        total_savings=Decimal("100.50"),
        baseline_cost=Decimal("500.00"),
        actual_cost=Decimal("399.50"),
        savings_percent=Decimal("20.10"),
        operations_count=1000,
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    return report


class TestTenantIsolation:
    """Test that workspace A cannot access workspace B data."""

    def test_workspace_b_cannot_read_workspace_a_routing_strategies(
        self,
        db: Session,
        routing_strategy_a: RoutingStrategy,
        token_b: str,
    ):
        """Workspace B cannot read workspace A's routing strategies."""
        client = TestClient(app)

        # Try to get routing stats (which would query routing strategies)
        response = client.get(
            "/api/v1/autonomous/routing/stats",
            params={"operation_type": "transcribe"},
            headers={"Authorization": f"Bearer {token_b}"},
        )

        # Should not return workspace A's data
        # Either empty result or 404
        assert response.status_code in [200, 404]
        if response.status_code == 200:
            # If it returns data, it should be empty or for workspace B only
            data = response.json()
            # Verify no workspace A data leaked
            assert routing_strategy_a.workspace_id not in str(data)

    def test_workspace_b_cannot_read_workspace_a_insights(
        self,
        db: Session,
        savings_report_a: SavingsReport,
        token_b: str,
    ):
        """Workspace B cannot read workspace A's insights."""
        client = TestClient(app)

        response = client.get(
            "/api/v1/insights/savings",
            headers={"Authorization": f"Bearer {token_b}"},
        )

        # Should return empty or workspace B's own data
        assert response.status_code == 200
        data = response.json()

        # If workspace B has no data, should return zeros
        # If workspace B has data, should only be workspace B's
        assert savings_report_a.workspace_id not in str(data)

    def test_workspace_b_cannot_read_workspace_a_suggestions(
        self,
        db: Session,
        workspace_a: Workspace,
        token_b: str,
    ):
        """Workspace B cannot get workspace A's suggestions."""
        client = TestClient(app)

        response = client.get(
            "/api/v1/suggestions",
            headers={"Authorization": f"Bearer {token_b}"},
        )

        # Should return suggestions for workspace B only
        assert response.status_code == 200
        data = response.json()

        # Verify no workspace A data in suggestions
        assert workspace_a.id not in str(data)

    def test_workspace_b_cannot_access_workspace_a_autonomous_endpoints(
        self,
        db: Session,
        workspace_a: Workspace,
        token_b: str,
    ):
        """Workspace B cannot access workspace A's autonomous ML data."""
        client = TestClient(app)

        # Test cost prediction endpoint
        response = client.post(
            "/api/v1/autonomous/cost/predict",
            json={
                "operation_type": "transcribe",
                "provider": "openai",
                "input_tokens": 1000,
                "estimated_output_tokens": 300,
            },
            headers={"Authorization": f"Bearer {token_b}"},
        )

        # Should work but use workspace B's context
        assert response.status_code == 200
        # Prediction should be for workspace B, not workspace A
        assert workspace_a.id not in str(response.json())

    def test_direct_database_query_isolation(
        self,
        db: Session,
        routing_strategy_a: RoutingStrategy,
        workspace_b: Workspace,
    ):
        """Test that direct database queries respect workspace_id."""
        # Query routing strategies for workspace B
        strategies_b = (
            db.query(RoutingStrategy).filter(RoutingStrategy.workspace_id == workspace_b.id).all()
        )

        # Should not include workspace A's strategy
        assert routing_strategy_a.id not in [s.id for s in strategies_b]

        # Query for workspace A should find it
        strategies_a = (
            db.query(RoutingStrategy)
            .filter(RoutingStrategy.workspace_id == routing_strategy_a.workspace_id)
            .all()
        )

        assert routing_strategy_a.id in [s.id for s in strategies_a]
