from __future__ import annotations

from fastapi.testclient import TestClient


def test_health_and_plugins(client: TestClient) -> None:
    assert client.get("/health").json() == {"status": "ok"}

    plugins = client.get("/plugins").json()
    assert "manual_csv" in {plugin["name"] for plugin in plugins["ingestion"]}
    assert "demand_analyzer" in {plugin["name"] for plugin in plugins["analyzers"]}


def test_refresh_existing_is_safe_with_no_candidates(client: TestClient) -> None:
    response = client.post("/ingestion/refresh-existing")

    assert response.status_code == 200
    assert response.json() == {
        "status": "success",
        "plugin_runs": [],
        "products_updated": 0,
        "scores_updated": 0,
        "observations_created": 0,
        "errors": [],
        "message": "No existing candidates to refresh. Create a candidate in Validator first, then run Amazon research.",
    }


def test_ingestion_products_opportunities_and_detail(client: TestClient) -> None:
    run = client.post(
        "/ingestion/run",
        json={
            "plugins": [
                "manual_csv",
                "amazon_mock",
                "alibaba_mock",
                "reddit_mock",
                "google_trends_mock",
            ]
        },
    )
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
    assert detail["latest_score"]["final_score"] > 60
    assert detail["recent_observations"]
    cost_ceiling = detail["cost_models"][0]["assumptions"]["cost_ceiling"]
    assert cost_ceiling["max_landed_cost"] > 0
    assert cost_ceiling["decision"] == "quote_at_or_below_ceiling"

    runs = client.get("/plugin-runs").json()
    assert runs
