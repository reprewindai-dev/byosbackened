from core.config import Settings


def test_ai_integrations_openai_env_aliases_override_runtime_base_url():
    settings = Settings(
        openai_api_key="",
        openai_base_url="https://api.openai.com/v1",
        ai_integrations_openai_base_url="http://localhost:1106/modelfarm/openai",
        ai_integrations_openai_api_key="_DUMMY_API_KEY_",
    )

    assert settings.openai_base_url == "http://localhost:1106/modelfarm/openai"
    assert settings.openai_api_key == "_DUMMY_API_KEY_"


def test_ai_integrations_gemini_env_aliases_configure_modelfarm_runtime():
    settings = Settings(
        gemini_api_key="",
        gemini_base_url="https://generativelanguage.googleapis.com/v1beta/openai",
        ai_integrations_gemini_base_url="http://localhost:1106/modelfarm/gemini",
        ai_integrations_gemini_api_key="_DUMMY_API_KEY_",
    )

    assert settings.gemini_base_url == "http://localhost:1106/modelfarm/gemini"
    assert settings.gemini_api_key == "_DUMMY_API_KEY_"
    assert settings.gemini_model_chat == "gemini-2.5-pro"
