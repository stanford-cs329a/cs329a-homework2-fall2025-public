# from .openai_models import OpenAIModel

# __all__ = ["OpenAIModel"]


# def get_model(model: str, system_prompt: str = None) -> OpenAIModel:
#     return OpenAIModel(model, system_prompt)

from .litellm_models import LiteLLMModel

__all__ = ["LiteLLMModel"]


def get_model(model: str, system_prompt: str = None) -> LiteLLMModel:
    return LiteLLMModel(model, system_prompt)