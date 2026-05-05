from pathlib import Path

from app.services.ai_provider import (
    DEFAULT_FALLBACK_MODELS,
    GeminiAIProvider,
    InvalidProviderResponseError,
    MissingAPIKeyError,
    ProviderRequestError,
    TRANSCRIPTION_MODE_LABELS,
    build_transcription_prompt,
)


class FakeTypesModule:
    class Part:
        @staticmethod
        def from_bytes(*, data: bytes, mime_type: str):
            return {
                "data": data,
                "mime_type": mime_type,
            }


class FakeResponse:
    def __init__(self, text: str | None) -> None:
        self.text = text


class FakeModels:
    def __init__(self, responses_by_model: dict[str, list[object]]) -> None:
        self.responses_by_model = responses_by_model
        self.calls: list[dict[str, object]] = []

    def generate_content(self, *, model: str, contents: list[object]):
        self.calls.append(
            {
                "model": model,
                "contents": contents,
            }
        )
        queue = self.responses_by_model.setdefault(model, [])
        if not queue:
            raise AssertionError(f"Missing fake response for model {model}")

        outcome = queue.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


class FakeClient:
    def __init__(self, responses_by_model: dict[str, list[object]]) -> None:
        self.models = FakeModels(responses_by_model)


def test_build_transcription_prompt_contains_required_rules() -> None:
    prompt = build_transcription_prompt("faithful")

    assert "Nie poprawiaj stylu" in prompt
    assert "Nie dodawaj nagłówków" in prompt
    assert "Nie tłumacz notatki na język polski" in prompt
    assert "If the handwritten note is in English" in prompt
    assert "return the final note in English only" in prompt
    assert "[nieczytelne]" in prompt
    assert "[unreadable]" in prompt
    assert "Nie dopisuj informacji" in prompt


def test_build_transcription_prompt_supports_all_declared_modes() -> None:
    for mode in TRANSCRIPTION_MODE_LABELS:
        prompt = build_transcription_prompt(mode)
        assert isinstance(prompt, str)
        assert "[nieczytelne]" in prompt


def test_build_transcription_prompt_for_formatted_mode_emphasizes_visual_formatting() -> None:
    prompt = build_transcription_prompt("formatted")

    assert "estetycznym sformatowaniu" in prompt
    assert "Nie zmieniaj sensu tekstu" in prompt


def test_build_transcription_prompt_for_organized_mode_allows_style_cleanup_without_new_facts() -> None:
    prompt = build_transcription_prompt("organized")

    assert "Poprawiaj błędy stylistyczne" in prompt
    assert "Nie halucynuj" in prompt
    assert "nie dodawaj nowych informacji merytorycznych" in prompt


def test_build_transcription_prompt_for_expanded_mode_limits_added_content() -> None:
    prompt = build_transcription_prompt("expanded")

    assert "Łączna długość dopisanego przez Ciebie tekstu nie może przekroczyć 50%" in prompt
    assert "Jeśli nie masz wysokiej pewności, nie dopisuj nowych informacji" in prompt


def test_gemini_provider_requires_api_key() -> None:
    provider = GeminiAIProvider(api_key=None, model_name="gemini-test")

    try:
        provider.transcribe_images([Path("example.jpg")])
    except MissingAPIKeyError as error:
        assert "Ustaw klucz API Gemini w aplikacji w Ustawieniach" in str(error)
    else:  # pragma: no cover
        raise AssertionError("Expected MissingAPIKeyError")


def test_gemini_provider_uses_english_messages_when_configured() -> None:
    provider = GeminiAIProvider(api_key=None, model_name="gemini-test", language="en")

    try:
        provider.transcribe_images([Path("example.jpg")])
    except MissingAPIKeyError as error:
        assert "Gemini API key is missing" in str(error)
        assert "Settings" in str(error)
    else:  # pragma: no cover
        raise AssertionError("Expected MissingAPIKeyError")


def test_gemini_provider_builds_request_with_images_and_prompt(tmp_path: Path) -> None:
    image_path = tmp_path / "note.jpg"
    image_path.write_bytes(b"image-bytes")

    provider = GeminiAIProvider(api_key="key", model_name="gemini-test")
    fake_client = FakeClient({"gemini-test": [FakeResponse("Przepisana notatka")]})
    provider._create_client = lambda: fake_client
    provider._load_sdk = lambda: (None, FakeTypesModule)

    result = provider.transcribe_images([image_path], transcription_mode="organized")

    assert result.text == "Przepisana notatka"
    assert result.model_name == "gemini-test"
    assert result.transcription_mode == "organized"
    assert fake_client.models.calls[0]["model"] == "gemini-test"
    contents = fake_client.models.calls[0]["contents"]
    assert isinstance(contents[0], str)
    assert "uporządkuj" in contents[0].lower()
    assert "nie halucynuj" in contents[0].lower()
    assert contents[1]["mime_type"] == "image/jpeg"


def test_gemini_provider_rejects_empty_text_response(tmp_path: Path) -> None:
    image_path = tmp_path / "note.jpg"
    image_path.write_bytes(b"image-bytes")

    provider = GeminiAIProvider(api_key="key", model_name="gemini-test")
    provider._create_client = lambda: FakeClient({"gemini-test": [FakeResponse("   ")]})
    provider._load_sdk = lambda: (None, FakeTypesModule)

    try:
        provider.transcribe_images([image_path])
    except InvalidProviderResponseError:
        pass
    else:  # pragma: no cover
        raise AssertionError("Expected InvalidProviderResponseError")


def test_gemini_provider_retries_same_model_before_success(tmp_path: Path) -> None:
    image_path = tmp_path / "note.jpg"
    image_path.write_bytes(b"image-bytes")
    recorded_sleeps: list[float] = []

    provider = GeminiAIProvider(
        api_key="key",
        model_name="gemini-test",
        fallback_models=("gemini-test",),
        retry_attempts=3,
        initial_backoff_seconds=0.5,
        sleep_func=recorded_sleeps.append,
    )
    provider._create_client = lambda: FakeClient(
        {
            "gemini-test": [
                RuntimeError("503 UNAVAILABLE"),
                RuntimeError("503 UNAVAILABLE"),
                FakeResponse("Udana trzecia próba"),
            ]
        }
    )
    provider._load_sdk = lambda: (None, FakeTypesModule)

    result = provider.transcribe_images([image_path])

    assert result.text == "Udana trzecia próba"
    assert recorded_sleeps == [0.5, 1.0]


def test_gemini_provider_falls_back_to_next_model_on_503(tmp_path: Path) -> None:
    image_path = tmp_path / "note.jpg"
    image_path.write_bytes(b"image-bytes")

    provider = GeminiAIProvider(
        api_key="key",
        model_name="gemini-2.5-flash-lite",
        retry_attempts=2,
        initial_backoff_seconds=0.1,
        sleep_func=lambda _seconds: None,
    )
    fake_client = FakeClient(
        {
            "gemini-2.5-flash-lite": [
                RuntimeError("503 UNAVAILABLE"),
                RuntimeError("503 UNAVAILABLE"),
            ],
            "gemini-2.5-flash": [
                FakeResponse("Z fallbacku"),
            ],
        }
    )
    provider._create_client = lambda: fake_client
    provider._load_sdk = lambda: (None, FakeTypesModule)

    result = provider.transcribe_images([image_path])

    assert result.text == "Z fallbacku"
    assert result.model_name == "gemini-2.5-flash"
    assert [call["model"] for call in fake_client.models.calls] == [
        "gemini-2.5-flash-lite",
        "gemini-2.5-flash-lite",
        "gemini-2.5-flash",
    ]


def test_gemini_provider_reports_all_attempted_models_when_capacity_is_exhausted(tmp_path: Path) -> None:
    image_path = tmp_path / "note.jpg"
    image_path.write_bytes(b"image-bytes")

    provider = GeminiAIProvider(
        api_key="key",
        model_name=DEFAULT_FALLBACK_MODELS[0],
        retry_attempts=1,
        initial_backoff_seconds=0.1,
        sleep_func=lambda _seconds: None,
    )
    responses = {
        model_name: [RuntimeError("503 UNAVAILABLE")]
        for model_name in DEFAULT_FALLBACK_MODELS
    }
    provider._create_client = lambda: FakeClient(responses)
    provider._load_sdk = lambda: (None, FakeTypesModule)

    try:
        provider.transcribe_images([image_path])
    except ProviderRequestError as error:
        message = str(error)
        assert "Próbowano modeli" in message
        assert "gemini-3-flash-preview" in message
    else:  # pragma: no cover
        raise AssertionError("Expected ProviderRequestError")
