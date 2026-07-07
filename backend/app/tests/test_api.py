from __future__ import annotations

from fastapi.testclient import TestClient


def test_health_and_plugins(client: TestClient) -> None:
    assert client.get("/health").json() == {"status": "ok"}

    plugins = client.get("/plugins").json()
    assert "manual_csv" in {plugin["name"] for plugin in plugins["ingestion"]}
    assert "demand_analyzer" in {plugin["name"] for plugin in plugins["analyzers"]}


def test_ingestion_products_opportunities_and_detail(client: TestClient) -> None:
    run = client.post("/ingestion/run", json={})
    assert run.status_code == 200
    assert run.json()["status"] == "success"

    opportunities = client.get("/opportunities").json()
    assert opportunities["total"] == 7
    top = opportunities["items"][0]
    assert top["canonical_name"] == "facial ice roller"

    products = client.get("/products", params={"q": "ice"}).json()
    assert products["total"] == 1

    detail = client.get(f"/products/{top['id']}").json()
    assert detail["product"]["canonical_name"] == "facial ice roller"
    assert detail["latest_score"]["final_score"] > 70
    assert detail["recent_observations"]

    runs = client.get("/plugin-runs").json()
    assert runs

