import logging

import joblib

from app import services


def test_invalid_model_artifact_logs_and_uses_keyword_fallback(tmp_path, monkeypatch, caplog):
    monkeypatch.undo()
    model_path = tmp_path / "model.joblib"
    model_path.write_bytes(b"invalid model")
    monkeypatch.setattr(services, "MODEL_PATH", model_path)

    def fail_loading(path):
        raise ValueError("invalid model artifact")

    monkeypatch.setattr(joblib, "load", fail_loading)
    services.load_model.cache_clear()
    try:
        with caplog.at_level(logging.ERROR, logger="app.services"):
            assert services.load_model() is None
        assert "Could not load the AI model; using keyword fallback." in caplog.text
    finally:
        services.load_model.cache_clear()
