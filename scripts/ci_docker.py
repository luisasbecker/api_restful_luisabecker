"""Exercise the Compose delivery in an isolated GitHub Actions project."""

import json
import os
import secrets
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from run_compose_tests import compose, run_tests

BASE_URL = "http://127.0.0.1:8000"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def request(
    method: str,
    path: str,
    *,
    token: str | None = None,
    body: dict | None = None,
    expected: int = 200,
    json_response: bool = True,
):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = json.dumps(body).encode() if body is not None else None
    outgoing = Request(BASE_URL + path, data=data, headers=headers, method=method)
    try:
        with urlopen(outgoing, timeout=5) as response:
            status, content = response.status, response.read()
    except HTTPError as exc:
        with exc:
            status, content = exc.code, exc.read()
    except (OSError, URLError):
        raise RuntimeError("A API não respondeu ao smoke test.") from None
    # Do not print response bodies: login responses contain live JWTs.
    require(
        status == expected, f"{method} {path.split('?')[0]}: HTTP {status}, esperado {expected}."
    )
    if not content or not json_response:
        return None
    try:
        return json.loads(content)
    except ValueError:
        raise RuntimeError("A API retornou JSON inválido.") from None


def wait_ready() -> None:
    deadline = time.monotonic() + 90
    while time.monotonic() < deadline:
        try:
            request("GET", "/ready")
            return
        except RuntimeError:
            time.sleep(1)
    raise RuntimeError("A API não ficou pronta dentro de 90 segundos.")


def login(email: str, password: str) -> str:
    return request("POST", "/auth/login", body={"email": email, "password": password})[
        "accessToken"
    ]


def run_cli(env: dict[str, str], command: str, secret_name: str) -> None:
    # -e NAME inherits the value; no secret is placed in the command's arguments.
    compose(
        "run",
        "--rm",
        "--no-deps",
        "-T",
        "-e",
        secret_name,
        "api",
        "python",
        "-m",
        "task_api.presentation.cli",
        command,
        env=env,
    )


def prepare_demo(env: dict[str, str]) -> tuple[str, str, str, str]:
    run_cli(env, "bootstrap-admin", "BOOTSTRAP_PASSWORD")
    replacement = secrets.token_urlsafe(36)
    run_cli({**env, "BOOTSTRAP_PASSWORD": replacement}, "bootstrap-admin", "BOOTSTRAP_PASSWORD")
    admin = login(env["BOOTSTRAP_EMAIL"], env["BOOTSTRAP_PASSWORD"])
    request(
        "POST",
        "/auth/login",
        body={"email": env["BOOTSTRAP_EMAIL"], "password": replacement},
        expected=401,
    )
    run_cli(env, "seed-demo", "DEMO_PASSWORD")
    run_cli({**env, "DEMO_PASSWORD": replacement}, "seed-demo", "DEMO_PASSWORD")
    creator = login("demo.creator@example.org", env["DEMO_PASSWORD"])
    assignee = login("demo.assignee@example.org", env["DEMO_PASSWORD"])
    guest = login("demo.guest@example.org", env["DEMO_PASSWORD"])
    request(
        "POST",
        "/auth/login",
        body={"email": "demo.creator@example.org", "password": replacement},
        expected=401,
    )
    return admin, creator, assignee, guest


def smoke_api(env: dict[str, str]) -> None:
    request("GET", "/health")
    request("GET", "/docs", json_response=False)
    request("GET", "/openapi.json")
    admin, creator, assignee, guest = prepare_demo(env)
    users = request("GET", "/users?pageSize=100", token=admin)["items"]
    require(len(users) == 4, "Bootstrap/seed duplicaram contas ou não criaram todas as contas.")
    by_name = {user["name"]: user["id"] for user in users}
    assignee_id = by_name["Demo Responsável"]
    guest_id = by_name["Demo Convidado"]
    require(
        request("GET", f"/users/{guest_id}", token=admin)["role"] == "guest",
        "O seed não preservou o papel de convidado.",
    )
    task = request(
        "POST",
        "/tasks",
        token=creator,
        expected=201,
        body={
            "title": "Smoke Docker",
            "description": "Verificação de entrega",
            "priority": "high",
            "assignedTo": assignee_id,
            "dueAt": "2030-06-01T10:00:00Z",
        },
    )
    path = f"/tasks/{task['id']}"
    request("POST", "/tasks", token=guest, body={"title": "Negada"}, expected=403)
    request("GET", path, token=guest, expected=404)
    editable = {
        key: task[key]
        for key in ("title", "description", "status", "priority", "assignedTo", "dueAt")
    }
    request(
        "PUT",
        path,
        token=assignee,
        body={**editable, "title": "Alteração proibida", "status": "done"},
        expected=403,
    )
    unchanged = request("GET", path, token=creator)
    require(
        unchanged["title"] == editable["title"] and unchanged["status"] == "pending",
        "Um PUT proibido alterou a tarefa parcialmente.",
    )
    completed = request("PUT", path, token=assignee, body={**editable, "status": "done"})
    require(completed["completedAt"] is not None, "Conclusão sem timestamp.")
    comment = request(
        "POST",
        f"{path}/comments",
        token=assignee,
        body={"content": "Smoke de comentário"},
        expected=201,
    )
    comments = request("GET", f"{path}/comments", token=creator)
    require(
        comments["total"] == 1
        and comment["authorId"] == assignee_id
        and bool(comment["createdAt"]),
        "Comentário sem autor/timestamp ou ausente da listagem.",
    )
    query = {
        "assignedTo": assignee_id,
        "status": "done",
        "priority": "high",
        "dueBefore": "2030-06-02",
    }
    filtered = request("GET", "/tasks?" + urlencode(query), token=creator)
    require(
        filtered["total"] == 1 and filtered["items"][0]["id"] == task["id"],
        "Os filtros combinados não localizaram a tarefa esperada.",
    )
    excluded = request("GET", "/tasks?" + urlencode({**query, "priority": "low"}), token=creator)
    require(excluded["total"] == 0, "Os filtros não estão combinados por AND.")
    request("POST", "/auth/logout", token=creator, expected=204)
    request("GET", path, token=creator, expected=401)
    compose("restart", "api", env=env)
    wait_ready()
    request("GET", path, token=creator, expected=401)
    persisted = request("GET", path, token=assignee)
    require(
        persisted["completedAt"] == completed["completedAt"], "Tarefa não persistiu no reinício."
    )
    require(
        request("GET", f"{path}/comments", token=assignee)["total"] == 1,
        "Comentário não persistiu no reinício.",
    )
    request("DELETE", f"{path}/comments/{comment['id']}", token=assignee, expected=204)
    request("DELETE", path, token=admin, expected=204)
    request("GET", path, token=admin, expected=404)
    print("Smoke aprovado: CLI idempotente, permissões, comentários, filtros e logout persistente.")


def ci_environment() -> dict[str, str]:
    require(
        os.environ.get("GITHUB_ACTIONS") == "true", "Este script é exclusivo do job GitHub Actions."
    )
    env = os.environ.copy()
    env.update(
        COMPOSE_PROJECT_NAME="task-api-ci-" + secrets.token_hex(8),
        POSTGRES_USER="task_api_ci",
        POSTGRES_PASSWORD=secrets.token_urlsafe(36),
        POSTGRES_DB="task_api_ci",
        TEST_POSTGRES_USER="task_api_ci_test",
        TEST_POSTGRES_PASSWORD=secrets.token_urlsafe(36),
        TEST_POSTGRES_DB="task_api_ci_test",
        JWT_SECRET=secrets.token_urlsafe(48),
        JWT_ISSUER="task-api",
        JWT_AUDIENCE="task-api-client",
        JWT_MINUTES="30",
        BOOTSTRAP_NAME="Administrador CI",
        BOOTSTRAP_EMAIL="admin.ci@example.org",
        BOOTSTRAP_PASSWORD=secrets.token_urlsafe(36),
        DEMO_PASSWORD=secrets.token_urlsafe(36),
    )
    return env


def main() -> int:
    try:
        env = ci_environment()
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    code = 1
    try:
        print("Docker: build das imagens.", flush=True)
        compose("build", "api", "migrate", "tests", env=env)
        print("Docker: banco, migrações e API.", flush=True)
        compose("up", "-d", "api", env=env)
        wait_ready()
        compose("run", "--rm", "--no-deps", "migrate", env=env)
        print("Docker: bootstrap, seed e smoke HTTP.", flush=True)
        smoke_api(env)
        print("Docker: suíte e exportação de cobertura.", flush=True)
        code = run_tests(env)
    except RuntimeError as exc:
        # These errors are our checks above; they never contain bodies or secrets.
        print(f"Validação Docker falhou: {exc}", file=sys.stderr)
    except (OSError, KeyError, TypeError):
        print(
            "Validação Docker falhou. Confira a última etapa e os relatórios disponíveis.",
            file=sys.stderr,
        )
    finally:
        try:
            cleanup = compose("down", env=env, check=False)
            code = code or cleanup
        except OSError:
            code = code or 1
    return code


if __name__ == "__main__":
    raise SystemExit(main())
