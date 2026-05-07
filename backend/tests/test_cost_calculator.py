from core.cost_intelligence.cost_calculator import CostCalculator


def test_predict_cost_returns_alternatives_without_recursive_overflow():
    calculator = CostCalculator()

    prediction = calculator.predict_cost(
        operation_type="generation",
        provider="local",
        input_tokens=500,
        estimated_output_tokens=300,
        model="qwen2.5:3b",
        include_alternatives=True,
        use_ml=False,
    )

    assert prediction.predicted_cost >= 0
    assert len(prediction.alternative_providers) == 2
