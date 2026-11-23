import ast
import sys
from pathlib import Path


def test_inner_layers_do_not_import_framework_or_adapters():
    root = Path(__file__).resolve().parents[2] / "src" / "task_api"
    for layer in ("domain", "application"):
        for path in (root / layer).rglob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            package = ("task_api", *path.relative_to(root).parts[:-1])
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    names = [alias.name for alias in node.names]
                elif isinstance(node, ast.ImportFrom):
                    if node.level:
                        base = package[: len(package) - node.level + 1]
                        names = [".".join((*base, *(node.module or "").split(".")))]
                    else:
                        names = [node.module or ""]
                else:
                    continue
                for name in names:
                    if name.split(".")[0] in sys.stdlib_module_names:
                        continue
                    allowed = (
                        ("task_api.domain",)
                        if layer == "domain"
                        else ("task_api.domain", "task_api.application")
                    )
                    assert any(name == item or name.startswith(item + ".") for item in allowed), (
                        path,
                        name,
                    )


def test_routes_do_not_access_orm_or_sql():
    root = Path(__file__).resolve().parents[2] / "src/task_api"
    for relative in ("presentation/routes.py", "main.py"):
        tree = ast.parse((root / relative).read_text(encoding="utf-8"))
        imported = [node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)]
        assert not any(name.startswith(("sqlalchemy", "psycopg")) for name in imported if name)
        assert not any(
            isinstance(node, ast.Constant)
            and isinstance(node.value, str)
            and "SELECT " in node.value
            for node in ast.walk(tree)
        )
