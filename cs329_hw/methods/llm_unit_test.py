from __future__ import annotations
from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Tuple, Union
import json, re
from cs329_hw.methods.verifiers import TestCase
from cs329_hw.methods.simple_samplers import SampleMultiple

@dataclass
class LLMUnitTestGeneratorConfig:
    n_unit_tests: int = 10
    temperature: float = 0.7
    deduplicate_unit_tests: bool = True

class LLMUnitTestGenerator:
    """
    Class for generating unit tests with LLM.
    
    Given a problem docstring and function name, generates a list of JSON-formatted test cases,
    which are conereted to a list of TestCase objects for use with HumanEvalVerifier.
    
    [{"name": str, "args": [...], "kwargs": {...}, "expected": ...}, ...]
    """

    def __init__(
        self,
        sampler: SampleMultiple,
        cfg: LLMUnitTestGeneratorConfig = LLMUnitTestGeneratorConfig(),
        model_name: str = "together_ai/Qwen/Qwen3-Next-80B-A3B-Instruct"
    ):
        self.sampler = sampler
        self.cfg = cfg
        self.model_name = model_name

    def generate(
        self,
        problem_prompt: str,
        function_name: str,
        n_unit_tests: int = 10,
    ) -> list[TestCase]:
        """
        Generates a list of TestCase objects suitable for passing to HumanEvalVerifier.verify(test_suite=cases)

        This method orchestrates the entire unit test generation pipeline, from building the prompt,
        parsing the response, and formatting it into a clean (optionally deduplicated) list of TestCase objects.
        
        Args:
            problem_prompt (str): The problem specification.
            function_name (str): The name of the target function.
            n_unit_tests (int): The number of unit tests to generate.

        Returns:
            list[TestCase]: A list of TestCase objects ready for verification.
        """

        ### TODO: YOUR CODE STARTS HERE
        pass
        ### TODO: YOUR CODE ENDS HERE


    def _build_prompt(self, problem_prompt: str, function_name: str, num_unit_tests: int) -> str:
        """
        Builds a complete prompt for the LLM unit test generator.

        Your prompt should include:
          - A message framing the LLM's behavior as an expert unit test designer that
            logically infers test cases from a problem specification without ever executing code.
          - The problem statement (`problem_prompt`) and target function name (`function_name`) to be tested
          - A precise description of the required JSON structure. This should include:
            - Description of top-level structure (e.g. JSON array) and of the required fields for each test case object
              (e.g. `name`, `args`, `kwargs`, `expected`)
            - Brief explanation of each field's purpose and expected type (e.g. `name` is a string, `args` is an array, etc.)
          - Instructions for the number (`num_unit_tests`), diversity (basic + edge cases), and style of generated test cases
          - Explicit instructions against generating any markdown, text, or explanations outside of the primary JSON array.

        The LLM unit test generator should be prompted to return **only** a JSON array of test cases 
        with the following schema:
            - `name`: a short descriptive name for the test case (e.g. `test_positive_case`)
            - `args`: a JSON array for positional arguments. The order must match the function signature.
            - `kwargs`: a JSON object for keyword (named) arguments. Use this for optional parameters.
            - `expected`: the expected output for the test case, matching the function return type.
        
        [
            {{
                "name": "short_descriptionof_test",
                "args": [...],
                "kwargs": {{...}},
                "expected": ...
            }},
        ]
        """

        ### TODO: YOUR CODE STARTS HERE 
        pass
        ### TODO: YOUR CODE ENDS HERE

    def _parse_test_list(self, raw_output: str) -> List[Dict[str, Any]]:
        """
        Parses raw LLM output into a list of dicts with keys: `name`, `args`, `kwargs`, `expected`.
        Accepts raw JSON, or JSON inside fences. Falls back to [] if unparseable.
        """
        if not raw_output or not raw_output.strip():
            return []

        txt = raw_output.strip()

        m = re.search(r"```(?:json)?\s*([\s\S]*?)```", txt, flags=re.IGNORECASE)
        if m:
            txt = m.group(1).strip()

        arr_match = re.search(r"\[\s*[\s\S]*\]\s*$", txt)
        if arr_match:
            txt = arr_match.group(0)

        try:
            data = json.loads(txt)
        except Exception:
            return []

        if not isinstance(data, list):
            return []

        norm = []
        for i, r in enumerate(data):
            if not isinstance(r, dict):
                continue
            name = str(r.get("name", f"case_{i}"))
            args = r.get("args", [])
            kwargs = r.get("kwargs", {})
            expected = r.get("expected", None)
            if not isinstance(args, list):
                continue
            if not isinstance(kwargs, dict):
                continue
            norm.append({"name": name, "args": args, "kwargs": kwargs, "expected": expected})

        return norm

    def _to_testcase(self, rec: Dict[str, Any], i: int) -> TestCase:
        """Converts a dict to a TestCase object."""
        name = rec.get("name") or f"case_{i}"
        args = rec.get("args") or []
        kwargs = rec.get("kwargs") or {}
        expected = rec.get("expected", None)
        return TestCase(name=name, args=args, kwargs=kwargs, expected=expected)

    def _deduplicate_test_cases(self, cases: List[TestCase]) -> List[TestCase]:
        """Removes duplicate test cases based on their input arguments."""
        seen = set()
        uniq: List[TestCase] = []
        for tc in cases:
            key = (json.dumps(tc.args, sort_keys=True), json.dumps(tc.kwargs, sort_keys=True))
            if key in seen:
                continue
            seen.add(key)
            uniq.append(tc)
        return uniq
