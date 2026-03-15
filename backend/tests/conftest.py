from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from app.browser import executor
from app.database import get_session
from app.live.runtime import runtime_manager
from app.main import app
from app.models.credential import SandboxCredential
from app.models.document import Document, DocumentChunk
from app.models.policy import PolicyRule
from app.models.recipe import DemoRecipe
from app.models.session import BrowserAction, DemoSession, SessionMessage
from app.models.workspace import Workspace
from app.services.encryption import encrypt
from app.v2.runtime import runtime_registry


@pytest.fixture(name="engine")
def engine_fixture():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture(autouse=True)
def reset_browser_sessions():
    executor._active_sessions.clear()
    runtimes = list(runtime_manager._runtimes.keys())
    for session_id in runtimes:
        runtime_manager._runtimes.pop(session_id, None)
    runtime_registry._states.clear()
    yield
    executor._active_sessions.clear()
    runtimes = list(runtime_manager._runtimes.keys())
    for session_id in runtimes:
        runtime_manager._runtimes.pop(session_id, None)
    runtime_registry._states.clear()


@pytest.fixture(name="session")
def session_fixture(engine):
    with Session(engine) as session:
        yield session


@pytest.fixture(name="client")
def client_fixture(session: Session):
    def get_session_override():
        return session

    app.dependency_overrides[get_session] = get_session_override
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def workspace(session: Session) -> Workspace:
    ws = Workspace(
        name="Acme CRM",
        description="Sales workspace",
        product_url="https://app.example.com",
        allowed_domains="app.example.com,docs.example.com",
    )
    session.add(ws)
    session.commit()
    session.refresh(ws)
    return ws


@pytest.fixture
def demo_session(session: Session, workspace: Workspace) -> DemoSession:
    started_at = datetime.now(timezone.utc) - timedelta(minutes=5)
    current = DemoSession(
        workspace_id=workspace.id,
        public_token=workspace.public_token,
        buyer_name="Taylor Buyer",
        buyer_email="taylor@example.com",
        mode="text",
        started_at=started_at,
    )
    session.add(current)
    session.commit()
    session.refresh(current)
    return current


@pytest.fixture
def recipe_factory(session: Session, workspace: Workspace):
    def factory(**overrides) -> DemoRecipe:
        recipe = DemoRecipe(
            workspace_id=workspace.id,
            name=overrides.pop("name", "Open Dashboard"),
            description=overrides.pop("description", "Open the dashboard and explain metrics"),
            trigger_phrases=overrides.pop("trigger_phrases", "dashboard,metrics"),
            steps_json=overrides.pop(
                "steps_json",
                '[{"action":"navigate","target":"https://app.example.com/dashboard","description":"Open dashboard"}]',
            ),
            priority=overrides.pop("priority", 5),
            is_active=overrides.pop("is_active", True),
            **overrides,
        )
        session.add(recipe)
        session.commit()
        session.refresh(recipe)
        return recipe

    return factory


@pytest.fixture
def policy_factory(session: Session, workspace: Workspace):
    def factory(**overrides) -> PolicyRule:
        rule = PolicyRule(
            workspace_id=workspace.id,
            rule_type=overrides.pop("rule_type", "blocked_topic"),
            pattern=overrides.pop("pattern", "secret"),
            description=overrides.pop("description", "Sensitive topic"),
            action=overrides.pop("action", "refuse"),
            severity=overrides.pop("severity", "high"),
            is_active=overrides.pop("is_active", True),
            **overrides,
        )
        session.add(rule)
        session.commit()
        session.refresh(rule)
        return rule

    return factory


@pytest.fixture
def chunk_factory(session: Session, workspace: Workspace):
    def factory(**overrides) -> DocumentChunk:
        document = Document(
            workspace_id=workspace.id,
            filename=overrides.pop("filename", "guide.md"),
            file_type=overrides.pop("file_type", "md"),
            content_text=overrides.pop("content_text", "Product guide"),
            status="ready",
        )
        session.add(document)
        session.commit()
        session.refresh(document)

        chunk = DocumentChunk(
            document_id=document.id,
            workspace_id=workspace.id,
            chunk_index=overrides.pop("chunk_index", 0),
            content=overrides.pop("content", "Dashboard supports pipeline metrics"),
            feature_tag=overrides.pop("feature_tag", "dashboard"),
            entity_type=overrides.pop("entity_type", "feature"),
            **overrides,
        )
        session.add(chunk)
        session.commit()
        session.refresh(chunk)
        return chunk

    return factory


@pytest.fixture
def credential_factory(session: Session, workspace: Workspace):
    def factory(**overrides) -> SandboxCredential:
        credential = SandboxCredential(
            workspace_id=workspace.id,
            label=overrides.pop("label", "demo-user-1"),
            login_url=overrides.pop("login_url", "https://app.example.com/login"),
            username_encrypted=overrides.pop("username_encrypted", encrypt("demo@example.com")),
            password_encrypted=overrides.pop("password_encrypted", encrypt("top-secret")),
            is_active=overrides.pop("is_active", True),
            **overrides,
        )
        session.add(credential)
        session.commit()
        session.refresh(credential)
        return credential

    return factory


@pytest.fixture
def message_factory(session: Session, demo_session: DemoSession):
    def factory(**overrides) -> SessionMessage:
        message = SessionMessage(
            session_id=demo_session.id,
            role=overrides.pop("role", "user"),
            content=overrides.pop("content", "How do your dashboards work?"),
            message_type=overrides.pop("message_type", "text"),
            planner_decision=overrides.pop("planner_decision", None),
            metadata_json=overrides.pop("metadata_json", None),
            **overrides,
        )
        session.add(message)
        session.commit()
        session.refresh(message)
        return message

    return factory


@pytest.fixture
def browser_action_factory(session: Session, demo_session: DemoSession):
    def factory(**overrides) -> BrowserAction:
        action = BrowserAction(
            session_id=demo_session.id,
            action_type=overrides.pop("action_type", "navigate"),
            target=overrides.pop("target", "https://app.example.com/dashboard"),
            status=overrides.pop("status", "success"),
            narration=overrides.pop("narration", "Opened dashboard"),
            duration_ms=overrides.pop("duration_ms", 250),
            **overrides,
        )
        session.add(action)
        session.commit()
        session.refresh(action)
        return action

    return factory
