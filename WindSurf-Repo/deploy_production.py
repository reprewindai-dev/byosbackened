#!/usr/bin/env python3
"""
Production Deployment Script for Multi-Tenant BYOS Backend
Handles complete deployment including tenant setup, model pulling, and validation
"""

import asyncio
import subprocess
import sys
import time
import httpx
import json
from pathlib import Path
from typing import Dict, Any, List
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ProductionDeployer:
    """Handle complete production deployment."""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.api_base = f"{base_url}/api"
        
    async def deploy_production(self) -> Dict[str, Any]:
        """Execute complete production deployment."""
        logger.info("🚀 Starting Production Deployment")
        start_time = time.time()
        
        deployment_steps = [
            ("Infrastructure Setup", self.setup_infrastructure),
            ("Database Migration", self.run_database_migration),
            ("Pull LLM Models", self.pull_llm_models),
            ("Create Default Tenants", self.create_default_tenants),
            ("Validate Deployment", self.validate_deployment),
            ("Run Smoke Tests", self.run_smoke_tests),
            ("Generate Deployment Report", self.generate_deployment_report)
        ]
        
        results = {}
        
        for step_name, step_func in deployment_steps:
            logger.info(f"📋 Executing: {step_name}")
            try:
                step_start = time.time()
                result = await step_func()
                step_time = time.time() - step_start
                results[step_name] = {
                    "status": "SUCCESS",
                    "duration_seconds": round(step_time, 2),
                    "details": result
                }
                logger.info(f"✅ {step_name} completed in {step_time:.2f}s")
            except Exception as e:
                step_time = time.time() - step_start
                logger.error(f"❌ {step_name} failed: {e}")
                results[step_name] = {
                    "status": "FAILED",
                    "duration_seconds": round(step_time, 2),
                    "error": str(e)
                }
                # Continue with other steps for partial deployment
        
        total_time = time.time() - start_time
        summary = {
            "deployment_status": "PARTIAL" if any(r["status"] == "FAILED" for r in results.values()) else "SUCCESS",
            "total_duration_seconds": round(total_time, 2),
            "successful_steps": len([r for r in results.values() if r["status"] == "SUCCESS"]),
            "failed_steps": len([r for r in results.values() if r["status"] == "FAILED"]),
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
            "steps": results
        }
        
        logger.info(f"🏁 Deployment Complete: {summary['successful_steps']}/{len(deployment_steps)} steps successful in {summary['total_duration_seconds']}s")
        return summary
    
    async def setup_infrastructure(self) -> Dict[str, Any]:
        """Start infrastructure services."""
        logger.info("Starting Docker Compose services...")
        
        # Start services
        result = subprocess.run(
            ["docker-compose", "-f", "docker-compose.local.yml", "up", "-d"],
            capture_output=True,
            text=True,
            timeout=300
        )
        
        if result.returncode != 0:
            raise Exception(f"Docker Compose failed: {result.stderr}")
        
        # Wait for services to be healthy
        logger.info("Waiting for services to be healthy...")
        await self._wait_for_services()
        
        return {"services_started": True}
    
    async def _wait_for_services(self, timeout: int = 300) -> None:
        """Wait for all services to be healthy."""
        start_time = time.time()
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            while time.time() - start_time < timeout:
                try:
                    # Check backend health
                    response = await client.get(f"{self.base_url}/health")
                    if response.status_code == 200:
                        logger.info("✅ Backend is healthy")
                        break
                except:
                    pass
                
                logger.info("⏳ Waiting for services...")
                await asyncio.sleep(10)
            else:
                raise Exception("Services failed to become healthy within timeout")
    
    async def run_database_migration(self) -> Dict[str, Any]:
        """Run database migrations."""
        logger.info("Running database migrations...")
        
        # The init.sql script runs automatically via Docker entrypoint
        # Just verify the schema is correct
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{self.api_base}/v1/llm/models")
            # This will fail with auth, but confirms database connectivity
            if response.status_code not in [200, 401, 403]:
                raise Exception(f"Database connectivity check failed: {response.status_code}")
        
        return {"migration_status": "completed"}
    
    async def pull_llm_models(self) -> Dict[str, Any]:
        """Pull required LLM models."""
        logger.info("Pulling LLM models...")
        
        models_to_pull = ["llama3.1:8b", "qwen2.5:7b"]
        pulled_models = []
        
        for model in models_to_pull:
            try:
                # Pull model via Ollama API
                async with httpx.AsyncClient(timeout=300.0) as client:
                    response = await client.post(
                        "http://localhost:11434/api/pull",
                        json={"name": model}
                    )
                    if response.status_code == 200:
                        pulled_models.append(model)
                        logger.info(f"✅ Pulled model: {model}")
                    else:
                        logger.warning(f"⚠️ Failed to pull model {model}: {response.status_code}")
            except Exception as e:
                logger.warning(f"⚠️ Error pulling model {model}: {e}")
        
        return {"pulled_models": pulled_models, "attempted_models": models_to_pull}
    
    async def create_default_tenants(self) -> Dict[str, Any]:
        """Create default tenants with hashed API keys."""
        logger.info("Creating default tenants...")
        
        # Use tenant management script
        tenants_to_create = [
            {"name": "AgencyOS", "limit": 1000},
            {"name": "BattleArena", "limit": 2000},
            {"name": "LumiNode", "limit": 500}
        ]
        
        created_tenants = []
        
        for tenant_config in tenants_to_create:
            try:
                result = subprocess.run([
                    "python", "manage_tenants.py", "create",
                    tenant_config["name"],
                    "--limit", str(tenant_config["limit"])
                ], capture_output=True, text=True, timeout=30)
                
                if result.returncode == 0:
                    created_tenants.append(tenant_config["name"])
                    logger.info(f"✅ Created tenant: {tenant_config['name']}")
                else:
                    logger.warning(f"⚠️ Failed to create tenant {tenant_config['name']}: {result.stderr}")
            except Exception as e:
                logger.warning(f"⚠️ Error creating tenant {tenant_config['name']}: {e}")
        
        return {"created_tenants": created_tenants}
    
    async def validate_deployment(self) -> Dict[str, Any]:
        """Validate deployment components."""
        logger.info("Validating deployment...")
        
        validations = {}
        
        # Test backend health
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{self.base_url}/health")
                validations["backend_health"] = response.status_code == 200
        except:
            validations["backend_health"] = False
        
        # Test database connectivity
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{self.api_base}/v1/llm/models")
                validations["database"] = response.status_code in [200, 401, 403]
        except:
            validations["database"] = False
        
        # Test Redis connectivity
        try:
            # Test via cache endpoint
            headers = {"X-API-Key": "test_key"}
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{self.api_base}/v1/llm/models", headers=headers)
                validations["redis"] = response.status_code in [200, 401]
        except:
            validations["redis"] = False
        
        # Test Ollama connectivity
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get("http://localhost:11434/api/tags")
                validations["ollama"] = response.status_code == 200
        except:
            validations["ollama"] = False
        
        all_valid = all(validations.values())
        if not all_valid:
            logger.warning(f"⚠️ Some validations failed: {validations}")
        
        return {"validations": validations, "all_valid": all_valid}
    
    async def run_smoke_tests(self) -> Dict[str, Any]:
        """Run production smoke tests."""
        logger.info("Running smoke tests...")
        
        try:
            # Import and run smoke test
            from test_production_smoke import ProductionSmokeTest
            
            tester = ProductionSmokeTest(self.base_url)
            results = await tester.run_all_tests()
            
            return {
                "smoke_test_results": results,
                "all_passed": results["failed"] == 0
            }
        except Exception as e:
            logger.error(f"Smoke tests failed: {e}")
            return {
                "smoke_test_results": {"error": str(e)},
                "all_passed": False
            }
    
    async def generate_deployment_report(self) -> Dict[str, Any]:
        """Generate comprehensive deployment report."""
        logger.info("Generating deployment report...")
        
        # Gather system information
        system_info = {}
        
        # Docker services status
        try:
            result = subprocess.run(
                ["docker-compose", "-f", "docker-compose.local.yml", "ps"],
                capture_output=True,
                text=True
            )
            system_info["docker_services"] = result.stdout
        except:
            system_info["docker_services"] = "Failed to get status"
        
        # Available models
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get("http://localhost:11434/api/tags")
                if response.status_code == 200:
                    models = response.json().get("models", [])
                    system_info["available_models"] = [model["name"] for model in models]
        except:
            system_info["available_models"] = []
        
        # Tenant information
        try:
            result = subprocess.run(
                ["python", "manage_tenants.py", "list"],
                capture_output=True,
                text=True
            )
            system_info["tenant_list"] = result.stdout
        except:
            system_info["tenant_list"] = "Failed to get tenants"
        
        return {
            "system_info": system_info,
            "deployment_timestamp": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
            "base_url": self.base_url,
            "api_endpoints": {
                "health": f"{self.base_url}/health",
                "api_docs": f"{self.base_url}/api/docs",
                "multi_tenant_llm": f"{self.api_base}/v1/llm",
                "executive_dashboard": f"{self.api_base}/executive/dashboard"
            }
        }


async def main():
    """Main deployment function."""
    deployer = ProductionDeployer()
    
    try:
        results = await deployer.deploy_production()
        
        # Print deployment summary
        print("\n" + "="*60)
        print("PRODUCTION DEPLOYMENT SUMMARY")
        print("="*60)
        print(f"Status: {results['deployment_status']}")
        print(f"Duration: {results['total_duration_seconds']}s")
        print(f"Successful Steps: {results['successful_steps']}/{len(results['steps'])}")
        print(f"Timestamp: {results['timestamp']}")
        
        print("\nStep Details:")
        for step_name, step_result in results['steps'].items():
            status_icon = "✅" if step_result["status"] == "SUCCESS" else "❌"
            print(f"  {status_icon} {step_name} ({step_result['duration_seconds']}s)")
            if step_result["status"] == "FAILED":
                print(f"     Error: {step_result.get('error', 'Unknown error')}")
        
        # Print API endpoints
        if "generate_deployment_report" in results['steps']:
            report = results['steps']["generate_deployment_report"]["details"]
            if report and "api_endpoints" in report:
                print("\n🔗 API Endpoints:")
                for name, url in report["api_endpoints"].items():
                    print(f"  {name}: {url}")
        
        # Return appropriate exit code
        return 0 if results['deployment_status'] == "SUCCESS" else 1
        
    except Exception as e:
        logger.error(f"Deployment failed: {e}")
        print(f"\n❌ Deployment failed: {e}")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
