from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Union, NamedTuple

@dataclass
class TestCase:
    name: str
    args: List[Any]
    kwargs: Dict[str, Any]
    expected: Any

class ExecResult(NamedTuple):
    ok: bool
    stdout: str
    stderr: str
    exception: Optional[str]
    time_s: float

import textwrap

class HumanEvalVerifier:
    """
    Verifies code against either:
      (A) HumanEval-style test snippet (string) that defines `check(candidate)`; or
      (B) A list[TestCase] you generated (LLM-as-test-generator).
    Execution is delegated to `runner(code: str, timeout_s: int) -> ExecResult`.
    """

    def __init__(self, runner, timeout_s: int = 2):
        """
        runner: a callable like support.sandbox.run_python(code, timeout_s=...)
                that returns ExecResult(stdout/stderr/etc).
        """
        self.runner = runner
        self.timeout_s = timeout_s

    # ---------- Public API ----------

    def verify(
        self,
        code: str,
        function_name: str,
        test_suite: Union[str, List[TestCase]],
    ) -> Dict[str, Any]:
        """
        Returns:
          {
            'passed_all': bool,
            'num_passed': int,
            'num_total': int,
            'stdout': str,
            'stderr': str,
            'exception': Optional[str],
            'time_s': float,
          }
        """
        if isinstance(test_suite, str):
            harness = self._build_humaneval_harness(code, function_name, test_suite)
            result = self.runner(harness, timeout_s=self.timeout_s)
            passed_all, num_passed, num_total = self._parse_marker_summary(result.stdout)
            return {
                "passed_all": passed_all,
                "num_passed": num_passed,
                "num_total": num_total,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "exception": result.exception,
                "time_s": result.time_s,
            }

        elif isinstance(test_suite, list):
            harness = self._build_structured_harness(code, function_name, test_suite)
            result = self.runner(harness, timeout_s=self.timeout_s)
            passed_all, num_passed, num_total = self._parse_marker_summary(result.stdout)
            return {
                "passed_all": passed_all,
                "num_passed": num_passed,
                "num_total": num_total,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "exception": result.exception,
                "time_s": result.time_s,
            }

        else:
            raise TypeError("test_suite must be either str or List[TestCase].")
    
    @staticmethod
    def print_verification_result(res: dict) -> None:
        """
        Pretty-print the result dictionary returned by HumanEvalVerifier.verify().
        """
        print("=== Verification Result ===")
        print(f"passed_all: {res['passed_all']}")
        print(f"num_passed/num_total: {res['num_passed']} / {res['num_total']}")
        if res.get("stdout"):
            print("--- stdout ---")
            print(res["stdout"].strip())
        if res.get("stderr"):
            print("--- stderr ---")
            print(res["stderr"].strip())
        if res.get("exception"):
            print(f"exception: {res['exception']}")
        print(f"time_s: {res['time_s']:.4f}")

    # ---------- Harness builders ----------


    def _build_humaneval_harness(self, code: str, function_name: str, test_snippet: str) -> str:
        """
        Student code + HumanEval test snippet (defines check) + our assert monkey-patch + markers.
        """
        marker = textwrap.dedent(f"""
    import builtins, time, traceback

    __CASE_ID__ = 0
    __NUM_PASSED__ = 0
    __NUM_TOTAL__ = 0

    def __log_assert__(cond, msg=None):
        global __CASE_ID__, __NUM_PASSED__, __NUM_TOTAL__
        __CASE_ID__ += 1
        __NUM_TOTAL__ += 1
        if cond:
            __NUM_PASSED__ += 1
            print("__CASE__", __CASE_ID__, "PASS")
        else:
            print("__CASE__", __CASE_ID__, "FAIL", msg or "")

    # So we monkey patch 'builtins.__dict__' with a helper function
    def __patched_assert(cond, msg=None, *args):
        return __log_assert__(cond, msg)

    builtins.__dict__['assert_'] = __patched_assert

    __t0 = time.time()
    try:
        check({function_name})
    except Exception as e:
        print("__EXC__=", type(e).__name__, str(e))
    __elapsed = time.time() - __t0

    print("__RESULT__=OK" if (__NUM_PASSED__ != 0 and __NUM_PASSED__ == __NUM_TOTAL__) else "__RESULT__=FAIL")
    print("__COUNTS__=", __NUM_PASSED__, "/", __NUM_TOTAL__)
    print("__TIME__=", __elapsed)
    """)

        # Inject student's code + test snippet + our harness.
        # CORRECTED: Use \n for newlines, not \\n
        return f"{code}\n\n{test_snippet}\n\n{marker}"


    def _build_structured_harness(self, code: str, function_name: str, cases: List[TestCase]) -> str:
        """
        student code + our loop over structured cases + markers
        IMPORTANT: don't dedent the part containing {code}.
        """
        # build the per-case loop at column 0
        case_lines = []
        for i, tc in enumerate(cases):
            # CORRECTED: Use \n for newlines, not \\n
            case_lines.append(
                "try:\n"
                f"    __res = {function_name}(*{repr(tc.args)}, **{repr(tc.kwargs)})\n"
                f"    __ok = (__res == {repr(tc.expected)})\n"
                "except Exception as __e:\n"
                f"    __res = f'__EXC__:{{type(__e).__name__}}:{{__e}}'\n"
                "    __ok = False\n"
                f"print('__CASE__', {i}, int(__ok), repr(__res), repr({repr(tc.expected)}))\n"
                "if __ok:\n"
                "    __NUM_PASSED__ += 1\n"
            )
        loop_code = "".join(case_lines)

        tail = textwrap.dedent(f"""
import time
__NUM_PASSED__ = 0
__NUM_TOTAL__ = {len(cases)}
__t0 = time.time()
{loop_code}
__elapsed = time.time() - __t0

print("__RESULT__=OK" if __NUM_PASSED__ == __NUM_TOTAL__ else "__RESULT__=FAIL")
print("__COUNTS__=", __NUM_PASSED__, "/", __NUM_TOTAL__)
print("__TIME__=", __elapsed)
""")
        # CORRECTED: Use \n for newlines, not \\n
        return f"{code}\n\n{tail}"

    # ---------- Output parsing ----------

    def _parse_marker_summary(self, stdout: str):
        """
        Parse markers from harness output.

        Returns:
            (passed_all, num_passed, num_total)
        """
        passed_all = False
        num_passed = 0
        num_total = 0

        if not stdout:
            return passed_all, num_passed, num_total

        if isinstance(stdout, bytes):
            stdout = stdout.decode("utf-8", errors="ignore")


        for line in stdout.splitlines():
            line = line.strip()
            if line.startswith("__RESULT__="):
                passed_all = (line.split("=", 1)[1].strip() == "OK")
            elif line.startswith("__COUNTS__="):
                # format: "__COUNTS__= 7 / 9"
                try:
                    _, tail = line.split("=", 1)
                    left, right = tail.strip().split("/")
                    num_passed = int(left.strip())
                    num_total = int(right.strip())
                except ValueError as e:
                    print(f"Warning: failed to parse COUNTS line: {line} ({e})")

        # If counts are available but no explicit result, infer pass/fail
        # A small logic bug was here: `line.startswith("__RESULT__=")` should be checked against
        # a flag that indicates if the __RESULT__ line has been seen, not the current line.
        result_line_seen = any("__RESULT__=" in line for line in stdout.splitlines())
        if num_total > 0 and not result_line_seen:
            passed_all = (num_passed == num_total)

        return passed_all, num_passed, num_total