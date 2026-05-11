from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass(frozen=True, slots=True)
class ProviderAccessContract:
    provider_key: str
    display_name: str
    category: str
    transport: str
    modalities: tuple[str, ...]
    auth_sources: tuple[str, ...] = ()
    default_model: str | None = None
    role: str = ""
    default_route: bool = False
    notes: tuple[str, ...] = ()
    failure_taxonomy: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


PROVIDER_ACCESS_CONTRACTS: dict[str, ProviderAccessContract] = {
    "codex_cli": ProviderAccessContract(
        provider_key="codex_cli",
        display_name="Codex CLI",
        category="cli_agent",
        transport="cli",
        modalities=("code", "text"),
        auth_sources=("codex_cli_login",),
        default_model="gpt-5.5",
        role="Complex coding, security protocol, and repo mutation fallback through the Codex CLI.",
        default_route=True,
        notes=("This is the real OpenAI-family route in the current environment; OPENAI_API_KEY is not assumed.",),
        failure_taxonomy=("cli_unavailable", "auth_missing", "execution_failed", "provider_timeout"),
    ),
    "openai_api": ProviderAccessContract(
        provider_key="openai_api",
        display_name="OpenAI API",
        category="api_model",
        transport="api",
        modalities=("text", "code"),
        auth_sources=("OPENAI_API_KEY",),
        default_model="gpt-5.5",
        role="Optional direct API route for chat/control-plane experiments.",
        default_route=False,
        notes=("Not a current primary route unless OPENAI_API_KEY is explicitly configured.",),
        failure_taxonomy=("provider_not_configured", "provider_auth_missing", "provider_call_failed", "provider_timeout"),
    ),
    "minimax_api": ProviderAccessContract(
        provider_key="minimax_api",
        display_name="MiniMax API",
        category="api_model",
        transport="api",
        modalities=("text", "code"),
        auth_sources=("MINIMAX_API_KEY", "MINIMAX_TOKEN"),
        default_model="MiniMax-M2.7",
        role="Direct coding, review, planning, and patch proposal route.",
        default_route=True,
        notes=("Direct API calls may generate unified diff proposals; repo mutation requires coding_patch_apply AutomationLease and workflow patch gates.",),
        failure_taxonomy=("provider_auth_missing", "provider_call_failed", "provider_timeout", "proposal_parse_failed"),
    ),
    "deepseek_api": ProviderAccessContract(
        provider_key="deepseek_api",
        display_name="DeepSeek API",
        category="api_model",
        transport="api",
        modalities=("text", "code"),
        auth_sources=("DEEPSEEK_API_KEY",),
        default_model="deepseek-v4-flash",
        role="Medium review, validation analysis, and patch proposal route.",
        default_route=True,
        notes=("Medium-lane fallback should go directly to Codex CLI, not MiniMax. Repo mutation requires coding_patch_apply AutomationLease and workflow patch gates.",),
        failure_taxonomy=("provider_auth_missing", "provider_call_failed", "provider_timeout", "proposal_parse_failed"),
    ),
    "opencode_cli": ProviderAccessContract(
        provider_key="opencode_cli",
        display_name="OpenCode CLI",
        category="cli_agent",
        transport="cli",
        modalities=("code", "text"),
        auth_sources=("opencode_auth", "MINIMAX_API_KEY", "DEEPSEEK_API_KEY"),
        default_model="minimax/MiniMax-M2.7",
        role="Low-cost external coding CLI shell and model-pool route.",
        default_route=True,
        notes=("OMO/OpenCode plugin ecosystem is not integrated in this repository yet.",),
        failure_taxonomy=("cli_unavailable", "auth_missing", "artifact_output_mismatch", "execution_failed", "provider_timeout"),
    ),
    "mmx_generation_api": ProviderAccessContract(
        provider_key="mmx_generation_api",
        display_name="MMX/MiniMax Generation API",
        category="asset_generator",
        transport="api",
        modalities=("image", "audio", "music", "video"),
        auth_sources=("MINIMAX_API_KEY", "MINIMAX_TOKEN"),
        default_model="image-01",
        role="Primary multimodal asset generation route for game art, UI, SFX, music, and future video.",
        default_route=True,
        notes=("Token Plan keys are supported for multimodal access; highspeed text models are not assumed.",),
        failure_taxonomy=("provider_auth_missing", "asset_generation_failed", "asset_download_failed", "provider_timeout"),
    ),
    "vertex_generation_api": ProviderAccessContract(
        provider_key="vertex_generation_api",
        display_name="Vertex Generation API",
        category="asset_generator",
        transport="api",
        modalities=("image", "video", "vision_review"),
        auth_sources=("GOOGLE_APPLICATION_CREDENTIALS", "GOOGLE_CLOUD_PROJECT", "GCLOUD_PROJECT", "gcloud_adc"),
        default_model="imagen-4.0-generate-001",
        role="Vertex AI REST route for Imagen image generation and Gemini-family visual review.",
        default_route=False,
        notes=(
            "gcloud is an auth/environment tool, not an independent worker adapter.",
            "Cloud TTS is tracked separately as gcp_tts_api.",
            "Current M77 implementation covers vertex_imagen and vertex_gemini_review probes; Veo/video remains future work.",
            "Local probes prefer the active gcloud user token and can force ADC with WORKFLOW_GCP_AUTH_MODE=adc.",
        ),
        failure_taxonomy=("provider_auth_missing", "gcloud_missing", "asset_generation_failed", "provider_timeout"),
    ),
    "gcp_tts_api": ProviderAccessContract(
        provider_key="gcp_tts_api",
        display_name="Google Cloud Text-to-Speech API",
        category="asset_generator",
        transport="api",
        modalities=("audio",),
        auth_sources=("GOOGLE_APPLICATION_CREDENTIALS", "GOOGLE_CLOUD_PROJECT", "GCLOUD_PROJECT", "gcloud_adc"),
        default_model="cloud-tts",
        role="GCP Cloud Text-to-Speech route for voice/audio fallback; not Vertex AI proper.",
        default_route=False,
        notes=("Requires texttospeech.googleapis.com, quota project, and billing on the selected GCP project.",),
        failure_taxonomy=("provider_auth_missing", "gcp_quota_project_missing", "gcp_service_disabled", "gcp_permission_denied", "provider_timeout"),
    ),
    "mcp_tool": ProviderAccessContract(
        provider_key="mcp_tool",
        display_name="MCP Tool Broker",
        category="mcp_tool",
        transport="mcp",
        modalities=("tool",),
        auth_sources=("profile_env",),
        role="Tool access layer for workspace, search, image understanding, and external business tools.",
        default_route=False,
        notes=("MCP is not an LLM provider in this project; tools must be explicitly selected.",),
        failure_taxonomy=("dependency_missing", "tool_unavailable", "startup_failed", "call_timeout"),
    ),
    "langchain_agent": ProviderAccessContract(
        provider_key="langchain_agent",
        display_name="LangChain Agent",
        category="experimental_agent_framework",
        transport="langchain",
        modalities=("text", "tool"),
        auth_sources=("MINIMAX_API_KEY", "DEEPSEEK_API_KEY", "OPENAI_API_KEY"),
        role="Experimental opt-in agent framework for dynamic tools, RAG, and MCP composition.",
        default_route=False,
        notes=("Not part of the default provider route or control-plane core.",),
        failure_taxonomy=("dependency_missing", "provider_auth_missing", "agent_runtime_failed", "fallback_route_failed"),
    ),
}


def list_provider_access_contracts() -> list[dict[str, object]]:
    return [PROVIDER_ACCESS_CONTRACTS[key].to_dict() for key in sorted(PROVIDER_ACCESS_CONTRACTS)]


def provider_access_contract_for_key(provider_key: str | None) -> dict[str, object] | None:
    if provider_key is None:
        return None
    contract = PROVIDER_ACCESS_CONTRACTS.get(str(provider_key).strip().lower())
    return contract.to_dict() if contract is not None else None
