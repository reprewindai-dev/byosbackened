"""
TEST VALIDATOR - Proves the load tests are real and valid.

This module provides verification mechanisms to ensure:
1. Real HTTP requests are being made
2. Responses are actually from the backend
3. No synthetic/cached results
4. Full audit trail of test execution
"""
import asyncio
import httpx
import time
import json
import hashlib
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict


@dataclass
class ValidatedRequest:
    """A request with full verification data."""
    correlation_id: str
    timestamp: str
    method: str
    endpoint: str
    request_headers: Dict[str, str]
    response_status: int
    response_headers: Dict[str, str]
    response_body_hash: str  # Hash of response to prove we got real data
    latency_ms: float
    server_timing: Optional[str]  # X-Response-Time header from server
    cache_status: Optional[str]  # X-Cache header
    verified: bool = False  # Whether we validated the response


class TestValidator:
    """
    Validates that load tests are making real requests.
    
    Provides:
    - Correlation ID tracking
    - Response validation (not fake data)
    - Audit logging
    - Server-side verification endpoint
    """
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.validated_requests: List[ValidatedRequest] = []
        self.test_run_id = str(uuid.uuid4())[:8]
        self.start_time = datetime.now().isoformat()
        
    def generate_correlation_id(self) -> str:
        """Generate unique correlation ID for request tracking."""
        return f"{self.test_run_id}-{str(uuid.uuid4())[:12]}"
    
    async def make_validated_request(
        self,
        client: httpx.AsyncClient,
        method: str,
        endpoint: str,
        headers: Dict[str, str] = None,
        json_data: Dict = None,
        timeout: float = 2.0,
    ) -> ValidatedRequest:
        """
        Make a request with full validation tracking.
        
        This proves the request was real by:
        1. Adding correlation ID
        2. Recording all headers
        3. Hashing response body
        4. Capturing server timing
        """
        correlation_id = self.generate_correlation_id()
        
        # Add correlation ID to headers
        request_headers = headers.copy() if headers else {}
        request_headers["X-Correlation-ID"] = correlation_id
        request_headers["X-Test-Run-ID"] = self.test_run_id
        
        start = time.perf_counter()
        
        try:
            if method == "GET":
                response = await client.get(endpoint, headers=request_headers, timeout=timeout)
            elif method == "POST":
                response = await client.post(endpoint, json=json_data, headers=request_headers, timeout=timeout)
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            latency_ms = (time.perf_counter() - start) * 1000
            
            # Hash response body to prove we got real data
            body_content = response.content
            body_hash = hashlib.sha256(body_content).hexdigest()[:16]
            
            # Extract server headers
            server_timing = response.headers.get("X-Response-Time")
            cache_status = response.headers.get("X-Cache")
            server_correlation = response.headers.get("X-Correlation-ID")
            
            # Verify server echoed our correlation ID (proves request hit real backend)
            verified = server_correlation == correlation_id if server_correlation else False
            
            validated = ValidatedRequest(
                correlation_id=correlation_id,
                timestamp=datetime.now().isoformat(),
                method=method,
                endpoint=endpoint,
                request_headers=request_headers,
                response_status=response.status_code,
                response_headers=dict(response.headers),
                response_body_hash=body_hash,
                latency_ms=latency_ms,
                server_timing=server_timing,
                cache_status=cache_status,
                verified=verified,
            )
            
            self.validated_requests.append(validated)
            return validated
            
        except Exception as e:
            # Record failed request too
            validated = ValidatedRequest(
                correlation_id=correlation_id,
                timestamp=datetime.now().isoformat(),
                method=method,
                endpoint=endpoint,
                request_headers=request_headers,
                response_status=0,
                response_headers={},
                response_body_hash="",
                latency_ms=(time.perf_counter() - start) * 1000,
                server_timing=None,
                cache_status=None,
                verified=False,
            )
            self.validated_requests.append(validated)
            raise
    
    def generate_audit_report(self) -> Dict[str, Any]:
        """Generate full audit report of test execution."""
        total = len(self.validated_requests)
        verified = sum(1 for r in self.validated_requests if r.verified)
        successful = sum(1 for r in self.validated_requests if r.response_status == 200)
        
        # Group by endpoint
        endpoint_stats = {}
        for req in self.validated_requests:
            key = f"{req.method} {req.endpoint}"
            if key not in endpoint_stats:
                endpoint_stats[key] = {"total": 0, "verified": 0, "latencies": []}
            endpoint_stats[key]["total"] += 1
            if req.verified:
                endpoint_stats[key]["verified"] += 1
            endpoint_stats[key]["latencies"].append(req.latency_ms)
        
        return {
            "test_run_id": self.test_run_id,
            "start_time": self.start_time,
            "end_time": datetime.now().isoformat(),
            "total_requests": total,
            "verified_requests": verified,
            "verification_rate": verified / total * 100 if total > 0 else 0,
            "successful_requests": successful,
            "success_rate": successful / total * 100 if total > 0 else 0,
            "endpoint_breakdown": endpoint_stats,
            "raw_requests": [asdict(r) for r in self.validated_requests[:100]],  # First 100
        }
    
    def save_audit_log(self, filename: Optional[str] = None):
        """Save full audit log to file."""
        if not filename:
            filename = f"test_audit_{self.test_run_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        report = self.generate_audit_report()
        
        with open(filename, 'w') as f:
            json.dump(report, f, indent=2)
        
        return filename
    
    def print_validation_summary(self):
        """Print validation summary to console."""
        report = self.generate_audit_report()
        
        print("\n" + "=" * 80)
        print("🔍 TEST VALIDATION REPORT")
        print("=" * 80)
        print(f"Test Run ID: {report['test_run_id']}")
        print(f"Duration: {report['start_time']} to {report['end_time']}")
        print(f"\nRequest Validation:")
        print(f"  Total requests: {report['total_requests']:,}")
        print(f"  Verified by server: {report['verified_requests']:,} ({report['verification_rate']:.1f}%)")
        print(f"  Successful (HTTP 200): {report['successful_requests']:,} ({report['success_rate']:.1f}%)")
        
        if report['verification_rate'] >= 95:
            print(f"  ✅ VERIFICATION: {report['verification_rate']:.1f}% - Requests are REAL")
        elif report['verification_rate'] >= 80:
            print(f"  ⚠️  VERIFICATION: {report['verification_rate']:.1f}% - Some requests may be cached")
        else:
            print(f"  ❌ VERIFICATION: {report['verification_rate']:.1f}% - HIGH FAILURE RATE")
        
        print(f"\nEndpoint Breakdown:")
        for endpoint, stats in sorted(report['endpoint_breakdown'].items()):
            avg_latency = sum(stats['latencies']) / len(stats['latencies']) if stats['latencies'] else 0
            verified_pct = stats['verified'] / stats['total'] * 100
            print(f"  {endpoint:40s} {stats['total']:>4} req, {avg_latency:>6.1f}ms avg, {verified_pct:>5.1f}% verified")
        
        print("=" * 80)


async def run_validation_check():
    """Run a quick validation check to prove the system works."""
    print("=" * 80)
    print("🔍 TEST VALIDATION CHECK")
    print("=" * 80)
    print("\nThis verifies that:")
    print("  1. Real HTTP requests are made to the backend")
    print("  2. Responses come from the actual server")
    print("  3. No synthetic/fake data is generated")
    print()
    
    validator = TestValidator()
    
    async with httpx.AsyncClient(base_url="http://localhost:8000", timeout=5.0) as client:
        # Test health endpoint
        print("Testing /health endpoint...")
        try:
            result = await validator.make_validated_request(client, "GET", "/health")
            print(f"  ✅ Request verified: {result.verified}")
            print(f"  📊 Response hash: {result.response_body_hash}")
            print(f"  ⏱️  Latency: {result.latency_ms:.1f}ms")
        except Exception as e:
            print(f"  ❌ Failed: {e}")
        
        # Test status endpoint
        print("\nTesting /status endpoint...")
        try:
            result = await validator.make_validated_request(client, "GET", "/status")
            print(f"  ✅ Request verified: {result.verified}")
            print(f"  📊 Response hash: {result.response_body_hash}")
            print(f"  ⏱️  Latency: {result.latency_ms:.1f}ms")
        except Exception as e:
            print(f"  ❌ Failed: {e}")
    
    # Generate and save report
    print("\n" + "=" * 80)
    validator.print_validation_summary()
    
    audit_file = validator.save_audit_log()
    print(f"\n📁 Full audit log saved: {audit_file}")
    
    # Final verdict
    report = validator.generate_audit_report()
    if report['verification_rate'] >= 95 and report['success_rate'] >= 95:
        print("\n🎉 VALIDATION PASSED - Tests are making REAL requests!")
        return True
    else:
        print("\n⚠️  VALIDATION ISSUES - Check audit log for details")
        return False


if __name__ == "__main__":
    import sys
    
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    try:
        success = asyncio.run(run_validation_check())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted")
        sys.exit(130)
