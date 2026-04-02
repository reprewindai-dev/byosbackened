"""Test feature engineering idempotency."""
import pytest
from core.autonomous.training.feature_engineering import get_feature_engineer
from datetime import datetime
import numpy as np

feature_engineer = get_feature_engineer()


class TestFeatureEngineeringIdempotency:
    """Test that feature engineering is idempotent."""
    
    def test_cost_features_idempotent(self):
        """Test that extract_cost_features produces same output for same inputs."""
        # Use fixed reference time for determinism
        reference_time = datetime(2024, 1, 15, 12, 0, 0)
        
        # Extract features twice
        features1 = feature_engineer.extract_cost_features(
            operation_type="transcribe",
            provider="openai",
            input_tokens=1000,
            estimated_output_tokens=300,
            time_of_day=12,
            workspace_id="test-workspace",
            reference_time=reference_time,
        )
        
        features2 = feature_engineer.extract_cost_features(
            operation_type="transcribe",
            provider="openai",
            input_tokens=1000,
            estimated_output_tokens=300,
            time_of_day=12,
            workspace_id="test-workspace",
            reference_time=reference_time,
        )
        
        # Should be identical
        assert len(features1) == len(features2)
        assert all(np.isclose(f1, f2) for f1, f2 in zip(features1, features2))
    
    def test_cost_features_deterministic_with_reference_time(self):
        """Test that reference_time makes features deterministic."""
        reference_time = datetime(2024, 1, 15, 12, 0, 0)
        
        # Extract features with reference_time
        features_with_ref = feature_engineer.extract_cost_features(
            operation_type="transcribe",
            provider="openai",
            input_tokens=1000,
            estimated_output_tokens=300,
            workspace_id="test-workspace",
            reference_time=reference_time,
        )
        
        # Extract again with same reference_time (even if called later)
        features_with_ref2 = feature_engineer.extract_cost_features(
            operation_type="transcribe",
            provider="openai",
            input_tokens=1000,
            estimated_output_tokens=300,
            workspace_id="test-workspace",
            reference_time=reference_time,
        )
        
        # Should be identical
        assert len(features_with_ref) == len(features_with_ref2)
        assert all(np.isclose(f1, f2) for f1, f2 in zip(features_with_ref, features_with_ref2))
    
    def test_quality_features_idempotent(self):
        """Test that extract_quality_features produces same output for same inputs."""
        reference_time = datetime(2024, 1, 15, 12, 0, 0)
        
        features1 = feature_engineer.extract_quality_features(
            operation_type="transcribe",
            provider="openai",
            input_text="Test input text",
            workspace_id="test-workspace",
            reference_time=reference_time,
        )
        
        features2 = feature_engineer.extract_quality_features(
            operation_type="transcribe",
            provider="openai",
            input_text="Test input text",
            workspace_id="test-workspace",
            reference_time=reference_time,
        )
        
        # Should be identical
        assert len(features1) == len(features2)
        assert all(np.isclose(f1, f2) for f1, f2 in zip(features1, features2))
    
    def test_routing_features_idempotent(self):
        """Test that extract_routing_features produces same output for same inputs."""
        constraints = {
            "max_cost": 0.01,
            "min_quality": 0.85,
            "strategy": "cost_optimized",
        }
        
        features1 = feature_engineer.extract_routing_features(
            workspace_id="test-workspace",
            operation_type="transcribe",
            available_providers=["openai", "huggingface"],
            constraints=constraints,
        )
        
        features2 = feature_engineer.extract_routing_features(
            workspace_id="test-workspace",
            operation_type="transcribe",
            available_providers=["openai", "huggingface"],
            constraints=constraints,
        )
        
        # Should have same providers
        assert set(features1.keys()) == set(features2.keys())
        
        # Features for each provider should be identical
        for provider in features1.keys():
            f1 = features1[provider]
            f2 = features2[provider]
            assert len(f1) == len(f2)
            assert all(np.isclose(f1[i], f2[i]) for i in range(len(f1)))
    
    def test_workspace_hash_deterministic(self):
        """Test that workspace hash is deterministic."""
        reference_time = datetime(2024, 1, 15, 12, 0, 0)
        
        # Extract features for same workspace twice
        features1 = feature_engineer.extract_cost_features(
            operation_type="transcribe",
            provider="openai",
            input_tokens=1000,
            estimated_output_tokens=300,
            workspace_id="test-workspace-123",
            reference_time=reference_time,
        )
        
        features2 = feature_engineer.extract_cost_features(
            operation_type="transcribe",
            provider="openai",
            input_tokens=1000,
            estimated_output_tokens=300,
            workspace_id="test-workspace-123",
            reference_time=reference_time,
        )
        
        # Workspace hash should be same (last feature)
        assert features1[-1] == features2[-1]
        
        # Different workspace should have different hash
        features3 = feature_engineer.extract_cost_features(
            operation_type="transcribe",
            provider="openai",
            input_tokens=1000,
            estimated_output_tokens=300,
            workspace_id="test-workspace-456",
            reference_time=reference_time,
        )
        
        assert features1[-1] != features3[-1]
