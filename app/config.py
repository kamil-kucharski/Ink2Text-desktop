from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path


DEFAULT_GEMINI_MODEL = "gemini-2.5-flash-lite"
KEYRING_SERVICE_NAME = "Ink2Text"
KEYRING_API_KEY_USERNAME = "gemini_api_key"
SUPPORTED_GEMINI_MODELS = (
    "gemini-2.5-flash-lite",
    "gemini-2.5-flash",
    "gemini-3-flash-preview",
)


@dataclass(slots=True)
class AppConfig:
    gemini_api_key: str | None
    gemini_model: str
    app_language: str
    onboarding_completed: bool
    config_path: Path
    load_error: str | None = None


def load_app_config(base_dir: Path | None = None, env_path: Path | None = None) -> AppConfig:
    if env_path is not None:
        _load_dotenv_file(env_path)
    elif base_dir is None:
        _load_dotenv_file(Path.cwd() / ".env")

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
        or _load_api_key_from_keyring()
        or payload.get("gemini_api_key")
    )
    gemini_model = (
        os.getenv("NOTATKI_AI_GEMINI_MODEL")
        or os.getenv("GEMINI_MODEL")
        or payload.get("gemini_model")
        or DEFAULT_GEMINI_MODEL
    )
    app_language = (
        os.getenv("NOTATKI_AI_LANGUAGE")
        or payload.get("app_language")
        or "pl"
    )
    onboarding_completed = payload.get("onboarding_completed") == "true"

    return AppConfig(
        gemini_api_key=gemini_api_key,
        gemini_model=gemini_model,
        app_language=app_language,
        onboarding_completed=onboarding_completed,
        config_path=config_path,
        load_error=load_error,
    )


def save_app_config(
    config_path: Path,
    gemini_api_key: str,
    gemini_model: str,
    app_language: str = "pl",
    onboarding_completed: bool | None = None,
    store_api_key_securely: bool = False,
) -> None:
    config_path.parent.mkdir(parents=True, exist_ok=True)
    api_key_stored_securely = False
    if store_api_key_securely and gemini_api_key:
        api_key_stored_securely = _save_api_key_to_keyring(gemini_api_key)

    payload = {
        "gemini_model": gemini_model,
        "app_language": app_language,
    }
    if not api_key_stored_securely:
        payload["gemini_api_key"] = gemini_api_key
    if onboarding_completed is not None:
        payload["onboarding_completed"] = "true" if onboarding_completed else "false"
    with config_path.open("w", encoding="utf-8") as file:
        json.dump(payload, file, ensure_ascii=False, indent=2)
        file.write("\n")


def _load_api_key_from_keyring() -> str | None:
    try:
        import keyring
    except ModuleNotFoundError:
        return None

    try:
        value = keyring.get_password(KEYRING_SERVICE_NAME, KEYRING_API_KEY_USERNAME)
    except Exception:
        return None

    return value.strip() if isinstance(value, str) and value.strip() else None


def _save_api_key_to_keyring(api_key: str) -> bool:
    try:
        import keyring
    except ModuleNotFoundError:
        return False

    try:
        keyring.set_password(KEYRING_SERVICE_NAME, KEYRING_API_KEY_USERNAME, api_key)
    except Exception:
        return False

    return True


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
