"""Provider registry - dynamic provider management."""
from typing import Dict, List, Optional, Type, Callable, TypeVar
from apps.ai.contracts import STTProvider, LLMProvider, SearchProvider
from core.providers.circuit_breaker import get_circuit_breaker_manager, CircuitBreakerOpenError
from core.providers.timeout_retry import get_timeout_retry
import importlib
import logging

logger = logging.getLogger(__name__)

T = TypeVar("T")


class ProviderRegistry:
    """Registry for AI providers with circuit breaker and timeout/retry protection."""

    def __init__(self):
        self.stt_providers: Dict[str, Type[STTProvider]] = {}
        self.llm_providers: Dict[str, Type[LLMProvider]] = {}
        self.search_providers: Dict[str, Type[SearchProvider]] = {}
        self.provider_instances: Dict[str, any] = {}
        self._cb_manager = get_circuit_breaker_manager()
        self._timeout_retry = get_timeout_retry()

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

    def _get_instance(self, cache_key: str, factory: Callable[[], T]) -> T:
        """Get or create a cached provider instance."""
        if cache_key not in self.provider_instances:
            self.provider_instances[cache_key] = factory()
        return self.provider_instances[cache_key]

    def is_provider_available(self, name: str) -> bool:
        """Check if a provider's circuit breaker is closed (healthy)."""
        return not self._cb_manager.is_open(name)

    def get_stt_provider(self, name: str) -> Optional[STTProvider]:
        """Get STT provider instance. Returns None if circuit is open."""
        if name not in self.stt_providers:
            return None

        if self._cb_manager.is_open(name):
            logger.warning(f"STT provider {name} circuit is OPEN — skipping")
            return None

        return self._get_instance(f"stt:{name}", lambda: self.stt_providers[name]())

    def get_llm_provider(self, name: str) -> Optional[LLMProvider]:
        """Get LLM provider instance. Returns None if circuit is open."""
        if name not in self.llm_providers:
            return None

        if self._cb_manager.is_open(name):
            logger.warning(f"LLM provider {name} circuit is OPEN — skipping")
            return None

        return self._get_instance(f"llm:{name}", lambda: self.llm_providers[name]())

    def get_search_provider(self, name: str) -> Optional[SearchProvider]:
        """Get search provider instance."""
        if name not in self.search_providers:
            return None

        return self._get_instance(f"search:{name}", lambda: self.search_providers[name]())

    def call_provider(self, name: str, func: Callable[..., T], *args, **kwargs) -> T:
        """
        Execute a provider function with circuit breaker + timeout/retry protection.

        Usage:
            result = registry.call_provider("ollama", provider.generate, prompt=...)

        Raises:
            CircuitBreakerOpenError: if the provider circuit is open
            Exception: after retries are exhausted
        """
        breaker = self._cb_manager.get_breaker(name)
        return breaker.call(
            self._timeout_retry.execute_with_retry,
            name,
            func,
            *args,
            **kwargs,
        )

    def get_circuit_states(self) -> Dict[str, Dict]:
        """Get circuit breaker states for all tracked providers."""
        return self._cb_manager.get_all_states()

    def list_providers(self) -> Dict[str, List[str]]:
        """List all registered providers."""
        return {
            "stt": list(self.stt_providers.keys()),
            "llm": list(self.llm_providers.keys()),
            "search": list(self.search_providers.keys()),
        }

    def list_available_providers(self) -> Dict[str, List[str]]:
        """List providers that are currently available (circuit closed)."""
        return {
            ptype: [name for name in names if not self._cb_manager.is_open(name)]
            for ptype, names in self.list_providers().items()
        }

    def load_plugin_provider(self, plugin_path: str, provider_name: str):
        """Load provider from plugin."""
        try:
            module = importlib.import_module(plugin_path)
            provider_class = getattr(module, provider_name)

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
