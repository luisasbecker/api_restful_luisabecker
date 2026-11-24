# Execução local e configuração

## Variáveis

Copie `.env.example` para `.env` e substitua as senhas e o segredo JWT. `DATABASE_URL` aponta para o banco da aplicação; `TEST_DATABASE_URL`, para outro banco terminado em `_test`. Para comandos no host use `127.0.0.1` e as portas mapeadas (`5432` aplicação, `5433` teste). Entre contêineres, o Compose usa `db:5432` e `test-db:5432`. O arquivo `.env` é ignorado pelo Git e pelo build Docker.

`JWT_SECRET` requer ao menos 32 bytes; placeholders iniciados por `replace-` são recusados. `JWT_ISSUER` e `JWT_AUDIENCE` têm padrões explícitos. `JWT_MINUTES` é inteiro positivo, com padrão 30; zero e valores negativos são recusados. `BOOTSTRAP_NAME` e `BOOTSTRAP_EMAIL` identificam a conta administrativa inicial; a senha vem de `BOOTSTRAP_PASSWORD` no ambiente do processo ou de prompt oculto. O seed usa `DEMO_PASSWORD` da mesma forma e só roda em development/test.

### URLs e isolamento do banco de testes

As duas URLs devem usar `postgresql+psycopg://`, host explícito e nome de banco de 1–63 caracteres ASCII: letras, números e `_`, iniciado por letra ou `_`. O nome do banco não aceita codificação percentual, barras ou texto de conexão. Isso mantém a identidade verificada igual àquela interpretada pelo SQLAlchemy e enviada ao PostgreSQL.

São permitidas somente as opções de query `sslmode`, `connect_timeout` inteiro positivo e `application_name` não vazio, sem repetição. Opções que substituem o destino, como `host`, `dbname`, `service` e `options`, são recusadas, assim como URLs malformadas, fragmentos e caracteres de controle.

Antes de aplicar migrações ou limpar tabelas de teste, a fixture exige `APP_ENV=test`, nome do banco terminado em `_test` e nome diferente do banco da aplicação. A comparação usa o nome do banco, não apenas o texto das URLs: alterar usuário, senha, host ou porta não libera um banco com o mesmo nome. Por precaução, bancos de servidores diferentes também devem ter nomes diferentes. Mantenha credenciais exclusivas de teste.

### Senhas no Compose e na CLI

O Compose constrói suas URLs com `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB` e as variáveis equivalentes `TEST_POSTGRES_*`. Use nomes simples para os usuários e, nas senhas `POSTGRES_PASSWORD`/`TEST_POSTGRES_PASSWORD`, somente letras, números, `_` e `-`, com comprimento aleatório suficiente. Esses valores são inseridos diretamente na URL e também configuram a senha real do PostgreSQL; não substitua a senha real por sua versão codificada. Ao escrever `DATABASE_URL` e `TEST_DATABASE_URL` manualmente para execução nativa, caracteres reservados em usuário/senha devem ser percent-encoded.

As senhas de usuários da API não estão sujeitas a essa restrição de URL. Os comandos interativos abaixo usam entrada oculta. Para fornecer segredos já definidos no terminal ao contêiner, encaminhe explicitamente a variável, sem inserir seu valor no comando:

```text
docker compose run --rm -e BOOTSTRAP_PASSWORD api python -m task_api.presentation.cli bootstrap-admin
docker compose run --rm -e DEMO_PASSWORD api python -m task_api.presentation.cli seed-demo
```

Uma variável presente no terminal ou em `.env` não é encaminhada automaticamente ao serviço `api` se não estiver declarada no Compose; por isso os exemplos usam `-e`. No processo nativo, a CLI lê ambiente e `.env` normalmente.

## Caminho principal — Docker Compose

```text
docker compose up --build -d api
docker compose ps
docker compose run --rm -it api python -m task_api.presentation.cli bootstrap-admin
docker compose run --rm -it api python -m task_api.presentation.cli seed-demo
```

O `up api` aguarda `db` saudável e `migrate` concluído. Migrações são um serviço de execução única, fora dos workers da API. `/ready` verifica `SELECT 1`; `/health` só indica que o processo responde. O banco de testes usa volume e credenciais próprios. As portas de desenvolvimento ficam mapeadas somente em `127.0.0.1`.

### Testes em contêiner e exportação dos relatórios

Com Python disponível no host, execute na raiz do projeto:

```text
python scripts/run_compose_tests.py
```

No macOS, use `python3 scripts/run_compose_tests.py`. Quem já usa uv pode executar `uv run python scripts/run_compose_tests.py`. O script utiliza apenas a biblioteca padrão: constrói a imagem, executa `tests`, exporta para `artifacts/docker/` e devolve o código de saída dos testes, mesmo se a cópia posterior falhar. Se os testes passarem, mas a exportação falhar, o comando também retorna falha.

O serviço `tests` grava em `/app/artifacts` no volume nomeado `test_artifacts`. A imagem prepara esse diretório para o usuário `app`, UID 10001. A cópia posterior grava os arquivos como o usuário do host; não é necessário conceder permissões amplas ao diretório local nem executar os testes como root.

Alternativa sem Python no host:

```text
docker compose --profile test run --build --rm tests
docker compose --profile test create --no-build tests
docker compose --profile test cp tests:/app/artifacts/. ./artifacts
```

Observe o resultado do primeiro comando: sucesso na cópia não significa aprovação da suíte. `create` prepara um contêiner parado para acessar o volume após o `run --rm`; não executa novamente pytest. Nesta alternativa, os relatórios vão para `artifacts/`; no script, vão para `artifacts/docker/`.

Para encerrar os serviços, use `docker compose --profile test down`. Esse comando preserva os volumes `app_pgdata`, `test_pgdata` e `test_artifacts`. A revisão não exige apagar volumes da aplicação.

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
if ($LASTEXITCODE -ne 0) { throw 'A suíte ou o limite de cobertura falhou.' }
uv run pytest --cov=src/task_api --cov-branch --cov-report=json:artifacts/coverage-branches.json
```

O arquivo `.env` é lido pela aplicação, CLI, Alembic e fixture pytest. Valem as salvaguardas da seção de isolamento: URLs distintas por texto não bastam quando apontam para bancos com o mesmo nome. Encerre esse terminal de testes ao terminar, ou remova o override com `Remove-Item Env:APP_ENV` antes de reutilizá-lo como ambiente de desenvolvimento.

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
```

Em outro terminal, execute:

```bash
APP_ENV=test uv run pytest --cov=src/task_api --cov-report=term-missing --cov-report=xml:artifacts/coverage.xml --cov-report=html:artifacts/htmlcov --cov-report=json:artifacts/coverage-lines.json --cov-fail-under=60
```

Não é necessário Make ou WSL. O macOS Apple Silicon não tem plataforma amd64 fixada no Compose; a execução nele ainda precisa ser testada.

## Estado de validação

Em 23/11/2026, os ajustes foram validados nativamente em Linux com Python 3.13.5, PostgreSQL 17.12 real e dependências do lockfile instaladas com uv 0.13.9. Passaram os 132 testes, as verificações de Ruff e o smoke HTTP contra Uvicorn, incluindo reinício real do processo e revogação persistente de sessão. O smoke reutilizou o fluxo de `scripts/ci_docker.py` com adaptadores nativos de CLI e reinício.

Docker não estava disponível no ambiente local desta revisão. Após a publicação dos ajustes, a [CI 45300281204](https://github.com/luisasbecker/api_restful_luisabecker/actions/runs/45300281204), no commit `272b9d34e6ac5c9ead0214eafa4630f2ff8c43fc`, aprovou os jobs `test` e `docker`, incluindo construção da imagem e execução por Compose em Linux. Os ajustes atuais não foram executados em Windows/macOS; o registro anterior do Windows é histórico. Consulte [testes](testes.md) para métricas e comandos, e [progresso](progresso.md) para o estado da publicação e as pendências de entrega.

O job `docker` executou `scripts/ci_docker.py` no GitHub Actions, com configuração temporária própria, build, migrações, bootstrap, seed, smoke HTTP, reinício e suíte completa. Foram aprovados 132 testes na imagem e a verificação de persistência dos dados e da revogação de sessão após reiniciar a API. Esse script recusa execução fora do GitHub Actions; para testes locais em Docker, use `scripts/run_compose_tests.py`.

## Diagnóstico e limites

- `uv sync --locked` falha se `pyproject.toml` e `uv.lock` divergirem: execute `uv lock` somente ao atualizar dependências, revise o diff e versione ambos.
- Erro em `/ready`: verifique `docker compose ps`, `docker compose logs db migrate api` e a URL/credenciais; `/health` pode continuar 200 quando o banco está indisponível.
- Teste recusa limpeza: confirme `APP_ENV=test`, nomes de banco distintos, sufixo `_test` e as opções permitidas da URL. Nunca aponte `TEST_DATABASE_URL` para dados da aplicação.
- Relatórios Docker: use o script de testes para exportar `test_artifacts` a `artifacts/docker/`; se a cópia falhar, o volume é preservado e a exportação manual pode ser repetida.
- Logs de requisição: erros 404, 405 e 500 também usam o envelope documentado e `X-Request-ID`; correlacione esse ID com os eventos JSON. Alembic preserva loggers existentes ao executar migrações no mesmo processo.
- 401 após logout/troca de senha é esperado: faça login novamente. JWT não tem refresh token.

Esta entrega é local. Antes de expor à internet, acrescentar HTTPS, limitação de tentativas no login, gestão/rotação de segredos, backups e hardening de infraestrutura. Nenhum deploy público foi implementado.
