import importlib.util
import sys
from pathlib import Path
from unittest.mock import Mock

import pytest


@pytest.fixture
def delivery_scripts(monkeypatch):
    scripts = Path(__file__).resolve().parents[2] / "scripts"

    def load(name):
        spec = importlib.util.spec_from_file_location(name, scripts / f"{name}.py")
        module = importlib.util.module_from_spec(spec)
        monkeypatch.setitem(sys.modules, name, module)
        spec.loader.exec_module(module)
        return module

    return load("run_compose_tests"), load("ci_docker")


@pytest.mark.parametrize(
    ("test_code", "export_error", "expected"),
    [
        (0, None, 0),
        (2, None, 2),
        (0, OSError("Export unavailable"), 1),
        (5, RuntimeError("Copy failed"), 5),
    ],
)
def test_report_export_never_hides_a_failed_suite(
    delivery_scripts, monkeypatch, test_code, export_error, expected
):
    runner, _ = delivery_scripts
    monkeypatch.setattr(runner, "compose", Mock(return_value=test_code))
    export = Mock(side_effect=export_error)
    monkeypatch.setattr(runner, "export_reports", export)

    assert runner.run_tests() == expected
    export.assert_called_once_with(None)


def test_docker_ci_refuses_local_execution_before_starting_containers(
    delivery_scripts, monkeypatch, capsys
):
    _, ci = delivery_scripts
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    docker = Mock(side_effect=AssertionError("Docker must not be invoked"))
    monkeypatch.setattr(ci, "compose", docker)

    assert ci.main() == 1
    docker.assert_not_called()
    assert "exclusivo do job GitHub Actions" in capsys.readouterr().err
