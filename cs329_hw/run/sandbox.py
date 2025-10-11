from __future__ import annotations

import os
import sys
import time
import tempfile
import subprocess
from typing import Optional, NamedTuple

# ----- Public result type -----------------------------------------------------

class ExecResult(NamedTuple):
    ok: bool                 # process exited with code 0
    stdout: str
    stderr: str
    exception: Optional[str] # high-level reason (timeout, OOM-ish, signal)
    time_s: float            # wall-clock time


# ----- POSIX resource limiting helpers ---------------------------------------

def _posix_limit_resources(cpu_seconds: int, mem_mb: int, file_mb: int) -> None:
    """
    preexec_fn for subprocess on POSIX: set rlimits to contain runaway programs.
    - CPU seconds (soft+hard)
    - Address space (approx memory cap)
    - File size (prevent huge outputs to disk)
    - Open files / processes (light containment)
    """
    try:
        import resource  # POSIX-only
        # CPU time
        resource.setrlimit(resource.RLIMIT_CPU, (cpu_seconds, cpu_seconds))
        # Address space (virtual memory) cap
        mem_bytes = mem_mb * 1024 * 1024
        resource.setrlimit(resource.RLIMIT_AS, (mem_bytes, mem_bytes))
        # File size cap for files the process creates
        file_bytes = file_mb * 1024 * 1024
        resource.setrlimit(resource.RLIMIT_FSIZE, (file_bytes, file_bytes))
        # Limit number of open files
        resource.setrlimit(resource.RLIMIT_NOFILE, (256, 256))
        # Limit number of processes/threads (best-effort; not on all platforms)
        if hasattr(resource, "RLIMIT_NPROC"):
            resource.setrlimit(resource.RLIMIT_NPROC, (64, 64))
        # (Optional) core dumps off
        if hasattr(resource, "RLIMIT_CORE"):
            resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    except Exception:
        # If anything fails, we proceed without rlimits rather than crash.
        pass


def _is_posix() -> bool:
    return os.name == "posix"


# ----- Runner ----------------------------------------------------------------

def run_python(
    code: str,
    timeout_s: int = 2,
    mem_mb: int = 256,
    cpu_seconds: Optional[int] = None,
    file_mb: int = 16,
    python_exe: Optional[str] = None,
) -> ExecResult:
    """
    Execute arbitrary Python source in a separate process with basic limits.

    Parameters
    ----------
    code : str
        Full Python program to run (typically: candidate code + test harness).
    timeout_s : int
        Wall-clock timeout for the subprocess. If exceeded, the process is killed.
    mem_mb : int
        Approx memory limit (address space) in MB (POSIX only).
    cpu_seconds : Optional[int]
        CPU time limit in seconds (POSIX only). Defaults to timeout_s if None.
    file_mb : int
        Max file size the process can create (POSIX only).
    python_exe : Optional[str]
        Which Python to use. Defaults to sys.executable.

    Returns
    -------
    ExecResult
        Structured outcome with captured stdout/stderr and high-level reason.
    """
    start = time.time()
    exc_reason = None
    python_exe = python_exe or sys.executable
    cpu_seconds = cpu_seconds or timeout_s

    # Minimal, safer-ish interpreter flags:
    #  -I : isolated mode (ignores user site dirs, PYTHON* env vars)
    #  -B : don’t write .pyc
    #  -S : don’t import site (faster, fewer imports available by default)
    py_flags = ["-I", "-B", "-S"]

    # Very minimal environment (helps avoid leaking creds; still not a true jail)
    env = {
        "PATH": "/usr/bin:/bin",
        "PYTHONHASHSEED": "0",
        "PYTHONIOENCODING": "UTF-8",
        # Nuke common proxy vars to reduce accidental network egress
        "http_proxy": "",
        "https_proxy": "",
        "HTTP_PROXY": "",
        "HTTPS_PROXY": "",
        # No user/site customization
        "PYTHONNOUSERSITE": "1",
    }

    try:
        with tempfile.TemporaryDirectory(prefix="sandbox_") as tmp:
            main_path = os.path.join(tmp, "main.py")
            with open(main_path, "w", encoding="utf-8") as fh:
                fh.write(code)

            # Build subprocess args
            cmd = [python_exe, *py_flags, main_path]

            # On POSIX, apply rlimits via preexec_fn
            preexec = (
                lambda: _posix_limit_resources(cpu_seconds, mem_mb, file_mb)
                if _is_posix() else None
            )

            proc = subprocess.run(
                cmd,
                cwd=tmp,
                input=None,
                capture_output=True,
                text=True,
                timeout=timeout_s,
                env=env,
                preexec_fn=preexec if _is_posix() else None,
            )

            elapsed = time.time() - start
            ok = (proc.returncode == 0)

            # Map non-zero returns to a coarse exception reason
            if not ok:
                # Signal-based termination (e.g., SIGKILL from RLIMIT_CPU)
                if _is_posix() and proc.returncode < 0:
                    exc_reason = f"signal:{-proc.returncode}"
                else:
                    exc_reason = f"returncode:{proc.returncode}"

            return ExecResult(
                ok=ok,
                stdout=proc.stdout,
                stderr=proc.stderr,
                exception=exc_reason,
                time_s=elapsed,
            )

    except subprocess.TimeoutExpired as e:
        elapsed = time.time() - start
        return ExecResult(
            ok=False,
            stdout=e.stdout or "",
            stderr=e.stderr or "",
            exception="timeout",
            time_s=elapsed,
        )
    except MemoryError:
        elapsed = time.time() - start
        return ExecResult(
            ok=False,
            stdout="",
            stderr="",
            exception="memory_error",
            time_s=elapsed,
        )
    except Exception as e:
        elapsed = time.time() - start
        return ExecResult(
            ok=False,
            stdout="",
            stderr=str(e),
            exception=f"exception:{type(e).__name__}",
            time_s=elapsed,
        )
