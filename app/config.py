from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path


DEFAULT_GEMINI_MODEL = "gemini-2.5-flash-lite"
SUPPORTED_GEMINI_MODELS = (
    "gemini-2.5-flash-lite",
    "gemini-2.5-flash",
    "gemini-3-flash-preview",
)


@dataclass(slots=True)
class AppConfig:
    gemini_api_key: str | None
    gemini_model: str
    config_path: Path
    load_error: str | None = None


def load_app_config(base_dir: Path | None = None, env_path: Path | None = None) -> AppConfig:
    _load_dotenv_file(env_path or Path.cwd() / ".env")

    app_data_dir = base_dir or Path.cwd() / "app_data"
    config_path = app_data_dir / "config.json"
    payload: dict[str, str] = {}
    load_error: str | None = None

    if config_path.exists():
        try:
            with config_path.open("r", encoding="utf-8") as file:
                raw_payload = json.load(file)
            if isinstance(raw_payload, dict):
                payload = {
                    key: value
                    for key, value in raw_payload.items()
                    if isinstance(key, str) and isinstance(value, str)
                }
            else:
                load_error = (
                    f"Plik konfiguracyjny {config_path} ma nieprawidłowy format. "
                    "Oczekiwano obiektu JSON."
                )
        except json.JSONDecodeError as error:
            load_error = (
                f"Nie udało się odczytać konfiguracji z {config_path}: {error.msg}."
            )
        except OSError as error:
            load_error = (
                f"Nie udało się odczytać konfiguracji z {config_path}: {error}."
            )

    gemini_api_key = (
        os.getenv("GOOGLE_API_KEY")
        or os.getenv("GEMINI_API_KEY")
        or payload.get("gemini_api_key")
    )
    gemini_model = (
        os.getenv("NOTATKI_AI_GEMINI_MODEL")
        or os.getenv("GEMINI_MODEL")
        or payload.get("gemini_model")
        or DEFAULT_GEMINI_MODEL
    )

    return AppConfig(
        gemini_api_key=gemini_api_key,
        gemini_model=gemini_model,
        config_path=config_path,
        load_error=load_error,
    )


def save_app_config(config_path: Path, gemini_api_key: str, gemini_model: str) -> None:
    config_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "gemini_api_key": gemini_api_key,
        "gemini_model": gemini_model,
    }
    with config_path.open("w", encoding="utf-8") as file:
        json.dump(payload, file, ensure_ascii=False, indent=2)
        file.write("\n")


def _load_dotenv_file(env_path: Path) -> None:
    if not env_path.exists():
        return

    try:
        lines = env_path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return

    for raw_line in lines:
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        if not key:
            continue

        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]

        os.environ.setdefault(key, value)
