"""The default runner of an audit job: builds the provider and the agents, then runs the pipeline."""

import threading
from pathlib import Path

from auditagent.agents.commercial_extractor import CommercialExtractor
from auditagent.agents.legal_extractor import LegalExtractor
from auditagent.config import Settings, get_settings
from auditagent.ingestion.embedder import SentenceTransformerEmbedder
from auditagent.llm.base import LLMProvider
from auditagent.llm.factory import build_provider
from auditagent.pipeline.run import AuditReport, audit_files

_lock = threading.Lock()
_embedder: SentenceTransformerEmbedder | None = None
_providers: dict[tuple[str, str], LLMProvider] = {}


def _settings(provider_name: str | None, model: str | None) -> Settings:
    """The settings of .env with the provider and the model of this audit (when given)."""
    settings = get_settings()
    updates = {}
    if provider_name:
        updates["llm_provider"] = provider_name
    chosen = provider_name or settings.llm_provider
    if model:
        updates["ollama_model" if chosen == "ollama" else "gemini_model"] = model
    return settings.model_copy(update=updates) if updates else settings


def get_embedder() -> SentenceTransformerEmbedder:
    """The local embedding model, loaded once per process (TODO item 34)."""
    global _embedder
    with _lock:
        if _embedder is None:
            embedder = SentenceTransformerEmbedder()
            embedder.embed(["warm up"])
            _embedder = embedder
        return _embedder


def get_provider(provider_name: str | None, model: str | None) -> LLMProvider:
    """One provider per (provider, model), so that the gap between Gemini calls holds across jobs."""
    settings = _settings(provider_name, model)
    name = settings.llm_provider
    key = (name, settings.ollama_model if name == "ollama" else settings.gemini_model)
    with _lock:
        if key not in _providers:
            _providers[key] = build_provider(settings)
        return _providers[key]


def run_audit(
    contract: Path, purchase_order: Path, invoice: Path, provider: str | None, model: str | None
) -> AuditReport:
    """Run Agent 1, Agent 2 and the rule engine on three PDF files."""
    llm = get_provider(provider, model)
    legal = LegalExtractor(llm, get_embedder())
    commercial = CommercialExtractor(llm)
    return audit_files(contract, purchase_order, invoice, legal, commercial)
