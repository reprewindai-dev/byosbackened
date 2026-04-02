"""Provider registry - dynamic provider management."""

from typing import Dict, List, Optional, Type
from apps.ai.contracts import STTProvider, LLMProvider, SearchProvider
import importlib
import logging

logger = logging.getLogger(__name__)


class ProviderRegistry:
    """Registry for AI providers."""

    def __init__(self):
        self.stt_providers: Dict[str, Type[STTProvider]] = {}
        self.llm_providers: Dict[str, Type[LLMProvider]] = {}
        self.search_providers: Dict[str, Type[SearchProvider]] = {}
        self.provider_instances: Dict[str, any] = {}

    def register_stt_provider(self, name: str, provider_class: Type[STTProvider]):
        """Register STT provider."""
        self.stt_providers[name] = provider_class
        logger.info(f"Registered STT provider: {name}")

    def register_llm_provider(self, name: str, provider_class: Type[LLMProvider]):
        """Register LLM provider."""
        self.llm_providers[name] = provider_class
        logger.info(f"Registered LLM provider: {name}")

    def register_search_provider(self, name: str, provider_class: Type[SearchProvider]):
        """Register search provider."""
        self.search_providers[name] = provider_class
        logger.info(f"Registered search provider: {name}")

    def get_stt_provider(self, name: str) -> Optional[STTProvider]:
        """Get STT provider instance."""
        if name not in self.stt_providers:
            return None

        # Return cached instance or create new
        cache_key = f"stt:{name}"
        if cache_key not in self.provider_instances:
            self.provider_instances[cache_key] = self.stt_providers[name]()
        return self.provider_instances[cache_key]

    def get_llm_provider(self, name: str) -> Optional[LLMProvider]:
        """Get LLM provider instance."""
        if name not in self.llm_providers:
            return None

        cache_key = f"llm:{name}"
        if cache_key not in self.provider_instances:
            self.provider_instances[cache_key] = self.llm_providers[name]()
        return self.provider_instances[cache_key]

    def get_search_provider(self, name: str) -> Optional[SearchProvider]:
        """Get search provider instance."""
        if name not in self.search_providers:
            return None

        cache_key = f"search:{name}"
        if cache_key not in self.provider_instances:
            self.provider_instances[cache_key] = self.search_providers[name]()
        return self.provider_instances[cache_key]

    def list_providers(self) -> Dict[str, List[str]]:
        """List all registered providers."""
        return {
            "stt": list(self.stt_providers.keys()),
            "llm": list(self.llm_providers.keys()),
            "search": list(self.search_providers.keys()),
        }

    def load_plugin_provider(self, plugin_path: str, provider_name: str):
        """Load provider from plugin."""
        try:
            module = importlib.import_module(plugin_path)
            provider_class = getattr(module, provider_name)

            # Auto-detect provider type and register
            if issubclass(provider_class, STTProvider):
                self.register_stt_provider(provider_name, provider_class)
            elif issubclass(provider_class, LLMProvider):
                self.register_llm_provider(provider_name, provider_class)
            elif issubclass(provider_class, SearchProvider):
                self.register_search_provider(provider_name, provider_class)
            else:
                logger.warning(f"Unknown provider type: {provider_name}")
        except Exception as e:
            logger.error(f"Failed to load plugin provider {provider_name}: {e}")


# Global registry
_registry = ProviderRegistry()


def get_registry() -> ProviderRegistry:
    """Get provider registry."""
    return _registry
