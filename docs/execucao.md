# Execução local e configuração

## Variáveis

Copie `.env.example` para `.env` e substitua as senhas e o segredo JWT. `DATABASE_URL` aponta para o banco da aplicação; `TEST_DATABASE_URL`, para outro banco terminado em `_test`. Para comandos no host use `127.0.0.1` e as portas mapeadas (`5432` aplicação, `5433` teste). Entre contêineres, o Compose usa `db:5432` e `test-db:5432`. O arquivo `.env` é ignorado pelo Git e pelo build Docker.

`JWT_SECRET` requer ao menos 32 bytes; placeholders iniciados por `replace-` são recusados. `JWT_ISSUER`, `JWT_AUDIENCE` e `JWT_MINUTES` têm padrões explícitos. `BOOTSTRAP_NAME` e `BOOTSTRAP_EMAIL` identificam a conta administrativa inicial; a senha vem de `BOOTSTRAP_PASSWORD` no ambiente ou de prompt oculto. O seed usa `DEMO_PASSWORD` da mesma forma e só roda em development/test.

## Caminho principal — Docker Compose

```text
docker compose up --build -d api
docker compose ps
docker compose run --rm -it api python -m task_api.presentation.cli bootstrap-admin
docker compose run --rm -it api python -m task_api.presentation.cli seed-demo
docker compose --profile test run --rm tests
docker compose down
```

O `up api` aguarda `db` saudável e `migrate` concluído. Migrações são um serviço de execução única, fora dos workers da API. `/ready` verifica `SELECT 1`; `/health` só indica que o processo responde. `docker compose down` preserva os volumes `app_pgdata` e `test_pgdata`; não use `down -v` se quiser preservar dados. O banco de testes usa volume e credenciais próprios. Exponha somente as portas mapeadas em `127.0.0.1` para desenvolvimento local.

## Windows 11 — uv e banco em Docker

No PowerShell:

```powershell
Copy-Item .env.example .env
# Edite .env e substitua todos os placeholders.
uv python install 3.13
uv sync --locked
docker compose --profile test up -d db test-db
uv run alembic upgrade head
uv run python -m task_api.presentation.cli bootstrap-admin
uv run python -m task_api.presentation.cli seed-demo
uv run uvicorn task_api.main:create_app --factory --host 127.0.0.1 --port 8000
```

Em outro terminal, para a suíte completa:

```powershell
$env:APP_ENV='test'
uv run pytest --cov=src/task_api --cov-report=term-missing --cov-report=xml:artifacts/coverage.xml --cov-report=html:artifacts/htmlcov --cov-report=json:artifacts/coverage-lines.json --cov-fail-under=60
uv run pytest --cov=src/task_api --cov-branch --cov-report=json:artifacts/coverage-branches.json
```

O arquivo `.env` é lido pela aplicação, CLI, Alembic e fixture pytest. A fixture recusa limpeza se `APP_ENV` não for `test`, se as URLs coincidirem ou se o banco de teste não terminar em `_test`.

## macOS — uv e banco em Docker

No zsh/bash (procedimento documentado, ainda não executado em macOS):

```bash
cp .env.example .env
# Edite .env e substitua todos os placeholders.
uv python install 3.13
uv sync --locked
docker compose --profile test up -d db test-db
uv run alembic upgrade head
uv run python -m task_api.presentation.cli bootstrap-admin
uv run python -m task_api.presentation.cli seed-demo
uv run uvicorn task_api.main:create_app --factory --host 127.0.0.1 --port 8000
APP_ENV=test uv run pytest --cov=src/task_api --cov-report=term-missing --cov-report=xml:artifacts/coverage.xml --cov-report=html:artifacts/htmlcov --cov-report=json:artifacts/coverage-lines.json --cov-fail-under=60
```

Não é necessário Make ou WSL. O macOS Apple Silicon não tem plataforma amd64 fixada no Compose; a execução nele ainda precisa ser testada.

## Diagnóstico e limites

- `uv sync --locked` falha se `pyproject.toml` e `uv.lock` divergirem: execute `uv lock` somente ao atualizar dependências, revise o diff e versione ambos.
- Erro em `/ready`: verifique `docker compose ps`, `docker compose logs db migrate api` e a URL/credenciais; `/health` pode continuar 200 quando o banco está indisponível.
- Teste recusa limpeza: confirme `APP_ENV=test`, URL distinta e sufixo `_test`. Nunca aponte `TEST_DATABASE_URL` para dados da aplicação.
- 401 após logout/troca de senha é esperado: faça login novamente. JWT não tem refresh token.

Esta entrega é local. Antes de expor à internet, acrescentar HTTPS, limitação de tentativas no login, gestão/rotação de segredos, backups e hardening de infraestrutura. Nenhum deploy público foi implementado.
