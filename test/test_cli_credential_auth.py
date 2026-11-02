from types import SimpleNamespace
import sys
from pathlib import Path

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from starlette.datastructures import Headers
from fastapi import HTTPException

sys.path.insert(0, str(Path(__file__).parents[1] / "cli" / "src"))

import backend.cli_credential_manager as credentials
import backend.route_definitions as routes
from backend.models import Base, CliCredential, CliRequestNonce, User
from app2docker_cli.cli import APIClient


def _credential_db(tmp_path, monkeypatch):
    engine = create_engine(f"sqlite:///{tmp_path / 'auth.db'}")
    Base.metadata.create_all(
        engine,
        tables=[User.__table__, CliCredential.__table__, CliRequestNonce.__table__],
    )
    session = sessionmaker(bind=engine)
    monkeypatch.setattr(credentials, "get_db_session", session)
    db = session()
    user = User(username="alice", password_hash="unused", enabled=True)
    db.add(user)
    db.commit()
    db.refresh(user)
    db.close()
    return user.user_id


def _key_pair(tmp_path):
    private = ed25519.Ed25519PrivateKey.generate()
    private_path = tmp_path / "id_ed25519"
    private_path.write_bytes(
        private.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.OpenSSH,
            serialization.NoEncryption(),
        )
    )
    public = private.public_key().public_bytes(
        serialization.Encoding.OpenSSH,
        serialization.PublicFormat.OpenSSH,
    ).decode()
    return private_path, public


def test_unique_certificate_signs_request_and_replay_is_rejected(tmp_path, monkeypatch):
    user_id = _credential_db(tmp_path, monkeypatch)
    private_path, public_key = _key_pair(tmp_path)
    credential = credentials.create_credential(user_id, "laptop", public_key)
    with pytest.raises(ValueError, match="不能重复使用"):
        credentials.create_credential(user_id, "duplicate", public_key)

    client = APIClient(
        {
            "server": "https://example.com",
            "credential_id": credential["credential_id"],
            "private_key": str(private_path),
        }
    )
    body = b'{"trigger_source":"cli"}'
    headers = client._auth_headers("POST", "/api/pipelines/p1/run", body)
    request = SimpleNamespace(
        headers=Headers(headers=headers),
        method="POST",
        scope={
            "raw_path": b"/api/pipelines/p1/run",
            "query_string": b"",
            "app2docker.body_sha256": headers["X-App2Docker-Content-SHA256"],
        },
        url=SimpleNamespace(path="/api/pipelines/p1/run"),
    )

    result = credentials.verify_signed_request(request)

    assert result["username"] == "alice"
    assert result["credential_id"] == credential["credential_id"]
    with pytest.raises(ValueError, match="拒绝重放"):
        credentials.verify_signed_request(request)

    tampered_headers = client._auth_headers("POST", "/api/pipelines/p1/run", body)
    tampered_request = SimpleNamespace(
        headers=Headers(headers=tampered_headers),
        method="POST",
        scope={
            "raw_path": b"/api/pipelines/p1/run",
            "query_string": b"",
            "app2docker.body_sha256": "0" * 64,
        },
        url=SimpleNamespace(path="/api/pipelines/p1/run"),
    )
    with pytest.raises(ValueError, match="摘要不匹配"):
        credentials.verify_signed_request(tampered_request)


def test_api_key_and_basic_auth_headers():
    api_key = APIClient(
        {"server": "https://example.com", "api_key": "api-secret"}
    )
    basic = APIClient(
        {
            "server": "https://example.com",
            "username": "alice",
            "password": "secret",
        }
    )

    assert api_key._auth_headers("GET", "/health")["Authorization"] == "Bearer api-secret"
    assert basic._auth_headers("GET", "/health")["Authorization"].startswith("Basic ")


def test_permission_helpers_reuse_request_identity_but_new_request_cannot_replay(tmp_path, monkeypatch):
    user_id = _credential_db(tmp_path, monkeypatch)
    private_path, public_key = _key_pair(tmp_path)
    credential = credentials.create_credential(user_id, 'pipeline-admin', public_key)
    client = APIClient({'server':'https://example.com', 'credential_id':credential['credential_id'], 'private_key':str(private_path)})
    headers = client._auth_headers('PUT', '/api/pipelines/p1', b'{}')
    def request():
        return SimpleNamespace(headers=Headers(headers=headers),method='PUT',
            scope={'raw_path':b'/api/pipelines/p1','query_string':b'',
                   'app2docker.body_sha256':headers['X-App2Docker-Content-SHA256']},
            url=SimpleNamespace(path='/api/pipelines/p1'))
    first=request()
    assert routes.require_auth(first)=='alice'
    assert routes.require_auth(first)=='alice'
    with pytest.raises(HTTPException,match='401'):
        routes.require_auth(request())


def test_server_accepts_api_key_and_basic_identity(monkeypatch):
    monkeypatch.setattr(
        routes,
        "validate_app_key",
        lambda value: {"username": "api-user"} if value == "api-secret" else None,
    )
    api_request = SimpleNamespace(headers=Headers({"X-API-Key": "api-secret"}))
    assert routes.require_auth(api_request) == "api-user"

    monkeypatch.setattr(
        routes,
        "authenticate",
        lambda username, password: {
            "success": username == "alice" and password == "secret",
            "username": username,
            "require_password_change": False,
        },
    )
    basic_headers = APIClient(
        {"server": "https://example.com", "username": "alice", "password": "secret"}
    )._auth_headers("GET", "/health")
    assert routes.require_auth(SimpleNamespace(headers=Headers(basic_headers))) == "alice"

    monkeypatch.setattr(
        routes,
        "authenticate",
        lambda username, password: {
            "success": True,
            "username": username,
            "require_password_change": True,
        },
    )
    with pytest.raises(HTTPException) as error:
        routes.require_auth(SimpleNamespace(headers=Headers(basic_headers)))
    assert error.value.status_code == 403
