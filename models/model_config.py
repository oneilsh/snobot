"""Model configuration and pricing information."""

from dataclasses import dataclass
from typing import Dict, Optional


@dataclass
class ModelConfig:
    """Configuration for a language model including pricing."""
    name: str
    input_cost_per_million: float  # Cost per million input tokens
    output_cost_per_million: float  # Cost per million output tokens
    display_name: Optional[str] = None
    
    def calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Calculate total cost for given token usage."""
        input_cost = (input_tokens / 1_000_000) * self.input_cost_per_million
        output_cost = (output_tokens / 1_000_000) * self.output_cost_per_million
        return input_cost + output_cost
    
    def get_display_name(self) -> str:
        """Get the display name for this model."""
        return self.display_name or self.name


# Model configurations with current pricing
MODEL_CONFIGS: Dict[str, ModelConfig] = {
    "gpt-4.1": ModelConfig(
        name="gpt-4.1",
        input_cost_per_million=2.00,
        output_cost_per_million=8.00,
        display_name="GPT-4.1"
    )
}

# Default model to use
DEFAULT_MODEL = "gpt-4.1"


def get_model_config(model_name: str) -> ModelConfig:
    """Get configuration for a model, with fallback to default pricing."""
    if model_name in MODEL_CONFIGS:
        return MODEL_CONFIGS[model_name]
    
    # Fallback for unknown models - use GPT-4.1 pricing as conservative estimate
    return ModelConfig(
        name=model_name,
        input_cost_per_million=2.00,
        output_cost_per_million=8.00,
        display_name=model_name
    )


def format_cost(cost: float) -> str:
    """Format cost for display."""
    if cost < 0.001:
        return f"${cost:.6f}"
    elif cost < 0.01:
        return f"${cost:.4f}"
    elif cost < 1.0:
        return f"${cost:.3f}"
    else:
        return f"${cost:.2f}"
