import pytest

from config.settings import ProductionConfig


REQUIRED_PRODUCTION_ENV = {
    "SECRET_KEY": "test-secret",
    "JWT_SECRET_KEY": "test-jwt-secret",
    "DATABASE_URL": "postgresql://user:password@db.example.test/app",
    "ENCRYPTION_KEY": "test-encryption-key",
    "CORS_ORIGINS": "https://app.example.test",
    "REDIS_URL": "redis://localhost:6379/1",
}


@pytest.mark.parametrize("missing_name", REQUIRED_PRODUCTION_ENV)
def test_production_config_names_each_missing_required_variable(
    monkeypatch, missing_name
):
    for name, value in REQUIRED_PRODUCTION_ENV.items():
        monkeypatch.setenv(name, value)
    monkeypatch.delenv(missing_name)

    with pytest.raises(RuntimeError, match=missing_name):
        ProductionConfig.validate()


def test_production_config_accepts_complete_environment(monkeypatch):
    for name, value in REQUIRED_PRODUCTION_ENV.items():
        monkeypatch.setenv(name, value)

    ProductionConfig.validate()
    assert ProductionConfig.DEBUG is False
    assert ProductionConfig.PROPAGATE_EXCEPTIONS is False


def test_production_config_rejects_wildcard_cors(monkeypatch):
    for name, value in REQUIRED_PRODUCTION_ENV.items():
        monkeypatch.setenv(name, value)
    monkeypatch.setattr(ProductionConfig, "CORS_ORIGINS", ["*"])

    with pytest.raises(RuntimeError, match="explicit origins"):
        ProductionConfig.validate()
