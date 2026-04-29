import json
from pathlib import Path

from app.config import DEFAULT_GEMINI_MODEL, load_app_config


def test_load_app_config_reads_local_json_when_env_is_missing(tmp_path: Path) -> None:
    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps(
            {
                "gemini_api_key": "local-key",
                "gemini_model": "gemini-local-model",
            }
        ),
        encoding="utf-8",
    )

    config = load_app_config(base_dir=tmp_path)

    assert config.gemini_api_key == "local-key"
    assert config.gemini_model == "gemini-local-model"
    assert config.load_error is None


def test_load_app_config_prefers_environment_values(tmp_path: Path, monkeypatch) -> None:
    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps(
            {
                "gemini_api_key": "local-key",
                "gemini_model": "gemini-local-model",
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("GOOGLE_API_KEY", "env-key")
    monkeypatch.setenv("GEMINI_MODEL", "gemini-env-model")

    config = load_app_config(base_dir=tmp_path)

    assert config.gemini_api_key == "env-key"
    assert config.gemini_model == "gemini-env-model"


def test_load_app_config_reports_invalid_json(tmp_path: Path) -> None:
    config_path = tmp_path / "config.json"
    config_path.write_text("{broken", encoding="utf-8")

    config = load_app_config(base_dir=tmp_path)

    assert config.gemini_api_key is None
    assert config.gemini_model == DEFAULT_GEMINI_MODEL
    assert config.load_error is not None


def test_load_app_config_reads_local_dotenv_file(tmp_path: Path, monkeypatch) -> None:
    env_path = tmp_path / ".env"
    env_path.write_text(
        "GEMINI_API_KEY=dotenv-key\nGEMINI_MODEL=dotenv-model\n",
        encoding="utf-8",
    )
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_MODEL", raising=False)
    monkeypatch.delenv("NOTATKI_AI_GEMINI_MODEL", raising=False)

    config = load_app_config(base_dir=tmp_path, env_path=env_path)

    assert config.gemini_api_key == "dotenv-key"
    assert config.gemini_model == "dotenv-model"


def test_load_app_config_prefers_real_environment_over_dotenv(tmp_path: Path, monkeypatch) -> None:
    env_path = tmp_path / ".env"
    env_path.write_text(
        "GEMINI_API_KEY=dotenv-key\nGEMINI_MODEL=dotenv-model\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("GEMINI_API_KEY", "real-env-key")
    monkeypatch.setenv("GEMINI_MODEL", "real-env-model")

    config = load_app_config(base_dir=tmp_path, env_path=env_path)

    assert config.gemini_api_key == "real-env-key"
    assert config.gemini_model == "real-env-model"
