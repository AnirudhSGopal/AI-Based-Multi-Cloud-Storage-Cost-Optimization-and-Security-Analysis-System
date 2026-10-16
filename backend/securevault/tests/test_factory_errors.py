from app.core.factory import create_app


def test_unhandled_error_returns_generic_json_without_traceback():
    app = create_app("testing")

    @app.get("/test-unhandled-error")
    def fail():
        raise RuntimeError("internal details must not reach the client")

    response = app.test_client().get("/test-unhandled-error")

    assert response.status_code == 500
    assert response.is_json
    assert response.get_json() == {"error": "Internal server error"}
    assert b"internal details" not in response.data
    assert b"Traceback" not in response.data


def test_api_responses_include_security_headers_and_explicit_cors(monkeypatch):
    from config.settings import TestingConfig

    monkeypatch.setattr(TestingConfig, "CORS_ORIGINS", ["https://frontend.example.test"])
    app = create_app("testing")

    allowed = app.test_client().get(
        "/api/v1/cloud/trend", headers={"Origin": "https://frontend.example.test"}
    )
    denied = app.test_client().get(
        "/api/v1/cloud/trend", headers={"Origin": "https://attacker.example.test"}
    )

    assert allowed.headers["Access-Control-Allow-Origin"] == "https://frontend.example.test"
    assert allowed.headers["Access-Control-Allow-Credentials"] == "true"
    assert "Access-Control-Allow-Origin" not in denied.headers
    assert allowed.headers["X-Content-Type-Options"] == "nosniff"
    assert allowed.headers["X-Frame-Options"] == "DENY"
    assert allowed.headers["Content-Security-Policy"] == (
        "default-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'"
    )
    assert allowed.headers["Referrer-Policy"] == "no-referrer"
    assert allowed.headers["Strict-Transport-Security"] == (
        "max-age=31536000; includeSubDomains"
    )


def test_cors_wildcard_subdomain_support(monkeypatch):
    from config.settings import TestingConfig

    monkeypatch.setattr(TestingConfig, "CORS_ORIGINS", ["https://*.vercel.app"])
    app = create_app("testing")

    allowed = app.test_client().options(
        "/api/v1/cloud/trend",
        headers={
            "Origin": "https://ai-based-multi-cloud-storage-cost-o.vercel.app",
            "Access-Control-Request-Method": "GET",
        },
    )
    denied = app.test_client().options(
        "/api/v1/cloud/trend",
        headers={
            "Origin": "https://malicious-site.com",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert allowed.headers.get("Access-Control-Allow-Origin") == "https://ai-based-multi-cloud-storage-cost-o.vercel.app"
    assert "Access-Control-Allow-Origin" not in denied.headers

