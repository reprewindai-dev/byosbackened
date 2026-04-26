"""
Continuous performance monitoring - prove consistency over time.

Runs continuous light load and logs metrics to prove the system
maintains 777ms P95 consistently, not just in bursts.
"""
import asyncio
import httpx
import time
import statistics
import json
import signal
import sys
from datetime import datetime, timedelta
from collections import deque
from typing import Deque, Dict

# Configuration
BASE_URL = "http://localhost:8000"
CHECK_INTERVAL = 5  # Seconds between checks
WINDOW_SIZE = 60    # Keep last 60 samples for rolling stats

# Target metrics
TARGET_P95 = 777
TARGET_P50 = 600
MIN_SUCCESS_RATE = 95


class ContinuousMonitor:
    """Continuous performance monitor."""
    
    def __init__(self):
        self.running = True
        self.latencies: Deque[float] = deque(maxlen=WINDOW_SIZE)
        self.errors = 0
        self.total = 0
        self.start_time = time.time()
        
        # History for trend analysis
        self.history: Deque[Dict] = deque(maxlen=100)  # Last 100 check points
        
    def signal_handler(self, sig, frame):
        """Handle shutdown gracefully."""
        print("\n\n🛑 Shutting down monitor...")
        self.running = False
        
    async def check_health(self, client: httpx.AsyncClient) -> tuple:
        """Check endpoint health and latency."""
        try:
            start = time.perf_counter()
            resp = await client.get("/health", timeout=2.0)
            latency = (time.perf_counter() - start) * 1000
            
            success = resp.status_code == 200
            return success, latency, None
            
        except Exception as e:
            return False, 0, str(e)
    
    def calculate_stats(self) -> Dict:
        """Calculate statistics from recent samples."""
        if not self.latencies:
            return {}
        
        sorted_lat = sorted(self.latencies)
        n = len(sorted_lat)
        
        return {
            "p50": sorted_lat[int(n * 0.50)],
            "p95": sorted_lat[int(n * 0.95)] if n >= 20 else sorted_lat[-1],
            "p99": sorted_lat[int(n * 0.99)] if n >= 100 else sorted_lat[-1],
            "mean": statistics.mean(sorted_lat),
            "min": min(sorted_lat),
            "max": max(sorted_lat),
            "std_dev": statistics.stdev(sorted_lat) if n > 1 else 0,
            "samples": n,
            "success_rate": (self.total - self.errors) / self.total * 100 if self.total > 0 else 0,
        }
    
    def check_targets(self, stats: Dict) -> Dict[str, bool]:
        """Check if metrics meet targets."""
        if not stats:
            return {}
        
        return {
            "p95_ok": stats["p95"] <= TARGET_P95,
            "p50_ok": stats["p50"] <= TARGET_P50,
            "success_ok": stats["success_rate"] >= MIN_SUCCESS_RATE,
            "variance_ok": (stats["std_dev"] / stats["mean"] * 100) < 15 if stats["mean"] > 0 else False,
        }
    
    def get_status_emoji(self, checks: Dict) -> str:
        """Get status emoji based on checks."""
        if all(checks.values()):
            return "✅"
        elif checks.get("p95_ok") and checks.get("success_ok"):
            return "⚠️ "
        else:
            return "❌"
    
    def print_header(self):
        """Print table header."""
        print("\n" + "=" * 100)
        print(f"{'Time':^12} | {'P50':^8} | {'P95':^8} | {'P99':^8} | {'Success':^8} | {'Status':^6} | {'Trend':^20}")
        print("─" * 100)
    
    def print_stats(self, stats: Dict, checks: Dict):
        """Print current statistics."""
        if not stats:
            return
        
        now = datetime.now().strftime("%H:%M:%S")
        status = self.get_status_emoji(checks)
        
        # Calculate trend
        trend = ""
        if len(self.history) >= 2:
            prev = list(self.history)[-2]
            if prev.get("p95"):
                diff = stats["p95"] - prev["p95"]
                if abs(diff) < 10:
                    trend = "→ stable"
                elif diff < 0:
                    trend = f"↓ improving ({abs(diff):.0f}ms)"
                else:
                    trend = f"↑ degrading (+{diff:.0f}ms)"
        
        print(
            f"{now:^12} | "
            f"{stats['p50']:>6.1f}ms | "
            f"{stats['p95']:>6.1f}ms | "
            f"{stats['p99']:>6.1f}ms | "
            f"{stats['success_rate']:>6.1f}% | "
            f"{status:^6} | "
            f"{trend:<20}"
        )
    
    async def run(self):
        """Run continuous monitoring."""
        signal.signal(signal.SIGINT, self.signal_handler)
        
        print("=" * 100)
        print("📊 CONTINUOUS PERFORMANCE MONITOR")
        print(f"Target: P95 <= {TARGET_P95}ms, P50 <= {TARGET_P50}ms, Success >= {MIN_SUCCESS_RATE}%")
        print(f"Sample window: {WINDOW_SIZE} requests ({WINDOW_SIZE * CHECK_INTERVAL // 60} minutes rolling)")
        print("=" * 100)
        
        iteration = 0
        
        async with httpx.AsyncClient(base_url=BASE_URL, timeout=2.0) as client:
            while self.running:
                success, latency, error = await self.check_health(client)
                
                self.total += 1
                if success:
                    self.latencies.append(latency)
                else:
                    self.errors += 1
                
                # Print stats every CHECK_INTERVAL seconds
                if iteration % CHECK_INTERVAL == 0 and self.latencies:
                    stats = self.calculate_stats()
                    checks = self.check_targets(stats)
                    
                    # Store history
                    self.history.append(stats)
                    
                    # Print header periodically
                    if len(self.history) % 20 == 1:
                        self.print_header()
                    
                    self.print_stats(stats, checks)
                    
                    # Alert on degradation
                    if not checks.get("p95_ok") and stats.get("p95", 0) > TARGET_P95 * 1.2:
                        print(f"⚠️  ALERT: P95 degraded to {stats['p95']:.1f}ms!")
                    
                    if not checks.get("success_ok"):
                        print(f"❌ ALERT: Success rate dropped to {stats['success_rate']:.1f}%!")
                
                iteration += 1
                await asyncio.sleep(1)
        
        # Final report
        self.print_final_report()
    
    def print_final_report(self):
        """Print final consistency report."""
        print("\n" + "=" * 100)
        print("📈 FINAL CONSISTENCY REPORT")
        print("=" * 100)
        
        duration = time.time() - self.start_time
        print(f"\nDuration: {duration / 60:.1f} minutes")
        print(f"Total checks: {self.total}")
        print(f"Errors: {self.errors}")
        
        if len(self.history) > 0:
            all_p95s = [h["p95"] for h in self.history if "p95" in h]
            all_p50s = [h["p50"] for h in self.history if "p50" in h]
            all_success = [h["success_rate"] for h in self.history if "success_rate" in h]
            
            if all_p95s:
                print(f"\nP95 Latency Statistics:")
                print(f"  Min: {min(all_p95s):.1f}ms")
                print(f"  Max: {max(all_p95s):.1f}ms")
                print(f"  Mean: {statistics.mean(all_p95s):.1f}ms")
                print(f"  Std Dev: {statistics.stdev(all_p95s):.1f}ms" if len(all_p95s) > 1 else "  Std Dev: N/A")
                print(f"  Times under {TARGET_P95}ms: {sum(1 for p in all_p95s if p <= TARGET_P95)}/{len(all_p95s)}")
            
            if all_success:
                print(f"\nSuccess Rate Statistics:")
                print(f"  Min: {min(all_success):.1f}%")
                print(f"  Mean: {statistics.mean(all_success):.1f}%")
        
        # Consistency grade
        if all_p95s:
            p95_variance = statistics.stdev(all_p95s) / statistics.mean(all_p95s) * 100
            under_target_pct = sum(1 for p in all_p95s if p <= TARGET_P95) / len(all_p95s) * 100
            
            print(f"\n🎯 CONSISTENCY GRADE:")
            if under_target_pct >= 95 and p95_variance < 10:
                print("  A+ - EXCELLENT: Consistently under target with low variance")
            elif under_target_pct >= 90 and p95_variance < 15:
                print("  A - GOOD: Mostly under target, acceptable variance")
            elif under_target_pct >= 80:
                print("  B - ACCEPTABLE: Usually under target, some spikes")
            else:
                print("  C - NEEDS WORK: Frequent over-target latencies")
            
            print(f"  ({under_target_pct:.1f}% under target, {p95_variance:.1f}% variance)")
        
        print("=" * 100)
        
        # Save results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"continuous_monitor_{timestamp}.json"
        with open(filename, 'w') as f:
            json.dump({
                "duration_seconds": duration,
                "target_p95": TARGET_P95,
                "target_p50": TARGET_P50,
                "history": list(self.history),
            }, f, indent=2, default=str)
        print(f"\n📁 Results saved: {filename}")


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    monitor = ContinuousMonitor()
    
    try:
        asyncio.run(monitor.run())
    except Exception as e:
        print(f"\n❌ Monitor error: {e}")
        sys.exit(1)
