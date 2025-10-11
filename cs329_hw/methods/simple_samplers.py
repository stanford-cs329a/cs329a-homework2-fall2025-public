from typing import List, Union
from cs329_hw.openai_inference import LiteLLMModel
import litellm

litellm.suppress_debug_info = True
litellm.telemetry = False

class GreedyMethod:
    """
    A class that implements a greedy zero-shot strategy using LiteLLM models.
    """

    def __init__(self, model: str, system_prompt: str = None, max_workers: int = 256):
        """
        Initialize the greedy method with a specific model.

        Args:
            model (str): The name of the model to use
            system_prompt (str, optional): System prompt to use for the model
        """
        self.llm = LiteLLMModel(
            model=model,
            system_prompt=system_prompt,
            temperature=0.7,  
            max_tokens=4096,
            max_workers=max_workers,
        )
        self.normalized_prediction = False

    def __call__(
        self, prompts: Union[str, List[str]]
    ) -> Union[List[List[str]], List[str]]:
        """
        Execute the greedy method on a given prompt or list of prompts.

        Args:
            prompts (str or List[str]): The input prompt(s) to process

        Returns:
            List[List[str]]: For single prompt: [[response]]
                            For multiple prompts: [[response1], [response2], ...]
        """
        if isinstance(prompts, str):
            return [[self.llm.send_request(prompts)]]  # Double wrap for consistency
        elif isinstance(prompts, list):
            assert all(
                isinstance(p, str) for p in prompts
            ), "All prompts must be strings"
            responses = self.llm.send_requests(prompts)
            return [[r] for r in responses]  # Wrap each response in a list
        else:
            raise TypeError("prompts must be a string or a list of strings.")


class SampleMultiple:
    def __init__(
        self,
        model: str,
        system_prompt: str = None,
        n_samples: int = 3,
        temperature: float = 0.7,
        max_workers: int = 256,
    ):
        """
        Initialize the sampling method with a specific model.

        Args:
            model (str): The name of the model to use
            system_prompt (str, optional): System prompt to use for the model
            n_samples (int, optional): Number of samples to generate per prompt. Defaults to 3.
        """
        self.llm = LiteLLMModel(
            model=model,
            system_prompt=system_prompt,
            temperature=temperature,
            max_tokens=4096,
            max_workers=max_workers,
        )
        self.n_samples = n_samples
        self.normalized_prediction = False

    def __call__(self, prompts: Union[str, List[str]]) -> List[List[str]]:
        """
        Execute the sampling method on a given prompt or list of prompts.

        Args:
            prompts (str or List[str]): The input prompt(s) to process

        Returns:
            List[List[str]]: A list of lists, where each inner list contains n_samples responses
                             for a single prompt
        """
        if isinstance(prompts, str):
            assert isinstance(prompts, str), "Single prompt must be a string"
            # Duplicate the single prompt n_samples times
            prompts_to_send = [prompts] * self.n_samples
            responses = self.llm.send_requests(prompts_to_send)
            return [responses]

        elif isinstance(prompts, list):
            assert all(
                isinstance(p, str) for p in prompts
            ), "All prompts must be strings"
            # Create a list with each prompt repeated n_samples times
            prompts_to_send = [
                prompt for prompt in prompts for _ in range(self.n_samples)
            ]
            responses = self.llm.send_requests(prompts_to_send)
            # Group the responses per original prompt
            grouped_responses = [
                responses[i * self.n_samples : (i + 1) * self.n_samples]
                for i in range(len(prompts))
            ]
            return grouped_responses

        else:
            raise TypeError("prompts must be a string or a list of strings.")