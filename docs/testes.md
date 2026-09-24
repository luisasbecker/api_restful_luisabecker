# Estratégia e evidências de testes

## Ambiente da execução

Executado em 24/09/2026 no Windows NT 10.0.26200.0 (Windows 11), com Python 3.13.13, uv 0.11.6 e PostgreSQL 17.11 portátil. Pacotes relevantes do lock efetivamente instalados: FastAPI 0.141.1, Pydantic 2.13.5, SQLAlchemy 2.0.54, psycopg 3.3.6, Alembic 1.20.0, PyJWT 2.15.0, pwdlib 0.3.1, pytest 9.1.1 e Ruff 0.16.8. Código testado e confirmado no commit local `120129a` (o commit foi criado após a medição, sem alterações de código entre a execução e o commit).

Foram criados dois bancos distintos em uma instância local do PostgreSQL, com contas/credenciais aleatórias separadas: `task_api` e `task_api_test`. O servidor escutou apenas em `127.0.0.1:55432`. As credenciais ficaram em `.local/`, ignorado pelo Git. A fixture aplicou `alembic upgrade head` no banco de teste e executou `TRUNCATE` somente depois de confirmar `APP_ENV=test`, URLs diferentes e sufixo `_test`. Não há SQLite, skip ou fallback de integração.

## Comandos e resultados

| Comando | Código de saída | Resultado |
|---|---:|---|
| `uv python install 3.13` | 0 | Python 3.13.13 instalado |
| `uv lock` | 0 | 44 pacotes resolvidos em lock real |
| `uv sync --locked` | 0 | 44 pacotes conferidos; ambiente coerente |
| `uv run ruff check .` | 0 | Sem problemas |
| `uv run ruff format --check .` | 0 | 47 arquivos formatados |
| `uv run alembic upgrade head` | 0 | Migração `0001_initial` aplicada em banco novo e reexecução idempotente |
| `uv run alembic check` | 0 | Nenhuma operação de upgrade nova detectada |
| `uv run pytest --cov=src/task_api --cov-report=term-missing --cov-report=xml:artifacts/coverage.xml --cov-report=html:artifacts/htmlcov --cov-report=json:artifacts/coverage-lines.json --cov-fail-under=60` | 0 | **36 testes passaram**; **848/928 linhas = 91,38%**; gate 60% cumprido |
| `uv run pytest --cov=src/task_api --cov-branch --cov-report=json:artifacts/coverage-branches.json -q` | 0 | **36 testes passaram**; **96/140 branches = 68,57%** (métrica complementar, sem substituir linhas) |
| Teste de integração isolado sem `APP_ENV`/URLs | 1 esperado | Fixture recusou limpeza; nenhum skip/fallback |
| `docker compose version` | 1 | `docker` não encontrado no PATH; build/Compose não executados |

O gate global de cobertura não ativa branches. O relatório de branches é produzido em execução separada. O JSON de branches também contém uma métrica agregada linhas+branches; **68,57% acima é a razão entre branches cobertos e branches totais**, calculada a partir de `covered_branches/num_branches`. Os artifacts locais são ignorados pelo Git. A execução emitiu uma advertência de depreciação do `TestClient` FastAPI/Starlette com HTTPX; todos os testes passaram.

Também foram executados `bootstrap-admin` e `seed-demo` contra o banco local com senhas aleatórias efêmeras (código 0). A segunda execução de `seed-demo` preservou as contas existentes. Um processo Uvicorn temporário respondeu 200 em `/health`, `/ready`, `/docs` e `/openapi.json` por HTTP real em `127.0.0.1:58080` (código 0); o processo foi encerrado após o smoke test. O teste `test_registration_profile_and_persistent_logout` recria a aplicação com o mesmo PostgreSQL e confirma que o token revogado continua inválido.

## Cobertura de cenários e limites

`tests/unit` cobre política de status/permissão, Argon2id, validação JWT, configuração/segredos e schemas. `tests/architecture` inspeciona imports absolutos/relativos e rotas. `tests/integration` cobre HTTP e transações PostgreSQL reais: privacidade, papel atual, PUT atômico, comentários vinculados ao pai, filtros/contagem, exclusão lógica, revogação, rollback e corridas de cadastro, último admin e atribuição/desativação com conexões independentes. Os nomes exatos estão ligados aos IDs em `matriz-aceite.md`.

O módulo CLI aparece com 0% de linhas automatizadas no relatório, embora tenha sido exercitado manualmente. A meta de 80% global foi superada sem excluir esse módulo. As corridas críticas foram executadas uma vez na suíte local final; não há ensaio prolongado de carga. Docker Compose, macOS e reprodução a partir de clone limpo com Docker **não foram executados** neste ambiente; seus arquivos e comandos existem, mas precisam ser verificados nessas plataformas antes de afirmar suporte completo. Não há deploy público.

## Publicação e CI no GitHub

Em 24/09/2026, após autorização da autora, `git push --atomic -u origin main feat/task-management-api` terminou com código 0. O remoto não tinha branches antes do envio. `git ls-remote` confirmou `main` em `a10973440c754246c69324b284e0791978685fa9` e `feat/task-management-api` em `d63a529e6b3e7aafbefe1aa72d52fc9bae6d02ee`. A base documental permanece em `main`; a implementação está na feature. Nenhum merge ou PR foi realizado.

A [execução de CI 36049791996](https://github.com/luisasbecker/api_restful_luisabecker/actions/runs/36049791996), sobre `d63a529`, foi consultada pela API do GitHub e terminou com `status=completed`, `conclusion=success`. No runner `ubuntu-latest`, com serviço PostgreSQL 17, passaram instalação do Python 3.13, `uv sync --locked`, Ruff check/format, Alembic upgrade, suíte com gate de linhas, suíte separada com branches e upload dos artifacts. Os percentuais acima continuam identificados como medições locais; esta verificação remota confirmou o sucesso das etapas, sem extrair novas métricas dos artifacts. O workflow não executa o build da imagem da aplicação nem o Compose; essas verificações continuam pendentes.
