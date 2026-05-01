"""Locust load test for BYOS AI Backend."""
from locust import HttpUser, task, between
import os

API_KEY = os.getenv("BYOS_API_KEY", "")


class BYOSUser(HttpUser):
    """Simulate BYOS API user load."""
    
    wait_time = between(0.1, 0.5)

    def on_start(self):
        """Set up headers before each user session starts."""
        if not API_KEY:
            raise RuntimeError("Set BYOS_API_KEY=byos_... before running Locust")
        self.client.headers = {
            "X-API-Key": API_KEY,
            "Content-Type": "application/json",
        }

    @task(3)
    def exec_request(self):
        """Main AI execution endpoint - highest frequency."""
        payload = {
            "workspace_id": "dev",
            "conversation_id": "load-test",
            "prompt": "Ping from Locust – simple test prompt.",
        }
        self.client.post("/v1/exec", json=payload)

    @task(1)
    def health_check(self):
        """Health endpoint - lower frequency."""
        self.client.get("/health")

    @task(1)
    def get_status(self):
        """Status endpoint with provider info."""
        self.client.get("/status")
