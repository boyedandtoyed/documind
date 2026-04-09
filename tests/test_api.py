import pytest
from fastapi.testclient import TestClient
from documind.api import app

client = TestClient(app)

def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ok"
    assert "documents_indexed" in data
    assert "version" in data

def test_upload_invalid_type():
    r = client.post(
        "/documents/upload",
        files={"file": ("test.exe", b"binary", "application/octet-stream")},
    )
    assert r.status_code == 415

def test_upload_txt():
    content = "Machine learning is a subset of artificial intelligence. " * 50
    r = client.post(
        "/documents/upload",
        files={"file": ("test.txt", content.encode(), "text/plain")},
    )
    assert r.status_code == 201
    data = r.json()
    assert data["chunks"] > 0
    assert data["document_id"]
    assert data["filename"] == "test.txt"
