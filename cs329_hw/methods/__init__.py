"""
Code from: https://github.com/stanford-cs329a/homework1-public
"""

from .simple_samplers import GreedyMethod, SampleMultiple
__all__ = ["GreedyMethod", "SampleMultiple", "InputGenConfig", "InputOnlyLLMTestGenerator"]


def get_sampler(
    method: str,
    model: str,
    system_prompt: str = None,
    n_samples: int = 3,
    temperature: float = 0.0,
):
    if method == "sample_multiple":
        assert temperature > 0.0, "Sample multiple requires temperature > 0"
        return SampleMultiple(model, system_prompt, n_samples, temperature)
    elif method == "greedy":
        assert (
            temperature == 0.0
        ), "Greedy decoding does not use temperature, it will be 0 by default"
        return GreedyMethod(model, system_prompt)
    else:
        raise ValueError(f"Unknown method: {method}")