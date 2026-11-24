# Estratégia e evidências de testes

## Resultado dos ajustes de 23/11/2026

Esta medição corresponde ao código do pacote de ajustes sobre a `main` em **`f598a538d959b12df628f90d104e12c923db6d87`**, após o merge do PR #1. Os ajustes foram preparados localmente para a autora revisar e fazer o commit; a medição não corresponde a um novo commit ou a uma nova execução remota de CI.

| Medida | Resultado |
|---|---:|
| Testes aprovados na suíte completa | **132** |
| Unitários | 112 |
| Integração com PostgreSQL real | 18 |
| Arquitetura | 2 |
| Linhas/instruções cobertas em todo `src/task_api` | **987 / 1012 = 97,53%** |
| Gate de linhas do enunciado | **60% — aprovado** |
| Ramificações cobertas, em execução separada | **150 / 176 = 85,23%** |
| Linhas da CLI cobertas automaticamente | **69 / 70 = 98,57%** |

O denominador inclui todos os módulos da API, incluindo CLI, infraestrutura, rotas e composição. Não foi introduzida exclusão de arquivos ou redução do gate. Os casos parametrizados contam como testes individuais; a quantidade de testes não substitui a verificação de comportamento.

## Ambiente efetivamente executado

Linux Debian 13, Python **3.13.5**, uv **0.13.9** e PostgreSQL **17.12**. As dependências foram instaladas com o `uv.lock` existente, sem alteração das versões: FastAPI 0.141.1, Starlette 1.7.0, Pydantic 2.13.5, SQLAlchemy 2.0.54, psycopg 3.3.6, Alembic 1.20.0, PyJWT 2.15.0, pwdlib 0.3.1, pytest 9.1.1, coverage 7.16.1 e Ruff 0.16.8.

Foi criado um cluster PostgreSQL temporário com acesso TCP apenas em `127.0.0.1`, autenticação SCRAM e credenciais aleatórias. Aplicação e integração usaram bancos e usuários distintos: `task_api_review` e `task_api_review_test`. As credenciais ficaram fora dos arquivos entregues e do repositório. O banco de testes recebeu as migrações Alembic; a fixture só executou a limpeza depois de validar ambiente, nomes e URLs. Não houve SQLite, fallback em memória ou skip por falta de banco.

## Comandos e resultados atuais

Com o ambiente virtual instalado, foram executados os comandos abaixo. As variáveis da aplicação e do banco de testes foram fornecidas por ambiente; os caminhos absolutos do workspace não fazem parte da configuração do projeto.

| Comando | Saída | Evidência |
|---|---:|---|
| `uv sync --locked --python /usr/bin/python3.13` | 0 | Dependências do lock instaladas |
| `.venv/bin/ruff check .` | 0 | Sem problemas |
| `.venv/bin/ruff format --check .` | 0 | 52 arquivos conformes |
| `.venv/bin/python -m alembic upgrade head` | 0 | Migração inicial aplicada em banco novo |
| Reexecução de `alembic upgrade head` | 0 | Migração idempotente |
| `.venv/bin/python -m alembic check` | 0 | Nenhuma operação nova de upgrade detectada |
| Suíte com cobertura de linhas, comando abaixo | 0 | 132 aprovados; gate de 60% cumprido |
| Suíte com cobertura de branches, comando abaixo | 0 | 132 aprovados; medição complementar |
| Smoke HTTP nativo com Uvicorn e PostgreSQL | 0 | CLI, colaboração e persistência após reinício |
| `git diff --check` | 0 | Sem erros de whitespace nos ajustes |

Comando exato da medição de linhas:

```text
.venv/bin/python -m pytest --cov=src/task_api --cov-report=term-missing --cov-report=xml:artifacts/coverage.xml --cov-report=html:artifacts/htmlcov --cov-report=json:artifacts/coverage-lines.json --cov-fail-under=60 --junitxml=artifacts/junit.xml -q
```

Comando exato da medição separada de ramificações:

```text
.venv/bin/python -m pytest --cov=src/task_api --cov-branch --cov-report=json:artifacts/coverage-branches.json -q
```

No Windows ou em outro ambiente gerenciado por uv, substitua `.venv/bin/python -m` por `uv run` para executar os mesmos módulos instalados. O guia de [execução](execucao.md) detalha a configuração.

A razão de ramificações é `covered_branches / num_branches`. O percentual combinado de linhas e ramificações do segundo JSON não é a cobertura de linhas do enunciado nem a cobertura pura de branches. O gate continua medindo somente linhas.

As duas execuções finais emitiram um aviso de depreciação do uso de HTTPX pelo TestClient na versão fixada de Starlette. O aviso não impediu os testes e não foi ocultado. Não foram alteradas dependências para eliminá-lo.

## Cenários acrescentados e regressões corrigidas

- **HTTP e logs:** 404 e 405 com envelope, preservação de `Allow`, 401 com desafio Bearer mesmo sem cabeçalho explícito, 500 com ID de correlação no cabeçalho/corpo/logs, códigos internos desconhecidos tratados com falha segura, JSON malformado e campos extras sem exposição de valores. O log de exceção inclui tipo, arquivo, função e linha, sem mensagem original ou variáveis locais.
- **Migrações e logging:** a execução de Alembic no processo de testes não desativa mais o logger da API. A suíte completa revelou esse comportamento, que não aparecia na execução apenas unitária. A correção usa `disable_existing_loggers=False`.
- **Configuração:** destino PostgreSQL explícito, nomes distintos apesar de aliases/credenciais diferentes, rejeição de nomes codificados e de parâmetros que possam substituir o destino, validação de opções aceitas e duração JWT positiva.
- **CLI:** entrada oculta/ambiente, validação sanitizada, descarte do engine, seed restrito ao ambiente e administrador ativo. Os testes PostgreSQL confirmam que repetir o bootstrap e o seed preserva IDs, papéis e hashes existentes e que uma conta comum não é promovida silenciosamente.
- **Scripts de entrega:** cinco casos unitários asseguram que exportar relatórios não oculta falhas dos testes e que o script exclusivo de CI recusa execução local antes de iniciar containers. Esses testes dos helpers usam processos simulados; não representam execução Docker.

Os testes anteriores de autorização, privacidade, filtros, sessão persistente, rollback e concorrência foram mantidos. Somente as asserções internas de três cenários foram adaptadas do status HTTP para o código semântico de `AppError`; os resultados HTTP continuam verificados nas rotas.

A rastreabilidade detalhada está em [matriz de aceite](matriz-aceite.md).

## Smoke HTTP e reinício efetivamente executados

O cenário de `scripts/ci_docker.py::smoke_api` foi executado contra Uvicorn e PostgreSQL **nativos**, substituindo apenas os adaptadores de execução da CLI e de reinício do container por subprocessos locais. Foram verificados:

1. `/health`, `/ready`, Swagger e OpenAPI por HTTP real.
2. Bootstrap e seed executados duas vezes; novas senhas fornecidas na repetição não substituíram as credenciais originais.
3. Papéis, atribuição, bloqueio atômico de PUT proibido, conclusão e timestamp.
4. Comentários com autoria/data e filtros combinados.
5. Logout e rejeição imediata do JWT.
6. Encerramento e novo processo Uvicorn usando o mesmo PostgreSQL; o JWT revogado continuou rejeitado, outra sessão permaneceu válida e tarefa/comentário persistiram.
7. Exclusão do comentário e da tarefa.

Essa execução comprova o fluxo nativo e o cenário HTTP reutilizado. **Não comprova build de imagem, montagem de volumes ou inicialização via Docker Compose.**

## Evidências anteriores e CI

As métricas anteriores são preservadas como histórico, sem atribuí-las aos novos ajustes:

| Execução | Código | Testes | Linhas | Branches |
|---|---|---:|---:|---:|
| Registro local Windows, 24/09/2026 | `120129a` | 36 | 848/928 = 91,38% | 96/140 = 68,57% |
| GitHub Actions da main, 23/11/2026 | `f598a538` | 36 | 851/928 = 91,70% | 96/140 = 68,57% |
| Ajustes locais deste documento | Base `f598a538` + arquivos do pacote | 132 | 987/1012 = 97,53% | 150/176 = 85,23% |

A [execução 45279118209](https://github.com/luisasbecker/api_restful_luisabecker/actions/runs/45279118209) da `main` terminou com sucesso. Os logs e o artifact `coverage` dessa execução foram conferidos: instalação, Ruff, migração, testes e gate aprovados. Esse workflow anterior executava somente o job nativo com serviço PostgreSQL; não construía a imagem da API.

O workflow atualizado acrescenta o job `docker`, com build, migração, bootstrap/seed, HTTP, reinício, suíte na imagem e exportação dos relatórios. **O novo job só poderá ser confirmado após o commit/push da autora e uma execução bem-sucedida no GitHub.**

## Relatórios e limites de entrega

A execução gera XML, JSON, HTML e JUnit em `artifacts/`, ignorado pelo Git. O pacote de ajustes inclui uma cópia das evidências em `evidencias/`; elas acompanham a entrega para conferência e não precisam ser adicionadas ao commit. O helper Docker exporta para `artifacts/docker/`.

Docker não estava instalado no ambiente de preparação: build/Compose e o job novo permanecem **não executados**. O guia macOS também não foi executado. O registro antigo do Windows corresponde à versão histórica, sem presumir que valide os novos ajustes nessa plataforma. Não houve ensaio prolongado de carga ou deploy público.

O vídeo demonstrativo de até 15 minutos ainda precisa ser produzido e vinculado à entrega. O [roteiro](roteiro-demonstracao.md) orienta sua gravação.
