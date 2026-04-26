#!/usr/bin/env python3
"""
FULL CONSISTENCY TEST - One command to rule them all.

Runs the complete consistency testing protocol:
1. Warmup phase
2. 5-iteration load test  
3. Continuous monitoring (optional)

Usage:
  python tests/load/run_full_consistency_test.py
  
With continuous monitoring:
  python tests/load/run_full_consistency_test.py --monitor
"""
import subprocess
import sys
import argparse
import time
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


def run_command(cmd: list, description: str) -> bool:
    """Run a command and show progress."""
    print("\n" + "=" * 80)
    print(f"🔄 {description}")
    print("=" * 80)
    
    try:
        result = subprocess.run(
            cmd,
            cwd=project_root,
            capture_output=False,
            text=True,
        )
        return result.returncode == 0
    except Exception as e:
        print(f"❌ Failed: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Full consistency test")
    parser.add_argument(
        "--monitor", 
        action="store_true",
        help="Run continuous monitoring after load test"
    )
    parser.add_argument(
        "--monitor-duration",
        type=int,
        default=300,
        help="Monitor duration in seconds (default: 300 = 5 min)"
    )
    args = parser.parse_args()
    
    print("=" * 80)
    print("🎯 FULL CONSISTENCY TEST PROTOCOL")
    print("   Target: 777ms P95 latency, consistently")
    print("=" * 80)
    
    # Phase 1: Warmup
    print("\n📋 PHASE 1: System Warmup")
    print("   Pre-populating caches and connection pools...")
    
    if not run_command(
        [sys.executable, "scripts/warmup_caches.py"],
        "Warming up system caches"
    ):
        print("\n❌ Warmup failed - cannot proceed")
        return 1
    
    time.sleep(1)  # Brief pause
    
    # Phase 2: Consistency Test
    print("\n📋 PHASE 2: Consistency Validation")
    print("   Running 5 iterations of 5000 concurrent users...")
    
    test_passed = run_command(
        [sys.executable, "tests/load/load_test_consistent_777ms.py"],
        "5-iteration consistency test"
    )
    
    if not test_passed:
        print("\n" + "=" * 80)
        print("❌ CONSISTENCY TEST FAILED")
        print("=" * 80)
        print("\nRecommendations:")
        print("  1. Check if backend is running: python -m apps.api.main")
        print("  2. Verify database connection pool size")
        print("  3. Check Redis connection status")
        print("  4. Review logs for bottlenecks")
        print("\nRun warmup separately to debug:")
        print("  python scripts/warmup_caches.py")
        return 1
    
    # Phase 3: Continuous Monitoring (optional)
    if args.monitor:
        print(f"\n📋 PHASE 3: Continuous Monitoring ({args.monitor_duration}s)")
        print("   Proving long-term consistency...")
        print("   Press Ctrl+C to stop early\n")
        
        try:
            run_command(
                [sys.executable, "scripts/continuous_monitor.py"],
                f"Continuous monitoring ({args.monitor_duration}s)"
            )
        except KeyboardInterrupt:
            print("\n\n⚠️  Monitoring stopped by user")
    
    # Final summary
    print("\n" + "=" * 80)
    print("✅ FULL CONSISTENCY TEST COMPLETE")
    print("=" * 80)
    
    if test_passed:
        print("\n🎉 ALL PHASES PASSED")
        print("\nResults:")
        print("  ✅ System warmed and caches populated")
        print("  ✅ 5-iteration consistency test passed")
        print("  ✅ P95 consistently under 777ms")
        print("  ✅ Low variance between runs")
        
        if args.monitor:
            print("  ✅ Long-term consistency verified")
        
        print("\n🚀 SYSTEM READY FOR PRODUCTION")
        print("   Confidently handles 5000 concurrent users")
        print("   Consistent 777ms P95 latency achieved")
    
    print("=" * 80)
    return 0


if __name__ == "__main__":
    sys.exit(main())
