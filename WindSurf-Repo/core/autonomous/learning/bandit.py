"""Multi-armed bandit for exploration/exploitation in routing."""

from typing import Dict, List, Optional
from decimal import Decimal
from datetime import datetime, timedelta
import math
import random
import logging

logger = logging.getLogger(__name__)


class MultiArmedBandit:
    """
    Multi-armed bandit for autonomous provider selection.

    Balances exploration (try new providers) vs exploitation (use what works).
    Learns per workspace - creates non-portable intelligence.
    """

    def __init__(self, workspace_id: str):
        self.workspace_id = workspace_id
        self.arms: Dict[str, Dict] = {}  # provider -> {count, reward_sum, avg_reward}
        self.exploration_rate = 0.1  # 10% exploration, 90% exploitation
        self.min_exploration_rate = 0.05  # Never go below 5% exploration (always learn)
        self.min_samples = 10  # Need at least 10 samples before trusting
        self.fallback_provider: Optional[str] = None  # Safest provider as fallback

    def select_arm(
        self,
        available_providers: List[str],
        operation_type: str,
        constraints: Optional[Dict] = None,
    ) -> str:
        """
        Select provider using epsilon-greedy strategy with guardrails.

        Exploits best known provider most of the time.
        Explores new providers occasionally.
        Includes safety constraints and fallback logic.
        """
        constraints = constraints or {}

        # Initialize arms if not seen before
        for provider in available_providers:
            if provider not in self.arms:
                self.arms[provider] = {
                    "count": 0,
                    "reward_sum": 0.0,
                    "avg_reward": 0.0,
                    "last_used": None,
                    "failure_count": 0,  # Track failures for circuit breaker
                }

        # Filter providers by safety constraints
        safe_providers = self._filter_by_constraints(available_providers, constraints)

        if not safe_providers:
            # No safe providers, use fallback
            fallback = self._get_fallback_provider(available_providers)
            logger.warning(
                f"No safe providers found for workspace {self.workspace_id}, "
                f"using fallback: {fallback}"
            )
            return fallback

        # Ensure exploration rate never goes below minimum
        effective_exploration_rate = max(self.exploration_rate, self.min_exploration_rate)

        # Epsilon-greedy: explore with probability epsilon
        if random.random() < effective_exploration_rate:
            # Explore: choose random safe provider
            selected = random.choice(safe_providers)
            logger.debug(f"Exploring: selected {selected} for workspace {self.workspace_id}")
        else:
            # Exploit: choose best known provider
            # Use upper confidence bound for providers with few samples
            best_provider = None
            best_score = float("-inf")
            confidence_threshold = 0.5  # Minimum confidence to use ML selection

            for provider in safe_providers:
                arm = self.arms[provider]

                # Check confidence (based on sample count)
                confidence = min(arm["count"] / (self.min_samples * 2), 1.0)

                if confidence < confidence_threshold:
                    # Confidence too low, skip this provider
                    continue

                if arm["count"] < self.min_samples:
                    # Not enough samples - use optimistic estimate
                    score = 1.0  # Optimistic
                else:
                    # Use average reward with confidence interval
                    # UCB: avg_reward + sqrt(2 * log(total_count) / count)
                    total_count = sum(a["count"] for a in self.arms.values())
                    ucb = math.sqrt(2 * math.log(total_count + 1) / arm["count"])
                    score = arm["avg_reward"] + ucb

                if score > best_score:
                    best_score = score
                    best_provider = provider

            # If no provider meets confidence threshold, use fallback
            if not best_provider:
                selected = self._get_fallback_provider(safe_providers)
                logger.warning(
                    f"Low confidence for all providers, using fallback: {selected} "
                    f"for workspace {self.workspace_id}"
                )
            else:
                selected = best_provider
                logger.debug(
                    f"Exploiting: selected {selected} (avg_reward={self.arms[selected]['avg_reward']:.3f}, "
                    f"confidence={min(self.arms[selected]['count'] / (self.min_samples * 2), 1.0):.2f}) "
                    f"for workspace {self.workspace_id}"
                )

        # Update last used and set as fallback if it's the safest
        self.arms[selected]["last_used"] = datetime.utcnow()
        self._update_fallback_provider()

        return selected

    def _filter_by_constraints(
        self,
        providers: List[str],
        constraints: Dict,
    ) -> List[str]:
        """Filter providers by safety constraints."""
        safe_providers = []

        max_latency_ms = constraints.get("max_latency_ms")
        max_cost = constraints.get("max_cost")

        for provider in providers:
            arm = self.arms.get(provider, {})

            # Check latency constraint (if we have historical data)
            if max_latency_ms and "avg_latency_ms" in arm:
                if arm["avg_latency_ms"] > max_latency_ms:
                    logger.debug(
                        f"Provider {provider} excluded: latency {arm['avg_latency_ms']} > {max_latency_ms}"
                    )
                    continue

            # Check cost constraint (if we have historical data)
            if max_cost and "avg_cost" in arm:
                if arm["avg_cost"] > float(max_cost):
                    logger.debug(
                        f"Provider {provider} excluded: cost {arm['avg_cost']} > {max_cost}"
                    )
                    continue

            # Check circuit breaker (if provider has too many failures)
            failure_count = arm.get("failure_count", 0)
            if failure_count >= 5:  # Circuit breaker threshold
                logger.debug(
                    f"Provider {provider} excluded: circuit breaker open (failures: {failure_count})"
                )
                continue

            safe_providers.append(provider)

        return safe_providers if safe_providers else providers  # Return all if none safe

    def _get_fallback_provider(self, available_providers: List[str]) -> str:
        """Get safest fallback provider."""
        # Use fallback if set and available
        if self.fallback_provider and self.fallback_provider in available_providers:
            return self.fallback_provider

        # Otherwise, use provider with highest average reward (most reliable)
        if self.arms:
            best_provider = max(
                (p for p in available_providers if p in self.arms),
                key=lambda p: self.arms[p].get("avg_reward", 0.0),
                default=None,
            )
            if best_provider:
                return best_provider

        # Last resort: return first available
        return available_providers[0] if available_providers else "huggingface"

    def _update_fallback_provider(self):
        """Update fallback provider to safest option."""
        if not self.arms:
            return

        # Find provider with highest average reward and sufficient samples
        best_provider = None
        best_reward = float("-inf")

        for provider, arm in self.arms.items():
            if arm["count"] >= self.min_samples:
                reward = arm["avg_reward"]
                failure_rate = arm.get("failure_count", 0) / max(arm["count"], 1)

                # Prefer providers with high reward and low failure rate
                adjusted_reward = reward * (1.0 - failure_rate)

                if adjusted_reward > best_reward:
                    best_reward = adjusted_reward
                    best_provider = provider

        if best_provider:
            self.fallback_provider = best_provider

    def update_reward(
        self,
        provider: str,
        reward: float,
        success: bool = True,
    ):
        """
        Update reward for provider.

        Reward is normalized: higher is better.
        Can be based on: cost savings, quality, latency, or combination.
        """
        if provider not in self.arms:
            self.arms[provider] = {
                "count": 0,
                "reward_sum": 0.0,
                "avg_reward": 0.0,
                "last_used": None,
                "failure_count": 0,
            }

        arm = self.arms[provider]
        arm["count"] += 1

        # Track failures for circuit breaker
        if not success:
            arm["failure_count"] = arm.get("failure_count", 0) + 1
        else:
            # Reset failure count on success (circuit breaker recovery)
            if arm.get("failure_count", 0) > 0:
                arm["failure_count"] = max(0, arm["failure_count"] - 1)

        arm["reward_sum"] += reward

        # Update average (exponential moving average for faster adaptation)
        alpha = 0.1  # Learning rate
        if arm["count"] == 1:
            arm["avg_reward"] = reward
        else:
            arm["avg_reward"] = alpha * reward + (1 - alpha) * arm["avg_reward"]

        # Update fallback provider if this becomes the safest
        self._update_fallback_provider()

        logger.debug(
            f"Updated reward for {provider}: reward={reward:.3f}, "
            f"avg_reward={arm['avg_reward']:.3f}, count={arm['count']}, "
            f"failures={arm.get('failure_count', 0)}"
        )

    def calculate_reward(
        self,
        cost: Decimal,
        quality: float,
        latency_ms: int,
        baseline_cost: Decimal,
    ) -> float:
        """
        Calculate reward from outcome.

        Reward combines:
        - Cost savings (higher savings = higher reward)
        - Quality (higher quality = higher reward)
        - Latency (lower latency = higher reward)
        """
        # Normalize cost savings (0-1 scale)
        if baseline_cost > 0:
            cost_savings = float((baseline_cost - cost) / baseline_cost)
            cost_savings = max(0, min(1, cost_savings))  # Clamp to [0, 1]
        else:
            cost_savings = 0.5  # Neutral if no baseline

        # Normalize quality (already 0-1)
        quality_norm = quality

        # Normalize latency (lower is better, assume max 10s)
        latency_norm = 1.0 - min(latency_ms / 10000, 1.0)

        # Weighted combination
        reward = (
            cost_savings * 0.5  # Cost savings is most important
            + quality_norm * 0.3  # Quality matters
            + latency_norm * 0.2  # Latency matters less
        )

        return reward

    def get_best_arm(self) -> Optional[str]:
        """Get best performing provider."""
        if not self.arms:
            return None

        best_provider = None
        best_reward = float("-inf")

        for provider, arm in self.arms.items():
            if arm["count"] >= self.min_samples and arm["avg_reward"] > best_reward:
                best_reward = arm["avg_reward"]
                best_provider = provider

        return best_provider

    def get_stats(self) -> Dict[str, Dict]:
        """Get statistics for all arms."""
        return {
            provider: {
                "count": arm["count"],
                "avg_reward": arm["avg_reward"],
                "last_used": arm["last_used"].isoformat() if arm["last_used"] else None,
            }
            for provider, arm in self.arms.items()
        }
