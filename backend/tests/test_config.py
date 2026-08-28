from app.config import Settings


def test_cors_origins_accept_comma_separated_environment(monkeypatch) -> None:
    monkeypatch.setenv(
        "BACKEND_CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000"
    )

    settings = Settings()

    assert settings.backend_cors_origins == [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]
