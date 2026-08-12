def enabled_sources():
    return ["healthline", "cleveland-clinic", "mayo-clinic", "webmd"]


def test_health_endpoint(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    body = response.get_json()
    assert body["mode"] == "demo"
    assert body["service"] == "medivita-api"
    assert body["status"] == "ok"
    assert body["providers"] == {"llm": "demo", "model": None, "news": "demo", "search": "demo"}


def test_sources_endpoint(client):
    response = client.get("/api/sources")
    assert response.status_code == 200
    assert [source["id"] for source in response.get_json()["sources"]] == enabled_sources()


def test_chat_validation_uses_consistent_error(client):
    response = client.post("/api/chat", json={"message": "x", "enabled_sources": []})
    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "VALIDATION_ERROR"


def test_chat_demo_response_varies_by_topic(client):
    response = client.post("/api/chat", json={"message": "What should I know about ibuprofen?", "enabled_sources": enabled_sources(), "history": []})
    body = response.get_json()
    assert response.status_code == 200
    assert body["mode"] == "demo"
    assert "nonsteroidal" in body["answer"]
    assert len(body["sections"]) == 4


def test_chat_filters_unknown_and_disabled_sources(client):
    response = client.post("/api/chat", json={"message": "Tell me about sleep", "enabled_sources": ["webmd", "unknown"], "history": []})
    assert [source["domain"] for source in response.get_json()["sources"]] == ["webmd.com"]


def test_deterministic_safety_notice_does_not_depend_on_llm(client):
    response = client.post(
        "/api/chat",
        json={"message": "I cannot breathe", "enabled_sources": enabled_sources(), "history": []},
    )
    assert "local emergency service" in response.get_json()["safety_notice"]


def test_health_check_validation(client):
    response = client.post("/api/health-check", json={"description": "short", "enabled_sources": enabled_sources()})
    assert response.status_code == 400


def test_health_check_demo_response(client):
    response = client.post("/api/health-check", json={"description": "I have had a headache and fatigue for two days.", "enabled_sources": enabled_sources()})
    body = response.get_json()
    assert response.status_code == 200
    assert "headache" in body["reported_symptoms"]
    assert body["mode"] == "demo"


def test_news_endpoint_and_filter(client):
    response = client.get("/api/news?category=nutrition&limit=2")
    articles = response.get_json()["articles"]
    assert response.status_code == 200
    assert articles and all(article["category"] == "nutrition" for article in articles)


def test_news_rejects_unsupported_category(client):
    response = client.get("/api/news?category=celebrity")
    assert response.status_code == 400
    assert response.get_json()["error"] == {"code": "VALIDATION_ERROR", "message": "Unsupported news category."}


def test_not_found_error_format(client):
    response = client.get("/api/missing")
    assert response.status_code == 404
    assert response.get_json()["error"]["code"] == "NOT_FOUND"
