"""Bitcoin payment processing for global subscriptions."""

import httpx
import hmac
import hashlib
import json
import time
from typing import Dict, Optional, Any
from datetime import datetime, timedelta
import logging
from core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class BitcoinPaymentProcessor:
    """Bitcoin payment processor using Coinbase Commerce API."""

    def __init__(self):
        self.api_key = settings.coinbase_commerce_api_key
        self.webhook_secret = settings.coinbase_commerce_webhook_secret

        if not self.api_key:
            logger.warning(
                "COINBASE_COMMERCE_API_KEY not configured. Bitcoin payments will not work."
            )
            logger.warning("Run: python setup_bitcoin_account.py")
            # Don't raise error, just log warning - allows testing without Bitcoin

        self.base_url = "https://api.commerce.coinbase.com"
        headers = {
            "X-CC-Version": "2018-03-22",
            "Content-Type": "application/json",
        }

        if self.api_key:
            headers["X-CC-Api-Key"] = self.api_key

        self.client = httpx.AsyncClient(timeout=30.0, headers=headers)

    async def create_charge(
        self,
        amount: float,
        currency: str = "USD",
        name: str = "Premium Subscription",
        description: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Create a Bitcoin payment charge.

        Args:
            amount: Amount in USD (will be converted to BTC)
            currency: Base currency (USD)
            name: Charge name
            description: Charge description
            metadata: Additional metadata

        Returns:
            Charge object with payment URL
        """
        try:
            # Coinbase Commerce accepts USD and converts to crypto
            payload = {
                "name": name,
                "description": description or f"Premium subscription - ${amount:.2f}",
                "pricing_type": "fixed_price",
                "local_price": {
                    "amount": f"{amount:.2f}",
                    "currency": currency,
                },
                "metadata": metadata or {},
            }

            response = await self.client.post(f"{self.base_url}/charges", json=payload)

            if response.status_code == 201:
                charge = response.json()["data"]
                return {
                    "charge_id": charge["id"],
                    "payment_url": charge["hosted_url"],
                    "code": charge["code"],
                    "amount": amount,
                    "currency": currency,
                    "crypto_amount": charge.get("pricing", {}).get("local", {}).get("amount"),
                    "crypto_currency": charge.get("pricing", {})
                    .get("crypto", {})
                    .get("currency", "BTC"),
                    "expires_at": charge.get("expires_at"),
                    "status": charge.get("timeline", [{}])[-1].get("status", "NEW"),
                }
            else:
                logger.error(f"Failed to create charge: {response.status_code} - {response.text}")
                raise Exception(f"Failed to create charge: {response.status_code}")

        except Exception as e:
            logger.error(f"Bitcoin charge creation error: {e}")
            raise

    async def get_charge(self, charge_id: str) -> Optional[Dict[str, Any]]:
        """Get charge status."""
        try:
            response = await self.client.get(f"{self.base_url}/charges/{charge_id}")

            if response.status_code == 200:
                charge = response.json()["data"]
                return {
                    "charge_id": charge["id"],
                    "status": charge.get("timeline", [{}])[-1].get("status", "NEW"),
                    "payment_url": charge.get("hosted_url"),
                    "expires_at": charge.get("expires_at"),
                }
        except Exception as e:
            logger.error(f"Failed to get charge: {e}")

        return None

    def verify_webhook(
        self,
        payload: str,
        signature: str,
    ) -> bool:
        """
        Verify webhook signature from Coinbase Commerce.

        Args:
            payload: Raw request body
            signature: X-CC-Webhook-Signature header

        Returns:
            True if signature is valid
        """
        try:
            # Coinbase Commerce uses HMAC SHA256
            expected_signature = hmac.new(
                self.webhook_secret.encode(), payload.encode(), hashlib.sha256
            ).hexdigest()

            return hmac.compare_digest(expected_signature, signature)
        except Exception as e:
            logger.error(f"Webhook verification error: {e}")
            return False

    async def process_webhook(self, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Process webhook event from Coinbase Commerce.

        Returns:
            Event data if valid, None otherwise
        """
        event_type = payload.get("event", {}).get("type")
        charge_data = payload.get("event", {}).get("data", {})

        if event_type in ["charge:confirmed", "charge:resolved"]:
            return {
                "charge_id": charge_data.get("id"),
                "status": "completed",
                "amount": charge_data.get("pricing", {}).get("local", {}).get("amount"),
                "currency": charge_data.get("pricing", {}).get("local", {}).get("currency"),
                "metadata": charge_data.get("metadata", {}),
            }
        elif event_type == "charge:failed":
            return {
                "charge_id": charge_data.get("id"),
                "status": "failed",
                "metadata": charge_data.get("metadata", {}),
            }

        return None

    async def close(self):
        """Close HTTP client."""
        await self.client.aclose()


class BitcoinWallet:
    """Bitcoin wallet configuration and management."""

    def __init__(self):
        # For production, use a proper Bitcoin wallet service
        # This is a placeholder - you'll need to set up actual wallet
        self.wallet_address = settings.bitcoin_wallet_address
        self.network = settings.bitcoin_network  # "mainnet" or "testnet"

    def get_wallet_address(self) -> str:
        """Get Bitcoin wallet address for receiving payments."""
        return self.wallet_address

    def generate_payment_address(self, user_id: str, subscription_id: str) -> Dict[str, str]:
        """
        Generate a unique payment address for a subscription.

        In production, use a proper Bitcoin wallet API to generate addresses.
        For now, returns the main wallet address.
        """
        # In production, integrate with:
        # - Electrum wallet API
        # - Bitcoin Core RPC
        # - Blockchain.info API
        # - Or use Coinbase Commerce (handles addresses automatically)

        return {
            "address": self.wallet_address,
            "user_id": user_id,
            "subscription_id": subscription_id,
        }

    async def check_payment_received(
        self,
        address: str,
        expected_amount_btc: float,
    ) -> bool:
        """
        Check if payment was received at address.

        In production, use blockchain API to check:
        - blockchain.info API
        - blockcypher.com API
        - Or rely on Coinbase Commerce webhooks
        """
        # Placeholder - in production, check blockchain
        return False


def get_bitcoin_processor() -> BitcoinPaymentProcessor:
    """Get Bitcoin payment processor instance."""
    return BitcoinPaymentProcessor()
