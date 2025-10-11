from __future__ import annotations
import os, sys, time, tempfile, subprocess, shutil
from typing import Optional, NamedTuple

class ExecResult(NamedTuple):
    ok: bool
    stdout: str
    stderr: str
    exception: Optional[str]
    time_s: float

def run_python_in_docker(
    code: str,
    timeout_s: int = 2,
    mem_mb: int = 256,
    cpus: float = 1.0,
    image: str = "humaneval-sandbox",
) -> ExecResult:
    start = time.time()
    exc = None

    # Resolve docker binary robustly
    docker_bin = shutil.which("docker")
    if docker_bin is None:
        return ExecResult(False, "", "", "docker_not_found", time.time() - start)

    try:
        with tempfile.TemporaryDirectory(prefix="hb_") as host_tmp:
            script_path = os.path.join(host_tmp, "main.py")
            with open(script_path, "w", encoding="utf-8") as f:
                f.write(code)

            cmd = [
                docker_bin, "run", "--rm",
                "--network", "none",
                "--cpus", str(cpus),
                "--memory", f"{mem_mb}m",
                "--pids-limit", "128",
                "--ulimit", "nofile=256:256",
                "--read-only",
                "--tmpfs", "/tmp:rw,noexec,nosuid,size=16m",
                "--cap-drop", "ALL",
                "--security-opt", "no-new-privileges",
                "-v", f"{host_tmp}:/work:ro",
                "-w", "/work",
                image,
                "python", "-I", "-B", "-S", "/work/main.py",
            ]

            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout_s,
                env={"PYTHONIOENCODING": "UTF-8", "PYTHONHASHSEED": "0"},
            )

            ok = (proc.returncode == 0)
            if not ok:
                if proc.returncode < 0:
                    exc = f"signal:{-proc.returncode}"
                else:
                    exc = f"returncode:{proc.returncode}"

            return ExecResult(
                ok=ok,
                stdout=proc.stdout,
                stderr=proc.stderr,
                exception=exc,
                time_s=time.time() - start,
            )

    except subprocess.TimeoutExpired as e:
        return ExecResult(False, e.stdout or "", e.stderr or "", "timeout", time.time() - start)
    except Exception as e:
        return ExecResult(False, "", str(e), f"exception:{type(e).__name__}", time.time() - start)
