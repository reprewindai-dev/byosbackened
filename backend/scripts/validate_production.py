#!/usr/bin/env python3
"""
Production Deployment Validation Script

Validates BYOS backend is production-ready by checking:
1. Environment variables (secrets, keys)
2. Database connectivity & migrations
3. Redis connectivity
4. Ollama LLM connectivity
5. Security configuration
6. Middleware stack
7. API endpoints
8. TLS/SSL configuration (if applicable)

Run: python scripts/validate_production.py
"""

import os
import sys
import json
import socket
import ssl
import hashlib
import subprocess
from datetime import datetime
from typing import Dict, List, Tuple, Optional
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import httpx
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError


# ═══════════════════════════════════════════════════════════════════════════════
# Validation Results
# ═══════════════════════════════════════════════════════════════════════════════

class ValidationResult:
    """Stores validation check result."""
    
    def __init__(self, name: str, passed: bool, message: str, details: Optional[Dict] = None):
        self.name = name
        self.passed = passed
        self.message = message
        self.details = details or {}
        self.timestamp = datetime.utcnow()
    
    def __repr__(self):
        status = "✅ PASS" if self.passed else "❌ FAIL"
        return f"[{status}] {self.name}: {self.message}"


class ProductionValidator:
    """Validates production deployment configuration."""
    
    def __init__(self):
        self.results: List[ValidationResult] = []
        self.errors: List[str] = []
        self.warnings: List[str] = []
        
        # Load environment
        self.env = dict(os.environ)
    
    def run_all_checks(self) -> Tuple[bool, List[ValidationResult]]:
        """Run all validation checks."""
        print("🔍 Starting Production Deployment Validation\n")
        
        checks = [
            self.check_environment_variables,
            self.check_database_connectivity,
            self.check_redis_connectivity,
            self.check_ollama_connectivity,
            self.check_security_configuration,
            self.check_middleware_configuration,
            self.check_api_endpoints,
            self.check_file_permissions,
        ]
        
        for check in checks:
            try:
                check()
            except Exception as e:
                self.results.append(ValidationResult(
                    name=check.__name__,
                    passed=False,
                    message=f"Check failed with exception: {str(e)}",
                ))
        
        return self._is_valid(), self.results
    
    def _is_valid(self) -> bool:
        """Check if all critical checks passed."""
        critical_checks = [r for r in self.results if not r.passed]
        return len(critical_checks) == 0
    
    # ═══════════════════════════════════════════════════════════════════════════
    # Check 1: Environment Variables
    # ═══════════════════════════════════════════════════════════════════════════
    
    def check_environment_variables(self):
        """Validate required environment variables."""
        print("📋 Checking Environment Variables...")
        
        required_vars = [
            ("SECRET_KEY", "JWT signing key", True),
            ("ENCRYPTION_KEY", "Field encryption key", True),
            ("DATABASE_URL", "Database connection", True),
            ("REDIS_URL", "Redis connection", True),
        ]
        
        optional_vars = [
            ("GROQ_API_KEY", "Groq fallback API key", False),
            ("STRIPE_SECRET_KEY", "Stripe payment processing", False),
            ("SENTRY_DSN", "Sentry error tracking", False),
        ]
        
        issues = []
        
        for var_name, description, required in required_vars:
            value = self.env.get(var_name)
            
            if not value:
                if required:
                    issues.append(f"Missing required: {var_name} ({description})")
                continue
            
            # Check for default/placeholder values
            if value in ["change-me", "placeholder", "", "default"]:
                issues.append(f"{var_name} uses default/placeholder value")
            
            # Check key strength
            if var_name in ["SECRET_KEY", "ENCRYPTION_KEY"] and len(value) < 32:
                issues.append(f"{var_name} is too short (should be 32+ chars)")
        
        # Check for production-specific settings
        debug = self.env.get("DEBUG", "false").lower()
        if debug == "true":
            self.warnings.append("DEBUG is set to 'true' - should be 'false' in production")
        
        passed = len([i for i in issues if "Missing required" in i]) == 0
        
        self.results.append(ValidationResult(
            name="Environment Variables",
            passed=passed,
            message=f"Found {len(issues)} issues" if issues else "All required variables present",
            details={"issues": issues, "warnings": self.warnings},
        ))
    
    # ═══════════════════════════════════════════════════════════════════════════
    # Check 2: Database Connectivity
    # ═══════════════════════════════════════════════════════════════════════════
    
    def check_database_connectivity(self):
        """Validate database connection."""
        print("🗄️  Checking Database Connectivity...")
        
        database_url = self.env.get("DATABASE_URL")
        if not database_url:
            self.results.append(ValidationResult(
                name="Database Connectivity",
                passed=False,
                message="DATABASE_URL not set",
            ))
            return
        
        try:
            engine = create_engine(database_url, connect_args={"connect_timeout": 5})
            
            with engine.connect() as conn:
                # Test basic query
                result = conn.execute(text("SELECT 1"))
                assert result.scalar() == 1
                
                # Check migrations
                result = conn.execute(text(
                    "SELECT COUNT(*) FROM alembic_version"
                ))
                version_count = result.scalar()
                
                # Check if tables exist
                result = conn.execute(text(
                    "SELECT COUNT(*) FROM information_schema.tables "
                    "WHERE table_schema = 'public'"
                ))
                table_count = result.scalar()
            
            self.results.append(ValidationResult(
                name="Database Connectivity",
                passed=True,
                message=f"Connected successfully. {table_count} tables found, {version_count} migration versions.",
                details={"tables": table_count, "migrations": version_count},
            ))
            
        except OperationalError as e:
            self.results.append(ValidationResult(
                name="Database Connectivity",
                passed=False,
                message=f"Cannot connect to database: {str(e)}",
            ))
        except Exception as e:
            self.results.append(ValidationResult(
                name="Database Connectivity",
                passed=False,
                message=f"Database check failed: {str(e)}",
            ))
    
    # ═══════════════════════════════════════════════════════════════════════════
    # Check 3: Redis Connectivity
    # ═══════════════════════════════════════════════════════════════════════════
    
    def check_redis_connectivity(self):
        """Validate Redis connection."""
        print("🔴 Checking Redis Connectivity...")
        
        redis_url = self.env.get("REDIS_URL", "redis://localhost:6379/0")
        
        try:
            import redis as redis_lib
            
            r = redis_lib.from_url(redis_url, socket_connect_timeout=5, decode_responses=True)
            
            if r.ping():
                # Test write/read
                test_key = "production_validation_test"
                r.set(test_key, "ok", ex=10)
                value = r.get(test_key)
                
                if value == "ok":
                    self.results.append(ValidationResult(
                        name="Redis Connectivity",
                        passed=True,
                        message="Redis connected and operational",
                        details={"url": redis_url.replace("//", "//***@")},  # Hide credentials
                    ))
                else:
                    self.results.append(ValidationResult(
                        name="Redis Connectivity",
                        passed=False,
                        message="Redis ping succeeded but read/write failed",
                    ))
            else:
                self.results.append(ValidationResult(
                    name="Redis Connectivity",
                    passed=False,
                    message="Redis ping failed",
                ))
                
        except ImportError:
            self.results.append(ValidationResult(
                name="Redis Connectivity",
                passed=False,
                message="Redis Python library not installed",
            ))
        except Exception as e:
            self.results.append(ValidationResult(
                name="Redis Connectivity",
                passed=False,
                message=f"Redis connection failed: {str(e)}",
            ))
    
    # ═══════════════════════════════════════════════════════════════════════════
    # Check 4: Ollama LLM Connectivity
    # ═══════════════════════════════════════════════════════════════════════════
    
    def check_ollama_connectivity(self):
        """Validate Ollama LLM connection."""
        print("🤖 Checking Ollama LLM Connectivity...")
        
        ollama_url = self.env.get("LLM_BASE_URL", "http://localhost:11434")
        default_model = self.env.get("LLM_MODEL_DEFAULT", "qwen2.5:3b")
        
        try:
            # Check if Ollama is reachable
            response = httpx.get(f"{ollama_url}/api/tags", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                models = [m.get("name") for m in data.get("models", [])]
                
                # Check if default model is available
                has_default = any(default_model in m for m in models)
                
                if has_default:
                    self.results.append(ValidationResult(
                        name="Ollama LLM Connectivity",
                        passed=True,
                        message=f"Ollama connected. Default model '{default_model}' available. {len(models)} models total.",
                        details={"models": models[:5]},  # First 5 models
                    ))
                else:
                    self.results.append(ValidationResult(
                        name="Ollama LLM Connectivity",
                        passed=True,  # Still pass, but warn
                        message=f"Ollama connected but default model '{default_model}' not found. Available: {models[:3]}",
                        details={"available_models": models},
                    ))
                    self.warnings.append(f"Default model '{default_model}' not found in Ollama")
            else:
                self.results.append(ValidationResult(
                    name="Ollama LLM Connectivity",
                    passed=False,
                    message=f"Ollama returned status {response.status_code}",
                ))
                
        except httpx.ConnectError:
            self.results.append(ValidationResult(
                name="Ollama LLM Connectivity",
                passed=False,
                message=f"Cannot connect to Ollama at {ollama_url}",
            ))
        except Exception as e:
            self.results.append(ValidationResult(
                name="Ollama LLM Connectivity",
                passed=False,
                message=f"Ollama check failed: {str(e)}",
            ))
    
    # ═══════════════════════════════════════════════════════════════════════════
    # Check 5: Security Configuration
    # ═══════════════════════════════════════════════════════════════════════════
    
    def check_security_configuration(self):
        """Validate security settings."""
        print("🔒 Checking Security Configuration...")
        
        issues = []
        
        # Check for production mode
        debug = self.env.get("DEBUG", "false").lower()
        if debug == "true":
            issues.append("DEBUG should be 'false' in production")
        
        # Check TLS/SSL
        ssl_cert = self.env.get("SSL_CERT_PATH")
        ssl_key = self.env.get("SSL_KEY_PATH")
        if ssl_cert and ssl_key:
            if not os.path.exists(ssl_cert):
                issues.append(f"SSL_CERT_PATH file not found: {ssl_cert}")
            if not os.path.exists(ssl_key):
                issues.append(f"SSL_KEY_PATH file not found: {ssl_key}")
        else:
            self.warnings.append("SSL certificates not configured (consider using HTTPS)")
        
        # Check secure cookie settings
        secure_cookies = self.env.get("SECURE_COOKIES", "false").lower()
        if secure_cookies != "true" and debug != "true":
            issues.append("SECURE_COOKIES should be 'true' in production")
        
        # Check CORS
        cors_origins = self.env.get("CORS_ORIGINS", "*")
        if cors_origins == "*" and debug != "true":
            issues.append("CORS_ORIGINS should not be '*' in production")
        
        passed = len(issues) == 0
        
        self.results.append(ValidationResult(
            name="Security Configuration",
            passed=passed,
            message=f"Found {len(issues)} security issues" if issues else "Security configuration valid",
            details={"issues": issues},
        ))
    
    # ═══════════════════════════════════════════════════════════════════════════
    # Check 6: Middleware Configuration
    # ═══════════════════════════════════════════════════════════════════════════
    
    def check_middleware_configuration(self):
        """Validate middleware is correctly configured."""
        print("🛡️  Checking Middleware Configuration...")
        
        try:
            from apps.api.main import app
            
            # Check middleware stack
            middleware_classes = [type(m).__name__ for m in app.user_middleware]
            
            required_middleware = [
                "LockerSecurityMiddleware",
                "RateLimitMiddleware", 
                "ZeroTrustMiddleware",
            ]
            
            missing = [m for m in required_middleware if m not in middleware_classes]
            
            if missing:
                self.results.append(ValidationResult(
                    name="Middleware Configuration",
                    passed=False,
                    message=f"Missing middleware: {', '.join(missing)}",
                    details={"configured": middleware_classes},
                ))
            else:
                self.results.append(ValidationResult(
                    name="Middleware Configuration",
                    passed=True,
                    message=f"All required middleware present ({len(middleware_classes)} total)",
                    details={"middleware": middleware_classes},
                ))
                
        except Exception as e:
            self.results.append(ValidationResult(
                name="Middleware Configuration",
                passed=False,
                message=f"Failed to check middleware: {str(e)}",
            ))
    
    # ═══════════════════════════════════════════════════════════════════════════
    # Check 7: API Endpoints
    # ═══════════════════════════════════════════════════════════════════════════
    
    def check_api_endpoints(self):
        """Validate API endpoints are accessible."""
        print("🌐 Checking API Endpoints...")
        
        base_url = self.env.get("API_BASE_URL", "http://localhost:8000")
        
        endpoints = [
            ("/health", "Health check"),
            ("/status", "System status"),
            ("/api/v1/docs", "Swagger UI"),
        ]
        
        results = []
        
        for path, description in endpoints:
            try:
                response = httpx.get(f"{base_url}{path}", timeout=10)
                results.append({
                    "path": path,
                    "description": description,
                    "status": response.status_code,
                    "ok": response.status_code == 200,
                })
            except Exception as e:
                results.append({
                    "path": path,
                    "description": description,
                    "error": str(e),
                    "ok": False,
                })
        
        all_ok = all(r["ok"] for r in results)
        
        self.results.append(ValidationResult(
            name="API Endpoints",
            passed=all_ok,
            message=f"{sum(r['ok'] for r in results)}/{len(results)} endpoints accessible",
            details={"endpoints": results},
        ))
    
    # ═══════════════════════════════════════════════════════════════════════════
    # Check 8: File Permissions
    # ═══════════════════════════════════════════════════════════════════════════
    
    def check_file_permissions(self):
        """Validate sensitive file permissions."""
        print("📁 Checking File Permissions...")
        
        issues = []
        
        # Check .env file permissions (if it exists)
        env_path = Path(".env")
        if env_path.exists():
            stat = env_path.stat()
            # Check if readable by others (Unix only)
            if hasattr(stat, 'st_mode'):
                mode = stat.st_mode
                if mode & 0o044:  # Readable by group or others
                    issues.append(".env file is readable by others (should be 600)")
        
        # Check for exposed .git directory
        git_path = Path(".git")
        if git_path.exists():
            # In production, .git shouldn't be accessible
            self.warnings.append(".git directory present (ensure it's not web-accessible)")
        
        passed = len(issues) == 0
        
        self.results.append(ValidationResult(
            name="File Permissions",
            passed=passed,
            message=f"Found {len(issues)} permission issues" if issues else "File permissions OK",
            details={"issues": issues},
        ))
    
    # ═══════════════════════════════════════════════════════════════════════════
    # Report Generation
    # ═══════════════════════════════════════════════════════════════════════════
    
    def print_report(self):
        """Print validation report."""
        print("\n" + "=" * 80)
        print("📊 PRODUCTION DEPLOYMENT VALIDATION REPORT")
        print("=" * 80)
        print(f"Timestamp: {datetime.utcnow().isoformat()}")
        print("-" * 80)
        
        passed = 0
        failed = 0
        
        for result in self.results:
            status = "✅ PASS" if result.passed else "❌ FAIL"
            print(f"\n{status} - {result.name}")
            print(f"   {result.message}")
            
            if result.details:
                for key, value in result.details.items():
                    if isinstance(value, list) and len(str(value)) > 60:
                        print(f"   {key}: [{len(value)} items]")
                    else:
                        print(f"   {key}: {value}")
            
            if result.passed:
                passed += 1
            else:
                failed += 1
        
        print("\n" + "=" * 80)
        print(f"SUMMARY: {passed} passed, {failed} failed, {len(self.warnings)} warnings")
        print("=" * 80)
        
        if self.warnings:
            print("\n⚠️  WARNINGS:")
            for warning in self.warnings:
                print(f"   - {warning}")
        
        if failed > 0:
            print("\n❌ PRODUCTION DEPLOYMENT NOT READY")
            print("   Fix failed checks before deploying to production.")
            return 1
        else:
            print("\n✅ PRODUCTION DEPLOYMENT READY")
            print("   All critical checks passed.")
            return 0


def main():
    """Main entry point."""
    validator = ProductionValidator()
    
    try:
        is_valid, results = validator.run_all_checks()
        exit_code = validator.print_report()
        
        # Optionally write report to file
        report_file = Path("production_validation_report.json")
        report_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "valid": is_valid,
            "results": [
                {
                    "name": r.name,
                    "passed": r.passed,
                    "message": r.message,
                    "details": r.details,
                }
                for r in results
            ],
            "warnings": validator.warnings,
        }
        
        report_file.write_text(json.dumps(report_data, indent=2))
        print(f"\n📝 Detailed report saved to: {report_file}")
        
        sys.exit(exit_code)
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Validation interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ Validation script failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
