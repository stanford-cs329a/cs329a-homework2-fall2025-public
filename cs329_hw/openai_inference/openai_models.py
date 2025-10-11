import os
import threading
from typing import List, Dict, Union
from openai import OpenAI
from tenacity import (
    retry,
    stop_after_attempt,
    wait_random_exponential,
)
from concurrent.futures import ThreadPoolExecutor

class OpenAIModel:
    """
    A class to send multiple requests to a specified OpenAI model concurrently using threading.
    """

    def __init__(
        self,
        model: str,
        system_prompt: str = None,
        temperature: float = 0.0,
        max_workers: int = 256,
    ):
        """
        Initializes the OpenAIModel with the specified model.

        Args:
            model (str): The name of the model to send requests to.
            system_prompt (str): The system prompt to use for the model.
            temperature (float): The temperature to use for the model.
            max_workers (int): The maximum number of concurrent requests to the model.

        Raises:
            ValueError: If OPENAI_API_KEY environment variable is not set.
        """
        if not os.getenv("OPENAI_API_KEY"):
            raise ValueError("OPENAI_API_KEY environment variable must be set.")

        self.client = OpenAI()
        self.model = model
        self.system_prompt = system_prompt
        self.temperature = temperature
        self.lock = threading.Lock()
        self.max_workers = max_workers

    @retry(wait=wait_random_exponential(min=1, max=5), stop=stop_after_attempt(3))
    def _make_completion_request(self, messages: List[Dict[str, str]]) -> str:
        """
        Makes a chat completion request with retry logic.

        Args:
            messages (List[Dict[str, str]]): The messages to send to the model.

        Returns:
            str: The response from the model.
        """
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=self.temperature,
        )
        return response.choices[0].message.content

    def send_request(self, prompt: str) -> str:
        """
        Sends a single request to the model and returns the response.

        Args:
            prompt (str): The prompt to send to the model.

        Returns:
            str: The response from the model or an error message.
        """
        messages = [{"role": "user", "content": prompt}]
        if self.system_prompt:
            messages.insert(0, {"role": "system", "content": self.system_prompt})
        try:
            return self._make_completion_request(messages)
        except Exception as e:
            import traceback

            print(f"Error in send_request: {str(e)}")
            print(f"Traceback:\n{traceback.format_exc()}")
            return f"Error: {str(e)}"

    def send_requests(self, prompts: List[str]) -> List[str]:
        """
        Sends multiple requests to the model concurrently and returns the list of responses.
        Uses a thread pool to limit concurrent requests.
        """
        responses = [None] * len(prompts)
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {executor.submit(self.send_request, prompt): i for i, prompt in enumerate(prompts)}

            for future in futures:
                i = futures[future]
                try:
                    responses[i] = future.result()
                except Exception as e:
                    responses[i] = f"Error: {str(e)}"
        
        return responses

    def __call__(self, prompts: Union[str, List[str]]) -> Union[str, List[str]]:
        """
        Allows the instance to be called as a function to send prompts.

        Args:
            prompts (str or List[str]): A prompt or a list of prompts to send to the model.

        Returns:
            str or List[str]: The response(s) from the model.
        """
        if isinstance(prompts, str):
            return self.send_request(prompts)
        elif isinstance(prompts, list):
            if not all(isinstance(p, str) for p in prompts):
                raise ValueError("All prompts must be strings.")
            return self.send_requests(prompts)
        else:
            raise TypeError("prompts must be a string or a list of strings.")
