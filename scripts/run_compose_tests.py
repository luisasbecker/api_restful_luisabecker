"""Run the Docker suite and export reports, preserving a failing pytest exit code."""

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def compose(*args: str, env: dict[str, str] | None = None, check: bool = True) -> int:
    result = subprocess.run(
        ["docker", "compose", "--profile", "test", *args],
        cwd=ROOT,
        env=env,
        check=False,
    )
    if check and result.returncode:
        raise RuntimeError(f"docker compose {args[0]} falhou (código {result.returncode}).")
    return result.returncode


def export_reports(env: dict[str, str] | None = None) -> None:
    destination = ROOT / "artifacts" / "docker"
    destination.mkdir(parents=True, exist_ok=True)
    # A stopped service container exposes the named volume after run --rm exits.
    # create does not start pytest, and cp writes files as the host's current user.
    compose("create", "--no-build", "tests", env=env)
    compose("cp", "tests:/app/artifacts/.", str(destination), env=env)


def run_tests(env: dict[str, str] | None = None) -> int:
    test_code = compose("run", "--build", "--rm", "-T", "tests", env=env, check=False)
    try:
        export_reports(env)
    except (OSError, RuntimeError):
        print(
            "Falha ao exportar relatórios; o volume test_artifacts foi preservado.", file=sys.stderr
        )
        return test_code or 1
    return test_code


def main() -> int:
    try:
        return run_tests(os.environ.copy())
    except OSError:
        print("Não foi possível executar Docker Compose; confira a instalação.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
