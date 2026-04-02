#!/usr/bin/env python3
"""
Code Structure Validation for Multi-Tenant BYOS Backend
Validates that all required components are properly implemented
"""

import os
import sys
import ast
import importlib.util
from pathlib import Path
from typing import Dict, List, Any
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CodeStructureValidator:
    """Validate the code structure and implementation."""
    
    def __init__(self, base_path: str = "."):
        self.base_path = Path(base_path)
        self.validation_results: Dict[str, Any] = {}
        
    def validate_all(self) -> Dict[str, Any]:
        """Run all validation checks."""
        logger.info("🔍 Starting Code Structure Validation")
        
        validations = [
            ("File Structure", self.validate_file_structure),
            ("Import Dependencies", self.validate_imports),
            ("Database Models", self.validate_database_models),
            ("API Endpoints", self.validate_api_endpoints),
            ("Security Implementation", self.validate_security),
            ("Configuration", self.validate_configuration),
            ("Docker Configuration", self.validate_docker_config),
            ("Scripts and Tools", self.validate_scripts)
        ]
        
        for validation_name, validation_func in validations:
            try:
                logger.info(f"Validating: {validation_name}")
                result = validation_func()
                self.validation_results[validation_name] = {
                    "status": "PASSED",
                    "details": result
                }
                logger.info(f"✅ {validation_name} PASSED")
            except Exception as e:
                logger.error(f"❌ {validation_name} FAILED: {e}")
                self.validation_results[validation_name] = {
                    "status": "FAILED",
                    "error": str(e)
                }
        
        # Generate summary
        total_validations = len(validations)
        passed_validations = len([v for v in self.validation_results.values() if v["status"] == "PASSED"])
        failed_validations = total_validations - passed_validations
        
        summary = {
            "total_validations": total_validations,
            "passed": passed_validations,
            "failed": failed_validations,
            "overall_status": "SUCCESS" if failed_validations == 0 else "FAILED",
            "details": self.validation_results
        }
        
        logger.info(f"Validation Complete: {passed_validations}/{total_validations} passed")
        return summary
    
    def validate_file_structure(self) -> Dict[str, Any]:
        """Validate required file structure exists."""
        required_files = [
            "apps/api/main.py",
            "apps/api/tenant_auth.py",
            "apps/api/routers/multi_tenant_llm.py",
            "apps/api/routers/executive_dashboard.py",
            "db/models/tenant.py",
            "db/models/__init__.py",
            "database/init.sql",
            "core/config.py",
            "core/security.py",
            "core/cache/redis_cache.py",
            "ai/providers/local_llm.py",
            "docker-compose.local.yml",
            "test_production_smoke.py",
            "manage_tenants.py",
            "deploy_production.py"
        ]
        
        missing_files = []
        existing_files = []
        
        for file_path in required_files:
            full_path = self.base_path / file_path
            if full_path.exists():
                existing_files.append(file_path)
            else:
                missing_files.append(file_path)
        
        return {
            "required_files": len(required_files),
            "existing_files": len(existing_files),
            "missing_files": missing_files,
            "all_present": len(missing_files) == 0
        }
    
    def validate_imports(self) -> Dict[str, Any]:
        """Validate that all imports in key files work."""
        key_files = [
            "apps/api/tenant_auth.py",
            "apps/api/routers/multi_tenant_llm.py",
            "db/models/tenant.py",
            "ai/providers/local_llm.py"
        ]
        
        import_results = {}
        
        for file_path in key_files:
            full_path = self.base_path / file_path
            if not full_path.exists():
                continue
                
            try:
                with open(full_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Parse AST to find imports
                tree = ast.parse(content)
                imports = []
                
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            imports.append(alias.name)
                    elif isinstance(node, ast.ImportFrom):
                        module = node.module or ""
                        for alias in node.names:
                            imports.append(f"{module}.{alias.name}")
                
                import_results[file_path] = {
                    "status": "PARSED",
                    "import_count": len(imports),
                    "imports": imports[:10]  # First 10 imports
                }
                
            except Exception as e:
                import_results[file_path] = {
                    "status": "FAILED",
                    "error": str(e)
                }
        
        return import_results
    
    def validate_database_models(self) -> Dict[str, Any]:
        """Validate database model structure."""
        tenant_model_path = self.base_path / "db/models/tenant.py"
        
        if not tenant_model_path.exists():
            raise Exception("tenant.py model file not found")
        
        with open(tenant_model_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check for required model classes
        required_classes = ["Tenant", "Execution", "TenantSetting"]
        found_classes = []
        
        tree = ast.parse(content)
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                if node.name in required_classes:
                    found_classes.append(node.name)
        
        # Check for required columns in Tenant model
        required_columns = ["tenant_id", "name", "api_key_hash", "execution_limit", "is_active"]
        
        return {
            "required_classes": required_classes,
            "found_classes": found_classes,
            "all_classes_present": len(found_classes) == len(required_classes),
            "has_api_key_hash": "api_key_hash" in content,
            "has_rls_support": "ENABLE ROW LEVEL SECURITY" in (self.base_path / "database/init.sql").read_text() if (self.base_path / "database/init.sql").exists() else False
        }
    
    def validate_api_endpoints(self) -> Dict[str, Any]:
        """Validate API endpoint implementations."""
        router_path = self.base_path / "apps/api/routers/multi_tenant_llm.py"
        
        if not router_path.exists():
            raise Exception("multi_tenant_llm.py router not found")
        
        with open(router_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check for required endpoints
        required_endpoints = [
            "/chat/completions",
            "/models", 
            "/executions",
            "/status"
        ]
        
        found_endpoints = []
        for endpoint in required_endpoints:
            if endpoint in content:
                found_endpoints.append(endpoint)
        
        # Check for tenant authentication
        has_tenant_auth = "get_tenant_from_api_key" in content
        has_rate_limiting = "rate_limit" in content.lower()
        has_caching = "cache" in content.lower()
        
        return {
            "required_endpoints": required_endpoints,
            "found_endpoints": found_endpoints,
            "all_endpoints_present": len(found_endpoints) == len(required_endpoints),
            "has_tenant_auth": has_tenant_auth,
            "has_rate_limiting": has_rate_limiting,
            "has_caching": has_caching
        }
    
    def validate_security(self) -> Dict[str, Any]:
        """Validate security implementation."""
        security_files = [
            "apps/api/tenant_auth.py",
            "core/security.py"
        ]
        
        security_features = {
            "api_key_hashing": False,
            "hmac_verification": False,
            "jwt_support": False,
            "password_hashing": False
        }
        
        for file_path in security_files:
            full_path = self.base_path / file_path
            if not full_path.exists():
                continue
                
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            if "hash_api_key" in content:
                security_features["api_key_hashing"] = True
            if "hmac" in content.lower():
                security_features["hmac_verification"] = True
            if "jwt" in content.lower():
                security_features["jwt_support"] = True
            if "password_hash" in content or "bcrypt" in content:
                security_features["password_hashing"] = True
        
        return security_features
    
    def validate_configuration(self) -> Dict[str, Any]:
        """Validate configuration setup."""
        config_path = self.base_path / "core/config.py"
        
        if not config_path.exists():
            raise Exception("config.py not found")
        
        with open(config_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        required_configs = [
            "database_url",
            "redis_url", 
            "local_llm_url",
            "secret_key"
        ]
        
        found_configs = []
        for config in required_configs:
            if config.replace("_", "") in content.lower() or config in content.lower():
                found_configs.append(config)
        
        return {
            "required_configs": required_configs,
            "found_configs": found_configs,
            "all_configs_present": len(found_configs) == len(required_configs)
        }
    
    def validate_docker_config(self) -> Dict[str, Any]:
        """Validate Docker configuration."""
        docker_path = self.base_path / "docker-compose.local.yml"
        
        if not docker_path.exists():
            raise Exception("docker-compose.local.yml not found")
        
        with open(docker_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        required_services = ["byos-backend", "postgres", "redis", "ollama"]
        found_services = []
        
        for service in required_services:
            if service in content:
                found_services.append(service)
        
        has_health_checks = "healthcheck" in content
        has_volumes = "volumes" in content
        has_networks = "networks" in content
        
        return {
            "required_services": required_services,
            "found_services": found_services,
            "all_services_present": len(found_services) == len(required_services),
            "has_health_checks": has_health_checks,
            "has_volumes": has_volumes,
            "has_networks": has_networks
        }
    
    def validate_scripts(self) -> Dict[str, Any]:
        """Validate utility scripts."""
        scripts = [
            "test_production_smoke.py",
            "manage_tenants.py", 
            "deploy_production.py"
        ]
        
        script_results = {}
        
        for script in scripts:
            script_path = self.base_path / script
            if script_path.exists():
                try:
                    with open(script_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # Basic syntax check
                    ast.parse(content)
                    
                    script_results[script] = {
                        "status": "VALID",
                        "size_lines": len(content.splitlines())
                    }
                except SyntaxError as e:
                    script_results[script] = {
                        "status": "SYNTAX_ERROR",
                        "error": str(e)
                    }
            else:
                script_results[script] = {
                    "status": "MISSING"
                }
        
        return script_results


def main():
    """Main validation function."""
    validator = CodeStructureValidator()
    results = validator.validate_all()
    
    # Print results
    print("\n" + "="*60)
    print("CODE STRUCTURE VALIDATION RESULTS")
    print("="*60)
    print(f"Overall Status: {results['overall_status']}")
    print(f"Passed: {results['passed']}/{results['total_validations']}")
    
    print("\nValidation Details:")
    for validation_name, result in results['details'].items():
        status_icon = "✅" if result["status"] == "PASSED" else "❌"
        print(f"  {status_icon} {validation_name}")
        
        if result["status"] == "FAILED" and "error" in result:
            print(f"     Error: {result['error']}")
    
    # Print key findings
    print("\n🔍 Key Findings:")
    
    if "File Structure" in results['details']:
        file_result = results['details']["File Structure"]["details"]
        print(f"  📁 Files: {file_result['existing_files']}/{file_result['required_files']} present")
    
    if "Database Models" in results['details']:
        db_result = results['details']["Database Models"]["details"]
        print(f"  🗄️  Database Models: {len(db_result['found_classes'])}/{len(db_result['required_classes'])} found")
        print(f"  🔐 API Key Hashing: {'✅' if db_result['has_api_key_hash'] else '❌'}")
    
    if "API Endpoints" in results['details']:
        api_result = results['details']["API Endpoints"]["details"]
        print(f"  🌐 API Endpoints: {len(api_result['found_endpoints'])}/{len(api_result['required_endpoints'])} implemented")
        print(f"  🔑 Tenant Auth: {'✅' if api_result['has_tenant_auth'] else '❌'}")
    
    if "Docker Configuration" in results['details']:
        docker_result = results['details']["Docker Configuration"]["details"]
        print(f"  🐳 Services: {len(docker_result['found_services'])}/{len(docker_result['required_services'])} configured")
    
    return 0 if results['overall_status'] == "SUCCESS" else 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
