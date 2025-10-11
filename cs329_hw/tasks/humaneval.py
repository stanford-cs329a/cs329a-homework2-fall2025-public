"""
Code adapted from: https://github.com/stanford-cs329a/homework1-public
"""

import os
import json
import random

class HumanEval:
    def __init__(self, root_dir: str = "./data", file_name: str = "test.json"):
        self.root_dir = root_dir
        self.file_path = os.path.join(root_dir, file_name)
        if not os.path.exists(self.file_path):
            raise FileNotFoundError(
                f"Could not find {self.file_path}. "
                "Please run the preprocessing script first."
            )
        
        with open(self.file_path, "r") as f:
            self.dataset = json.load(f)  # dict keyed by task_id

        self.rng = random.Random(42)

    def get_problems(self, debug_mode: bool = False) -> list[dict]:
        problems = [
            {
                "task_id": task_id,
                **problem_data
            }
            for task_id, problem_data in self.dataset.items()
        ]
        self.rng.shuffle(problems)
        if debug_mode:
            return problems[:20]
        else:
            return problems


    def get_system_prompt(self) -> str:
        return (
            """
            You are a professional at programming in Python. You will be given a docstring describing the behavior of a function.
            You have to reason about the docstring and return Python code satisfying the requirements. Your response should include
            code fences around the code *only*. Do not include anything besides code within the code fences.
            """
        )
