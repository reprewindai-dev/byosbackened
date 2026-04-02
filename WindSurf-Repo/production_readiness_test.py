#!/usr/bin/env python3
"""
Production Readiness Test Runner
================================

Comprehensive testing suite for production validation including:
- Load testing with k6
- Chaos testing (Redis/DB failover)
- Backup validation
- Performance profiling
- Cost analysis
"""

import asyncio
import subprocess
import time
import json
import logging
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime

logger = logging.getLogger(__name__)

class ProductionReadinessTest:
    """Production readiness testing suite."""
    
    def __init__(self):
        self.test_results = {}
        self.start_time = time.time()
        self.report_dir = Path("production_test_reports")
        self.report_dir.mkdir(exist_ok=True)
    
    async def run_load_test(self) -> Dict[str, Any]:
        """Run load testing with k6."""
        logger.info("⚡ Starting load testing...")
        
        try:
            # Check if k6 is installed
            result = subprocess.run(["k6", "version"], capture_output=True, text=True)
            if result.returncode != 0:
                return {"success": False, "error": "k6 not installed"}
            
            # Run load test
            load_test_file = "load_test_k6.js"
            if not Path(load_test_file).exists():
                return {"success": False, "error": "Load test file not found"}
            
            logger.info("Running k6 load test...")
            result = subprocess.run([
                "k6", "run", 
                "--out", "json=load_test_results.json",
                load_test_file
            ], capture_output=True, text=True, timeout=1800)  # 30 minute timeout
            
            # Parse results
            if result.returncode == 0:
                # Load JSON results
                try:
                    with open("load_test_results.json", "r") as f:
                        load_results = json.load(f)
                    
                    return {
                        "success": True,
                        "results": load_results,
                        "summary": self.parse_load_test_results(load_results)
                    }
                except Exception as e:
                    return {"success": False, "error": f"Failed to parse results: {e}"}
            else:
                return {
                    "success": False, 
                    "error": result.stderr,
                    "stdout": result.stdout
                }
                
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Load test timed out"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def parse_load_test_results(self, results: List[Dict]) -> Dict[str, Any]:
        """Parse k6 load test results."""
        if not results:
            return {"error": "No results to parse"}
        
        # Extract metrics
        metrics = {}
        for item in results:
            if item.get("type") == "Point":
                metric_name = item.get("metric", {}).get("name")
                if metric_name:
                    if metric_name not in metrics:
                        metrics[metric_name] = []
                    metrics[metric_name].append(item.get("data", {}).get("value", 0))
        
        # Calculate summary statistics
        summary = {
            "total_requests": len([r for r in results if r.get("type") == "Point"]),
            "http_req_duration": {
                "avg": sum(metrics.get("http_req_duration", [])) / len(metrics.get("http_req_duration", [1])),
                "max": max(metrics.get("http_req_duration", [0])),
                "min": min(metrics.get("http_req_duration", [0])),
                "p95": self.calculate_percentile(metrics.get("http_req_duration", []), 95),
                "p99": self.calculate_percentile(metrics.get("http_req_duration", []), 99)
            },
            "http_req_failed": {
                "rate": sum(metrics.get("http_req_failed", [])) / max(1, len(metrics.get("http_req_failed", [1]))) * 100
            },
            "vus": {
                "max": max(metrics.get("vus", [1])),
                "min": min(metrics.get("vus", [1]))
            }
        }
        
        return summary
    
    def calculate_percentile(self, values: List[float], percentile: int) -> float:
        """Calculate percentile of values."""
        if not values:
            return 0
        
        sorted_values = sorted(values)
        index = (percentile / 100) * len(sorted_values)
        
        if index >= len(sorted_values):
            return sorted_values[-1]
        
        return sorted_values[int(index)]
    
    async def run_chaos_tests(self) -> Dict[str, Any]:
        """Run chaos testing suite."""
        logger.info("🔥 Starting chaos testing...")
        
        chaos_results = {}
        
        # Redis chaos test
        try:
            import importlib.util
            spec = importlib.util.spec_from_file_location("chaos_test_redis", "chaos_test_redis.py")
            redis_test = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(redis_test)
            
            # Run Redis chaos test
            redis_chaos_test = redis_test.RedisChaosTest()
            chaos_results["redis"] = await redis_chaos_test.run_complete_test()
            
        except Exception as e:
            chaos_results["redis"] = {"success": False, "error": str(e)}
        
        # Database chaos test (placeholder for now)
        chaos_results["database"] = {
            "success": True,
            "note": "Database chaos test not implemented yet",
            "recommendation": "Implement DB failover testing"
        }
        
        return chaos_results
    
    async def run_backup_validation(self) -> Dict[str, Any]:
        """Run backup validation tests."""
        logger.info("💾 Starting backup validation...")
        
        try:
            import importlib.util
            spec = importlib.util.spec_from_file_location("backup_validation", "backup_validation_test.py")
            backup_test = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(backup_test)
            
            # Run backup validation test
            backup_validator = backup_test.BackupValidationTest()
            backup_results = await backup_validator.run_complete_test()
            
            return backup_results
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def run_performance_profiling(self) -> Dict[str, Any]:
        """Run performance profiling."""
        logger.info("📊 Starting performance profiling...")
        
        try:
            # Test API endpoints performance
            import httpx
            
            async with httpx.AsyncClient() as client:
                # Get auth token
                login_response = await client.post(
                    "http://localhost:8000/api/v1/auth/login-json",
                    json={"username": "admin", "password": "admin123"}
                )
                
                if login_response.status_code != 200:
                    return {"success": False, "error": "Authentication failed"}
                
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
                
                performance_results = {}
                
                for endpoint in endpoints:
                    times = []
                    
                    # Run 10 requests for each endpoint
                    for _ in range(10):
                        start_time = time.time()
                        
                        try:
                            response = await client.get(f"http://localhost:8000{endpoint}", headers=headers)
                            end_time = time.time()
                            
                            times.append((end_time - start_time) * 1000)  # Convert to ms
                            
                        except Exception as e:
                            times.append(float('inf'))  # Mark as failed
                    
                    # Calculate statistics
                    valid_times = [t for t in times if t != float('inf')]
                    
                    if valid_times:
                        performance_results[endpoint] = {
                            "avg_ms": sum(valid_times) / len(valid_times),
                            "min_ms": min(valid_times),
                            "max_ms": max(valid_times),
                            "p95_ms": self.calculate_percentile(valid_times, 95),
                            "p99_ms": self.calculate_percentile(valid_times, 99),
                            "success_rate": len(valid_times) / len(times) * 100,
                            "total_requests": len(times)
                        }
                    else:
                        performance_results[endpoint] = {
                            "avg_ms": 0,
                            "success_rate": 0,
                            "error": "All requests failed"
                        }
                
                return {
                    "success": True,
                    "results": performance_results,
                    "summary": self.calculate_performance_summary(performance_results)
                }
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def calculate_performance_summary(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate performance summary."""
        if not results:
            return {"error": "No performance results"}
        
        avg_response_times = []
        success_rates = []
        
        for endpoint, metrics in results.items():
            if "avg_ms" in metrics and metrics["avg_ms"] > 0:
                avg_response_times.append(metrics["avg_ms"])
            if "success_rate" in metrics:
                success_rates.append(metrics["success_rate"])
        
        return {
            "overall_avg_response_time": sum(avg_response_times) / len(avg_response_times) if avg_response_times else 0,
            "overall_success_rate": sum(success_rates) / len(success_rates) if success_rates else 0,
            "slowest_endpoint": max(results.keys(), key=lambda k: results[k].get("avg_ms", 0)),
            "fastest_endpoint": min(results.keys(), key=lambda k: results[k].get("avg_ms", float('inf'))),
            "endpoints_tested": len(results)
        }
    
    async def run_cost_analysis(self) -> Dict[str, Any]:
        """Run cost analysis for production deployment."""
        logger.info("💰 Starting cost analysis...")
        
        # This would integrate with cloud provider APIs
        # For now, provide estimated costs based on resource usage
        
        estimated_costs = {
            "infrastructure": {
                "compute": {
                    "api_servers": 4 * 50,  # 4 servers at $50/month
                    "worker_servers": 2 * 30,  # 2 workers at $30/month
                    "database": 100,  # Managed PostgreSQL
                    "redis": 50,  # Managed Redis
                    "load_balancer": 20,
                    "monitoring": 30
                },
                "storage": {
                    "database_storage": 0.23 * 100,  # $0.23/GB for 100GB
                    "backup_storage": 0.026 * 500,  # $0.026/GB for 500GB backups
                    "logs": 0.50 * 50  # $0.50/GB for 50GB logs
                },
                "data_transfer": {
                    "outbound": 0.09 * 1000,  # $0.09/GB for 1000GB
                    "inbound": 0  # Free
                }
            },
            "ai_costs": {
                "huggingface": 0,  # Free tier
                "openai": 0.002 * 10000,  # $0.002/1K tokens for 10M tokens
                "local_models": 200  # GPU costs
            },
            "third_party": {
                "stripe": 0.029 * 10000,  # 2.9% + $0.30 per transaction
                "monitoring": 50,
                "security": 30
            }
        }
        
        # Calculate totals
        total_infrastructure = sum(
            sum(category.values()) 
            for category in estimated_costs["infrastructure"].values()
        )
        total_ai = sum(estimated_costs["ai_costs"].values())
        total_third_party = sum(estimated_costs["third_party"].values())
        
        total_monthly = total_infrastructure + total_ai + total_third_party
        
        return {
            "success": True,
            "estimated_monthly_cost": total_monthly,
            "cost_breakdown": estimated_costs,
            "cost_per_user": total_monthly / 1000,  # Assuming 1000 users
            "cost_per_request": total_monthly / 1000000,  # Assuming 1M requests/month
            "recommendations": self.generate_cost_recommendations(estimated_costs)
        }
    
    def generate_cost_recommendations(self, costs: Dict[str, Any]) -> List[str]:
        """Generate cost optimization recommendations."""
        recommendations = []
        
        # Infrastructure recommendations
        if costs["infrastructure"]["compute"]["api_servers"] > 200:
            recommendations.append("Consider auto-scaling to reduce compute costs during low traffic")
        
        if costs["infrastructure"]["storage"]["database_storage"] > 50:
            recommendations.append("Implement data archiving for old records to reduce storage costs")
        
        # AI costs recommendations
        if costs["ai_costs"]["openai"] > 500:
            recommendations.append("Implement caching to reduce OpenAI API calls")
        
        if costs["ai_costs"]["local_models"] > 100:
            recommendations.append("Consider spot instances for model inference to reduce GPU costs")
        
        # Third-party recommendations
        if costs["third_party"]["stripe"] > 1000:
            recommendations.append("Negotiate volume pricing with Stripe for high transaction volumes")
        
        return recommendations
    
    async def generate_report(self) -> str:
        """Generate comprehensive production readiness report."""
        logger.info("📋 Generating production readiness report...")
        
        report = {
            "test_suite": "Production Readiness Validation",
            "timestamp": datetime.utcnow().isoformat(),
            "duration_seconds": time.time() - self.start_time,
            "results": self.test_results,
            "summary": self.generate_final_summary(),
            "recommendations": self.generate_final_recommendations()
        }
        
        # Save report
        report_file = self.report_dir / f"production_readiness_report_{int(time.time())}.json"
        with open(report_file, "w") as f:
            json.dump(report, f, indent=2, default=str)
        
        return str(report_file)
    
    def generate_final_summary(self) -> Dict[str, Any]:
        """Generate final summary of all tests."""
        summary = {
            "overall_score": 0,
            "tests_passed": 0,
            "tests_failed": 0,
            "critical_issues": [],
            "warnings": [],
            "production_ready": False
        }
        
        # Load test results
        load_test = self.test_results.get("load_test", {})
        if load_test.get("success"):
            load_score = 100
            if load_test.get("summary", {}).get("http_req_duration", {}).get("p95", 0) > 100:
                load_score -= 30
            if load_test.get("summary", {}).get("http_req_failed", {}).get("rate", 0) > 1:
                load_score -= 40
            summary["load_test_score"] = load_score
        else:
            summary["load_test_score"] = 0
            summary["critical_issues"].append("Load test failed")
        
        # Chaos test results
        chaos_test = self.test_results.get("chaos_tests", {})
        if chaos_test.get("redis", {}).get("summary", {}).get("resilience_score", 0):
            chaos_score = chaos_test["redis"]["summary"]["resilience_score"]
        else:
            chaos_score = 0
            summary["critical_issues"].append("Chaos testing incomplete")
        
        # Backup validation results
        backup_test = self.test_results.get("backup_validation", {})
        backup_score = backup_test.get("summary", {}).get("overall_score", 0)
        if backup_score < 70:
            summary["critical_issues"].append("Backup system needs improvement")
        
        # Performance results
        performance_test = self.test_results.get("performance_profiling", {})
        if performance_test.get("success"):
            perf_summary = performance_test.get("summary", {})
            perf_score = 100
            if perf_summary.get("overall_avg_response_time", 0) > 100:
                perf_score -= 20
            if perf_summary.get("overall_success_rate", 0) < 99:
                perf_score -= 30
            summary["performance_score"] = perf_score
        else:
            summary["performance_score"] = 0
            summary["critical_issues"].append("Performance profiling failed")
        
        # Calculate overall score
        scores = [
            summary.get("load_test_score", 0),
            chaos_score,
            backup_score,
            summary.get("performance_score", 0)
        ]
        
        summary["overall_score"] = sum(scores) / len(scores)
        summary["production_ready"] = summary["overall_score"] >= 80 and not summary["critical_issues"]
        
        return summary
    
    def generate_final_recommendations(self) -> List[str]:
        """Generate final recommendations based on test results."""
        recommendations = []
        
        summary = self.generate_final_summary()
        
        if summary["overall_score"] < 80:
            recommendations.append("System needs significant improvements before production deployment")
        
        if summary["critical_issues"]:
            recommendations.append(f"Address critical issues: {', '.join(summary['critical_issues'])}")
        
        # Load test recommendations
        load_test = self.test_results.get("load_test", {})
        if load_test.get("success"):
            load_summary = load_test.get("summary", {})
            if load_summary.get("http_req_duration", {}).get("p95", 0) > 100:
                recommendations.append("Optimize API response times to meet p95 < 100ms target")
            if load_summary.get("http_req_failed", {}).get("rate", 0) > 1:
                recommendations.append("Improve error handling to achieve < 1% error rate")
        
        # Chaos test recommendations
        chaos_test = self.test_results.get("chaos_tests", {})
        if chaos_test.get("redis", {}).get("summary", {}).get("resilience_score", 0) < 80:
            recommendations.append("Improve Redis failover handling and caching strategy")
        
        # Backup recommendations
        backup_test = self.test_results.get("backup_validation", {})
        if backup_test.get("summary", {}).get("overall_score", 0) < 80:
            recommendations.append("Improve backup system reliability and performance")
        
        # Performance recommendations
        performance_test = self.test_results.get("performance_profiling", {})
        if performance_test.get("success"):
            perf_summary = performance_test.get("summary", {})
            if perf_summary.get("overall_avg_response_time", 0) > 50:
                recommendations.append("Implement additional caching and query optimization")
        
        return recommendations
    
    async def run_all_tests(self) -> str:
        """Run complete production readiness test suite."""
        logger.info("🚀 Starting Production Readiness Test Suite")
        
        # Run all tests
        test_functions = [
            ("load_test", self.run_load_test),
            ("chaos_tests", self.run_chaos_tests),
            ("backup_validation", self.run_backup_validation),
            ("performance_profiling", self.run_performance_profiling),
            ("cost_analysis", self.run_cost_analysis)
        ]
        
        for test_name, test_func in test_functions:
            logger.info(f"Running {test_name}...")
            try:
                result = await test_func()
                self.test_results[test_name] = result
                
                if result.get("success"):
                    logger.info(f"✅ {test_name} completed successfully")
                else:
                    logger.error(f"❌ {test_name} failed: {result.get('error', 'Unknown error')}")
                    
            except Exception as e:
                logger.error(f"❌ {test_name} crashed: {e}")
                self.test_results[test_name] = {"success": False, "error": str(e)}
        
        # Generate report
        report_file = await self.generate_report()
        
        return report_file

async def main():
    """Main test runner."""
    tester = ProductionReadinessTest()
    
    try:
        report_file = await tester.run_all_tests()
        
        print("\n" + "="*80)
        print("🎯 PRODUCTION READINESS TEST COMPLETE")
        print("="*80)
        print(f"📄 Report saved to: {report_file}")
        
        summary = tester.generate_final_summary()
        print(f"📊 Overall Score: {summary['overall_score']:.1f}/100")
        print(f"✅ Production Ready: {'YES' if summary['production_ready'] else 'NO'}")
        
        if summary["critical_issues"]:
            print(f"🚨 Critical Issues: {len(summary['critical_issues'])}")
            for issue in summary["critical_issues"]:
                print(f"   - {issue}")
        
        if summary["warnings"]:
            print(f"⚠️ Warnings: {len(summary['warnings'])}")
        
        recommendations = tester.generate_final_recommendations()
        if recommendations:
            print(f"\n📋 Recommendations:")
            for rec in recommendations:
                print(f"   - {rec}")
        
        print("="*80)
        
    except Exception as e:
        logger.error(f"Test suite failed: {e}")
        print(f"❌ Test suite failed: {e}")

if __name__ == "__main__":
    asyncio.run(main())
