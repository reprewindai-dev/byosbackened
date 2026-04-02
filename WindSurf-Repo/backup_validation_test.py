"""
Backup and Restore Validation Suite
=================================

Tests backup integrity, restoration speed, and data consistency.
"""

import asyncio
import time
import logging
import subprocess
import tempfile
import os
from typing import Dict, List, Any
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from datetime import datetime

logger = logging.getLogger(__name__)

class BackupValidationTest:
    """Backup and restore testing suite."""
    
    def __init__(self):
        self.test_db_url = "sqlite:///./test_backup.db"
        self.backup_dir = tempfile.mkdtemp()
        self.test_results = {}
    
    async def create_test_data(self) -> Dict[str, Any]:
        """Create test data for backup validation."""
        logger.info("📝 Creating test data...")
        
        engine = create_engine(self.test_db_url)
        Session = sessionmaker(bind=engine)
        
        # Create test tables
        with engine.connect() as conn:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS test_users (
                    id INTEGER PRIMARY KEY,
                    email TEXT UNIQUE,
                    created_at TIMESTAMP,
                    data JSON
                )
            """))
            
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS test_workspaces (
                    id INTEGER PRIMARY KEY,
                    name TEXT,
                    user_id INTEGER,
                    created_at TIMESTAMP
                )
            """))
            
            conn.commit()
        
        # Insert test data
        session = Session()
        try:
            # Insert test users
            users_data = []
            for i in range(100):
                user_data = {
                    "id": i + 1,
                    "email": f"testuser{i}@example.com",
                    "created_at": datetime.utcnow(),
                    "data": {"role": "user", "active": True}
                }
                users_data.append(user_data)
            
            for user in users_data:
                session.execute(text("""
                    INSERT INTO test_users (id, email, created_at, data)
                    VALUES (:id, :email, :created_at, :data)
                """), user)
            
            # Insert test workspaces
            workspaces_data = []
            for i in range(50):
                workspace_data = {
                    "id": i + 1,
                    "name": f"Test Workspace {i}",
                    "user_id": (i % 100) + 1,
                    "created_at": datetime.utcnow()
                }
                workspaces_data.append(workspace_data)
            
            for workspace in workspaces_data:
                session.execute(text("""
                    INSERT INTO test_workspaces (id, name, user_id, created_at)
                    VALUES (:id, :name, :user_id, :created_at)
                """), workspace)
            
            session.commit()
            
            return {
                "users_count": len(users_data),
                "workspaces_count": len(workspaces_data),
                "created_at": datetime.utcnow()
            }
            
        finally:
            session.close()
    
    async def create_backup(self) -> Dict[str, Any]:
        """Create database backup."""
        logger.info("💾 Creating database backup...")
        
        backup_file = os.path.join(self.backup_dir, f"backup_{int(time.time())}.sql")
        
        try:
            # For SQLite
            if "sqlite" in self.test_db_url:
                # Use SQLite backup command
                result = subprocess.run([
                    "sqlite3", "./test_backup.db", 
                    f".backup {backup_file}"
                ], capture_output=True, text=True)
                
                if result.returncode == 0:
                    backup_size = os.path.getsize(backup_file)
                    return {
                        "success": True,
                        "backup_file": backup_file,
                        "backup_size": backup_size,
                        "created_at": datetime.utcnow()
                    }
                else:
                    return {
                        "success": False,
                        "error": result.stderr
                    }
            
            # For PostgreSQL (if applicable)
            elif "postgresql" in self.test_db_url:
                # Use pg_dump
                result = subprocess.run([
                    "pg_dump", self.test_db_url,
                    "--file", backup_file,
                    "--verbose"
                ], capture_output=True, text=True)
                
                if result.returncode == 0:
                    backup_size = os.path.getsize(backup_file)
                    return {
                        "success": True,
                        "backup_file": backup_file,
                        "backup_size": backup_size,
                        "created_at": datetime.utcnow()
                    }
                else:
                    return {
                        "success": False,
                        "error": result.stderr
                    }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def restore_backup(self, backup_file: str) -> Dict[str, Any]:
        """Restore database from backup."""
        logger.info("🔄 Restoring database from backup...")
        
        restore_start = time.time()
        
        try:
            # Create new database for restore
            restore_db_url = "sqlite:///./test_restore.db"
            
            # For SQLite
            if "sqlite" in self.test_db_url:
                # Copy backup file to restore location
                restore_file = "./test_restore.db"
                
                result = subprocess.run([
                    "sqlite3", restore_file,
                    f".restore {backup_file}"
                ], capture_output=True, text=True)
                
                restore_time = time.time() - restore_start
                
                if result.returncode == 0:
                    return {
                        "success": True,
                        "restore_time": restore_time,
                        "restore_file": restore_file,
                        "restored_at": datetime.utcnow()
                    }
                else:
                    return {
                        "success": False,
                        "error": result.stderr,
                        "restore_time": restore_time
                    }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "restore_time": time.time() - restore_start
            }
    
    async def validate_data_integrity(self, original_data: Dict, restore_file: str) -> Dict[str, Any]:
        """Validate data integrity after restore."""
        logger.info("🔍 Validating data integrity...")
        
        try:
            # Connect to restored database
            engine = create_engine(f"sqlite:///{restore_file}")
            Session = sessionmaker(bind=engine)
            session = Session()
            
            # Count users
            users_result = session.execute(text("SELECT COUNT(*) FROM test_users"))
            users_count = users_result.scalar()
            
            # Count workspaces
            workspaces_result = session.execute(text("SELECT COUNT(*) FROM test_workspaces"))
            workspaces_count = workspaces_result.scalar()
            
            # Sample data validation
            sample_users = session.execute(text("""
                SELECT email, created_at FROM test_users LIMIT 5
            """)).fetchall()
            
            sample_workspaces = session.execute(text("""
                SELECT name, user_id FROM test_workspaces LIMIT 5
            """)).fetchall()
            
            session.close()
            
            # Compare with original data
            users_match = users_count == original_data["users_count"]
            workspaces_match = workspaces_count == original_data["workspaces_count"]
            
            return {
                "users_count": users_count,
                "workspaces_count": workspaces_count,
                "original_users": original_data["users_count"],
                "original_workspaces": original_data["workspaces_count"],
                "users_match": users_match,
                "workspaces_match": workspaces_match,
                "data_integrity": users_match and workspaces_match,
                "sample_data": {
                    "users": [{"email": row[0], "created_at": str(row[1])} for row in sample_users],
                    "workspaces": [{"name": row[0], "user_id": row[1]} for row in sample_workspaces]
                }
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def measure_backup_performance(self) -> Dict[str, Any]:
        """Measure backup and restore performance."""
        logger.info("⏱️ Measuring backup performance...")
        
        # Create test data
        original_data = await self.create_test_data()
        
        # Measure backup performance
        backup_start = time.time()
        backup_result = await self.create_backup()
        backup_time = time.time() - backup_start
        
        if not backup_result["success"]:
            return {
                "success": False,
                "error": "Backup failed",
                "backup_error": backup_result.get("error")
            }
        
        # Measure restore performance
        restore_result = await self.restore_backup(backup_result["backup_file"])
        
        if not restore_result["success"]:
            return {
                "success": False,
                "error": "Restore failed",
                "restore_error": restore_result.get("error")
            }
        
        # Validate data integrity
        integrity_result = await self.validate_data_integrity(
            original_data, 
            restore_result["restore_file"]
        )
        
        # Calculate RTO/RPO
        rto = restore_result["restore_time"]  # Recovery Time Objective
        rpo = backup_time  # Recovery Point Objective (time since last backup)
        
        return {
            "success": True,
            "original_data": original_data,
            "backup": {
                "time": backup_time,
                "size": backup_result["backup_size"],
                "file": backup_result["backup_file"]
            },
            "restore": {
                "time": restore_result["restore_time"],
                "file": restore_result["restore_file"]
            },
            "integrity": integrity_result,
            "metrics": {
                "rto_seconds": rto,
                "rpo_seconds": rpo,
                "backup_throughput_mb_s": (backup_result["backup_size"] / (1024*1024)) / backup_time if backup_time > 0 else 0,
                "restore_throughput_mb_s": (backup_result["backup_size"] / (1024*1024)) / restore_result["restore_time"] if restore_result["restore_time"] > 0 else 0
            }
        }
    
    async def test_concurrent_backups(self) -> Dict[str, Any]:
        """Test concurrent backup operations."""
        logger.info("🔄 Testing concurrent backups...")
        
        # Create test data
        await self.create_test_data()
        
        # Start multiple backup operations
        backup_tasks = []
        for i in range(3):
            task = asyncio.create_task(self.create_backup())
            backup_tasks.append(task)
        
        # Wait for all backups to complete
        backup_results = await asyncio.gather(*backup_tasks, return_exceptions=True)
        
        successful_backups = [r for r in backup_results if isinstance(r, dict) and r.get("success")]
        failed_backups = [r for r in backup_results if not (isinstance(r, dict) and r.get("success"))]
        
        return {
            "total_backups": len(backup_tasks),
            "successful": len(successful_backups),
            "failed": len(failed_backups),
            "success_rate": (len(successful_backups) / len(backup_tasks)) * 100,
            "results": backup_results
        }
    
    async def run_complete_test(self) -> Dict[str, Any]:
        """Run complete backup validation test."""
        logger.info("🚀 Starting Backup Validation Test Suite")
        
        results = {
            "test_type": "backup_validation",
            "timestamp": datetime.utcnow().isoformat(),
            "performance": await self.measure_backup_performance(),
            "concurrent": await self.test_concurrent_backups(),
            "summary": {}
        }
        
        # Generate summary
        performance = results["performance"]
        if performance["success"]:
            integrity = performance["integrity"]["data_integrity"]
            rto = performance["metrics"]["rto_seconds"]
            rpo = performance["metrics"]["rpo_seconds"]
            
            results["summary"] = {
                "backup_valid": True,
                "restore_valid": True,
                "data_integrity": integrity,
                "rto_acceptable": rto < 60,  # Under 1 minute
                "rpo_acceptable": rpo < 300,  # Under 5 minutes
                "overall_score": self.calculate_backup_score(performance, results["concurrent"])
            }
        else:
            results["summary"] = {
                "backup_valid": False,
                "restore_valid": False,
                "data_integrity": False,
                "overall_score": 0
            }
        
        return results
    
    def calculate_backup_score(self, performance: Dict, concurrent: Dict) -> int:
        """Calculate backup system score (0-100)."""
        score = 100
        
        # Data integrity (40 points)
        if not performance.get("integrity", {}).get("data_integrity", False):
            score -= 40
        
        # RTO performance (20 points)
        rto = performance.get("metrics", {}).get("rto_seconds", 999)
        if rto > 60:  # Over 1 minute
            score -= 20
        elif rto > 30:  # Over 30 seconds
            score -= 10
        
        # RPO performance (20 points)
        rpo = performance.get("metrics", {}).get("rpo_seconds", 999)
        if rpo > 300:  # Over 5 minutes
            score -= 20
        elif rpo > 60:  # Over 1 minute
            score -= 10
        
        # Concurrent backup success (20 points)
        success_rate = concurrent.get("success_rate", 0)
        if success_rate < 80:
            score -= 20
        elif success_rate < 95:
            score -= 10
        
        return max(0, score)
    
    def cleanup(self):
        """Clean up test files."""
        try:
            import shutil
            shutil.rmtree(self.backup_dir)
            
            # Remove test databases
            for db_file in ["./test_backup.db", "./test_restore.db"]:
                if os.path.exists(db_file):
                    os.remove(db_file)
        except Exception as e:
            logger.warning(f"Cleanup failed: {e}")

async def main():
    """Run backup validation test."""
    test = BackupValidationTest()
    
    try:
        results = await test.run_complete_test()
        
        print("\n" + "="*60)
        print("💾 BACKUP VALIDATION TEST RESULTS")
        print("="*60)
        
        summary = results["summary"]
        print(f"📊 Overall Score: {summary['overall_score']}/100")
        print(f"✅ Backup Valid: {summary['backup_valid']}")
        print(f"✅ Restore Valid: {summary['restore_valid']}")
        print(f"✅ Data Integrity: {summary['data_integrity']}")
        print(f"⏱️ RTO Acceptable: {summary['rto_acceptable']}")
        print(f"⏱️ RPO Acceptable: {summary['rpo_acceptable']}")
        
        if summary["overall_score"] >= 90:
            print("🎉 Backup system is excellent")
        elif summary["overall_score"] >= 70:
            print("✅ Backup system is good")
        elif summary["overall_score"] >= 50:
            print("⚠️ Backup system needs improvements")
        else:
            print("❌ Backup system has serious issues")
        
        if results["performance"]["success"]:
            perf = results["performance"]["metrics"]
            print(f"\n📈 Performance Metrics:")
            print(f"   RTO: {perf['rto_seconds']:.1f}s")
            print(f"   RPO: {perf['rpo_seconds']:.1f}s")
            print(f"   Backup Throughput: {perf['backup_throughput_mb_s']:.2f} MB/s")
            print(f"   Restore Throughput: {perf['restore_throughput_mb_s']:.2f} MB/s")
        
        print("="*60)
        
    finally:
        test.cleanup()

if __name__ == "__main__":
    asyncio.run(main())
