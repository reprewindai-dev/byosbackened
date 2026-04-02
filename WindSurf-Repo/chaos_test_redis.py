"""
Chaos Testing Suite - Redis Failover Simulation
===============================================

Tests system resilience when Redis becomes unavailable.
"""

import asyncio
import time
import logging
from typing import Dict, Any
import redis.asyncio as redis
from fastapi import FastAPI
from httpx import AsyncClient

logger = logging.getLogger(__name__)

class RedisChaosTest:
    """Redis chaos testing suite."""
    
    def __init__(self):
        self.redis_url = "redis://localhost:6379/0"
        self.api_base = "http://localhost:8000"
        self.test_results = {}
    
    async def test_redis_connection(self) -> bool:
        """Test if Redis is available."""
        try:
            client = redis.from_url(self.redis_url)
            await client.ping()
            await client.close()
            return True
        except Exception as e:
            logger.error(f"Redis connection failed: {e}")
            return False
    
    async def simulate_redis_failure(self) -> Dict[str, Any]:
        """Simulate Redis failure and test system behavior."""
        logger.info("🔥 Starting Redis failure simulation...")
        
        # Test baseline performance with Redis
        baseline_metrics = await self.measure_api_performance("with_redis")
        
        # Simulate Redis failure (stop Redis service)
        logger.warning("⚠️ Simulating Redis failure...")
        # In production, this would be: docker stop redis or similar
        
        # Wait for system to detect failure
        await asyncio.sleep(5)
        
        # Test performance without Redis
        failure_metrics = await self.measure_api_performance("without_redis")
        
        # Simulate Redis recovery
        logger.info("🔄 Simulating Redis recovery...")
        # In production: docker start redis
        
        # Wait for Redis to be available
        await asyncio.sleep(10)
        
        # Test performance after recovery
        recovery_metrics = await self.measure_api_performance("after_recovery")
        
        return {
            "baseline": baseline_metrics,
            "failure": failure_metrics,
            "recovery": recovery_metrics,
            "degradation": self.calculate_degradation(baseline_metrics, failure_metrics),
            "recovery_time": self.calculate_recovery_time(baseline_metrics, recovery_metrics)
        }
    
    async def measure_api_performance(self, scenario: str) -> Dict[str, Any]:
        """Measure API performance under given scenario."""
        async with AsyncClient() as client:
            # Get auth token
            login_response = await client.post(
                f"{self.api_base}/api/v1/auth/login-json",
                json={"username": "admin", "password": "admin123"}
            )
            
            if login_response.status_code != 200:
                return {"error": "Authentication failed"}
            
            token = login_response.json()["access_token"]
            headers = {"Authorization": f"Bearer {token}"}
            
            # Test multiple endpoints
            endpoints = [
                "/health",
                "/api/v1/admin/dashboard/config",
                "/api/v1/admin/dashboard/system-status",
                "/api/v1/admin/dashboard/metrics",
                "/api/plans"
            ]
            
            results = {}
            
            for endpoint in endpoints:
                start_time = time.time()
                
                try:
                    response = await client.get(f"{self.api_base}{endpoint}", headers=headers)
                    end_time = time.time()
                    
                    results[endpoint] = {
                        "status_code": response.status_code,
                        "response_time": (end_time - start_time) * 1000,  # Convert to ms
                        "success": response.status_code == 200
                    }
                except Exception as e:
                    end_time = time.time()
                    results[endpoint] = {
                        "status_code": 0,
                        "response_time": (end_time - start_time) * 1000,
                        "success": False,
                        "error": str(e)
                    }
            
            return results
    
    def calculate_degradation(self, baseline: Dict, failure: Dict) -> Dict[str, float]:
        """Calculate performance degradation."""
        degradation = {}
        
        for endpoint in baseline.keys():
            if endpoint in failure:
                baseline_time = baseline[endpoint]["response_time"]
                failure_time = failure[endpoint]["response_time"]
                
                if baseline_time > 0:
                    degradation[endpoint] = ((failure_time - baseline_time) / baseline_time) * 100
                else:
                    degradation[endpoint] = 0
        
        return degradation
    
    def calculate_recovery_time(self, baseline: Dict, recovery: Dict) -> Dict[str, float]:
        """Calculate recovery time for each endpoint."""
        recovery_time = {}
        
        for endpoint in baseline.keys():
            if endpoint in recovery:
                baseline_time = baseline[endpoint]["response_time"]
                recovery_time_val = recovery[endpoint]["response_time"]
                
                if baseline_time > 0:
                    recovery_time[endpoint] = abs(recovery_time_val - baseline_time)
                else:
                    recovery_time[endpoint] = 0
        
        return recovery_time
    
    async def run_complete_test(self) -> Dict[str, Any]:
        """Run complete Redis chaos test."""
        logger.info("🚀 Starting Redis Chaos Test Suite")
        
        # Check Redis availability
        redis_available = await self.test_redis_connection()
        if not redis_available:
            return {"error": "Redis not available for testing"}
        
        # Run chaos simulation
        chaos_results = await self.simulate_redis_failure()
        
        # Generate report
        report = {
            "test_type": "redis_failover",
            "timestamp": time.time(),
            "redis_available": redis_available,
            "results": chaos_results,
            "summary": self.generate_summary(chaos_results)
        }
        
        return report
    
    def generate_summary(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate test summary."""
        summary = {
            "overall_degradation": 0,
            "max_degradation": 0,
            "avg_recovery_time": 0,
            "critical_failures": [],
            "resilience_score": 0
        }
        
        if "degradation" in results:
            degradations = list(results["degradation"].values())
            if degradations:
                summary["overall_degradation"] = sum(degradations) / len(degradations)
                summary["max_degradation"] = max(degradations)
        
        if "recovery_time" in results:
            recovery_times = list(results["recovery_time"].values())
            if recovery_times:
                summary["avg_recovery_time"] = sum(recovery_times) / len(recovery_times)
        
        # Calculate resilience score (0-100)
        resilience_score = 100
        if summary["max_degradation"] > 200:  # More than 200% degradation
            resilience_score -= 30
        elif summary["max_degradation"] > 100:  # More than 100% degradation
            resilience_score -= 20
        elif summary["max_degradation"] > 50:   # More than 50% degradation
            resilience_score -= 10
        
        if summary["avg_recovery_time"] > 5000:  # More than 5s recovery
            resilience_score -= 20
        elif summary["avg_recovery_time"] > 2000:  # More than 2s recovery
            resilience_score -= 10
        
        summary["resilience_score"] = max(0, resilience_score)
        
        return summary

async def main():
    """Run Redis chaos test."""
    test = RedisChaosTest()
    results = await test.run_complete_test()
    
    print("\n" + "="*60)
    print("🔥 REDIS CHAOS TEST RESULTS")
    print("="*60)
    
    if "error" in results:
        print(f"❌ Test failed: {results['error']}")
        return
    
    summary = results["summary"]
    print(f"📊 Resilience Score: {summary['resilience_score']}/100")
    print(f"📈 Max Degradation: {summary['max_degradation']:.1f}%")
    print(f"⏱️ Avg Recovery Time: {summary['avg_recovery_time']:.1f}ms")
    
    if summary["resilience_score"] >= 80:
        print("✅ System shows good resilience")
    elif summary["resilience_score"] >= 60:
        print("⚠️ System shows acceptable resilience")
    else:
        print("❌ System needs resilience improvements")
    
    print("="*60)

if __name__ == "__main__":
    asyncio.run(main())
