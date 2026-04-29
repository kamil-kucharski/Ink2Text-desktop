from __future__ import annotations

import mimetypes
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


DEFAULT_FALLBACK_MODELS = (
    "gemini-2.5-flash-lite",
    "gemini-2.5-flash",
    "gemini-3-flash-preview",
)
TRANSCRIPTION_MODE_LABELS = {
    "faithful": "Wierna transkrypcja",
    "formatted": "Formatowanie notatki",
    "organized": "Uporządkowanie notatki",
    "expanded": "Rozszerzenie notatki",
}


def build_transcription_prompt(mode: str = "faithful") -> str:
    common_rules = (
        "Zachowaj oryginalny język notatek.\n"
        "Zwróć tekst wyłącznie w języku użytym na obrazie. Nie tłumacz notatki na inny język.\n"
        "Jeśli jakiś fragment jest nieczytelny, wpisz [nieczytelne].\n"
        "Zwróć wyłącznie gotową treść notatki bez komentarza wstępnego."
    )

    if mode == "faithful":
        return (
            "Przepisz odręczne notatki z dostarczonych obrazów możliwie wiernie, linia po linii.\n"
            "Nie poprawiaj stylu, gramatyki, fleksji, szyku zdań ani błędów językowych.\n"
            "Nie dodawaj nagłówków, list, punktowania, numerowania ani dodatkowego formatowania, jeśli nie wynika to wprost z obrazu.\n"
            "Nie dopisuj informacji, których nie ma na obrazach.\n"
            f"{common_rules}"
        )

    if mode == "formatted":
        return (
            "Przepisz odręczne notatki i skup się na ich estetycznym sformatowaniu.\n"
            "Dodawaj nagłówki, listy wypunktowane, listy numerowane i logiczne akapity, jeśli poprawiają czytelność.\n"
            "Nie zmieniaj sensu tekstu i nie dopisuj nowych informacji merytorycznych.\n"
            "Możesz jedynie uporządkować układ wizualny treści, aby notatka wyglądała ładnie i przejrzyście.\n"
            f"{common_rules}"
        )

    if mode == "organized":
        return (
            "Przepisz odręczne notatki i uporządkuj je w estetyczną, przejrzystą formę.\n"
            "Dodawaj sensowne nagłówki, listy, podpunkty i logiczny podział na sekcje.\n"
            "Poprawiaj błędy stylistyczne, odmianę wyrazów, końcówki i drobne braki językowe, jeśli wynikają jednoznacznie z kontekstu.\n"
            "Możesz uzupełnić pojedyncze brakujące słowo lub krótki fragment tylko wtedy, gdy jest bardzo prawdopodobny i nie zmienia sensu.\n"
            "Nie halucynuj, nie wymyślaj faktów i nie dodawaj nowych informacji merytorycznych spoza notatki.\n"
            f"{common_rules}"
        )

    if mode == "expanded":
        return (
            "Przepisz odręczne notatki, uporządkuj je i estetycznie sformatuj.\n"
            "Dodawaj sensowne nagłówki, listy, podpunkty i logiczny podział na sekcje.\n"
            "Poprawiaj błędy stylistyczne, odmianę wyrazów, końcówki i drobne braki językowe, jeśli wynikają jednoznacznie z kontekstu.\n"
            "Dodatkowo możesz rozszerzyć notatkę o pomocne wyjaśnienia lub brakujące informacje merytoryczne tylko wtedy, gdy są bezpośrednio związane z tematem notatki i realnie zwiększają jej wartość.\n"
            "Każde rozszerzenie musi zachowywać sens oryginału, nie może zawierać halucynacji ani nieprawdziwych informacji.\n"
            "Łączna długość dopisanego przez Ciebie tekstu nie może przekroczyć 50% długości treści wynikającej z oryginalnej notatki.\n"
            "Jeśli nie masz wysokiej pewności, nie dopisuj nowych informacji.\n"
            f"{common_rules}"
        )

    raise ValueError(f"Nieobsługiwany tryb transkrypcji: {mode}")


@dataclass(slots=True)
class TranscriptionResult:
    text: str
    model_name: str
    transcription_mode: str


class AIProviderError(Exception):
    """Błąd warstwy komunikacji z AI."""


class MissingAPIKeyError(AIProviderError):
    """Brak klucza API dla providera."""


class ProviderDependencyError(AIProviderError):
    """Brak lokalnej zależności potrzebnej do providera."""


class ProviderRequestError(AIProviderError):
    """Błąd wysłania zapytania do providera."""


class InvalidProviderResponseError(AIProviderError):
    """Provider zwrócił niepoprawną odpowiedź."""


class AIProvider(Protocol):
    def transcribe_images(
        self,
        image_paths: list[Path],
        transcription_mode: str = "faithful",
    ) -> TranscriptionResult:
        raise NotImplementedError


class GeminiAIProvider:
    def __init__(
        self,
        api_key: str | None,
        model_name: str,
        config_path: Path | None = None,
        fallback_models: tuple[str, ...] = DEFAULT_FALLBACK_MODELS,
        retry_attempts: int = 3,
        initial_backoff_seconds: float = 1.0,
        sleep_func=time.sleep,
    ) -> None:
        self.api_key = api_key
        self.model_name = model_name
        self.config_path = config_path
        self.fallback_models = fallback_models
        self.retry_attempts = max(1, retry_attempts)
        self.initial_backoff_seconds = max(0.0, initial_backoff_seconds)
        self.sleep_func = sleep_func

    def transcribe_images(
        self,
        image_paths: list[Path],
        transcription_mode: str = "faithful",
    ) -> TranscriptionResult:
        if not self.api_key:
            raise MissingAPIKeyError(self._missing_api_key_message())
        if not image_paths:
            raise ProviderRequestError("Brak przygotowanych obrazów do wysłania.")

        client = self._create_client()
        prompt = build_transcription_prompt(transcription_mode)
        contents = [prompt, *[self._build_image_part(path) for path in image_paths]]
        attempted_models: list[str] = []
        last_retryable_error: Exception | None = None

        for model_name in self._candidate_models():
            attempted_models.append(model_name)
            try:
                response = self._generate_content_with_retries(client, model_name, contents)
            except Exception as error:  # pragma: no cover - zależne od SDK i sieci
                if self._is_retryable_error(error):
                    last_retryable_error = error
                    continue
                raise ProviderRequestError(self._humanize_sdk_error(error)) from error

            text = self._extract_text_from_response(response)
            if not text:
                raise InvalidProviderResponseError(
                    "Model nie zwrócił treści notatki. Spróbuj ponownie z innymi zdjęciami."
                )

            return TranscriptionResult(
                text=text,
                model_name=model_name,
                transcription_mode=transcription_mode,
            )

        if last_retryable_error is not None:
            attempted_models_text = ", ".join(attempted_models)
            raise ProviderRequestError(
                "Modele Gemini są chwilowo przeciążone lub niedostępne. "
                f"Próbowano modeli: {attempted_models_text}. "
                "Spróbuj ponownie za chwilę."
            ) from last_retryable_error

        raise ProviderRequestError("Nie udało się przetworzyć notatki przez Gemini.")

    def _create_client(self):
        genai_module, _ = self._load_sdk()
        return genai_module.Client(api_key=self.api_key)

    def _build_image_part(self, image_path: Path):
        _, types_module = self._load_sdk()
        if not image_path.is_file():
            raise ProviderRequestError(f"Nie znaleziono pliku obrazu: {image_path}")

        mime_type, _ = mimetypes.guess_type(str(image_path))
        return types_module.Part.from_bytes(
            data=image_path.read_bytes(),
            mime_type=mime_type or "image/jpeg",
        )

    def _load_sdk(self):
        try:
            from google import genai
            from google.genai import types
        except ModuleNotFoundError as error:
            raise ProviderDependencyError(
                "Brakuje pakietu google-genai. Doinstaluj zależności poleceniem: pip install -e .[dev]"
            ) from error

        return genai, types

    def _extract_text_from_response(self, response) -> str:
        text = getattr(response, "text", None)
        if isinstance(text, str) and text.strip():
            return text.strip()

        candidates = getattr(response, "candidates", None) or []
        extracted_parts: list[str] = []
        for candidate in candidates:
            content = getattr(candidate, "content", None)
            parts = getattr(content, "parts", None) or []
            for part in parts:
                part_text = getattr(part, "text", None)
                if isinstance(part_text, str) and part_text.strip():
                    extracted_parts.append(part_text.strip())

        return "\n".join(extracted_parts).strip()

    def _missing_api_key_message(self) -> str:
        message = (
            "Brak klucza API Gemini. Ustaw zmienną środowiskową GEMINI_API_KEY "
            "lub GOOGLE_API_KEY."
        )
        if self.config_path is not None:
            message += (
                f" Możesz też dodać lokalny plik {self.config_path} z polem "
                '"gemini_api_key".'
            )
        return message

    def _candidate_models(self) -> list[str]:
        if self.model_name in self.fallback_models:
            start_index = self.fallback_models.index(self.model_name)
            return list(self.fallback_models[start_index:])

        return [self.model_name, *[model for model in self.fallback_models if model != self.model_name]]

    def _generate_content_with_retries(self, client, model_name: str, contents: list[object]):
        last_error: Exception | None = None

        for attempt in range(1, self.retry_attempts + 1):
            try:
                return client.models.generate_content(
                    model=model_name,
                    contents=contents,
                )
            except Exception as error:  # pragma: no cover - zależne od SDK i sieci
                last_error = error
                if not self._is_retryable_error(error) or attempt >= self.retry_attempts:
                    raise

                backoff = self.initial_backoff_seconds * (2 ** (attempt - 1))
                self.sleep_func(backoff)

        if last_error is not None:  # pragma: no cover - pętla zawsze rzuca lub zwraca
            raise last_error

        raise ProviderRequestError("Nie udało się skontaktować z Gemini.")

    def _is_retryable_error(self, error: Exception) -> bool:
        lowered = str(error).lower()
        retryable_markers = (
            "503",
            "unavailable",
            "temporarily overloaded",
            "overloaded",
            "429",
            "resource_exhausted",
            "rate limit",
            "500",
            "internal",
            "timeout",
            "timed out",
            "deadline_exceeded",
            "connection",
            "network",
        )
        return any(marker in lowered for marker in retryable_markers)

    def _humanize_sdk_error(self, error: Exception) -> str:
        message = str(error).strip() or error.__class__.__name__
        lowered = message.lower()

        if "503" in lowered or "unavailable" in lowered or "overloaded" in lowered:
            return "Gemini jest chwilowo przeciążony. Spróbuj ponownie za moment."
        if "quota" in lowered or "429" in lowered or "rate limit" in lowered:
            return "Przekroczono limit API Gemini. Spróbuj ponownie później."
        if "api key" in lowered or "permission" in lowered or "unauthorized" in lowered:
            return "Gemini odrzucił klucz API lub uprawnienia do projektu."
        if "timeout" in lowered or "timed out" in lowered:
            return "Przekroczono czas oczekiwania na odpowiedź Gemini."
        if "connection" in lowered or "network" in lowered:
            return "Nie udało się połączyć z Gemini. Sprawdź internet i spróbuj ponownie."

        return f"Nie udało się przetworzyć notatki przez Gemini: {message}"
