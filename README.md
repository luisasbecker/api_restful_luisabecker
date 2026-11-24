# API de Gestão de Tarefas Colaborativas

Backend acadêmico em Python 3.13/FastAPI e PostgreSQL 17. Implementa as 11 operações obrigatórias de usuários, autenticação e tarefas, com exatamente três complementares: **5 — papéis e permissões**, **6 — comentários em tarefas** e **8 — filtros avançados**. Não há frontend nem serviços externos. O mesmo banco atende todos os usuários; cada tarefa é visível apenas a criador, responsável ou administrador.

## Início rápido com Docker Compose

Pré-requisitos: Git e Docker Engine/Desktop com Compose v2. O build e a execução via Compose foram validados em Linux pelo job `docker` do GitHub Actions; veja as [evidências de testes](docs/testes.md). A validação local desta revisão foi nativa em Linux.

1. Copie `.env.example` para `.env` e substitua todas as senhas e `JWT_SECRET` por valores aleatórios. Nas senhas `POSTGRES_PASSWORD` e `TEST_POSTGRES_PASSWORD`, use somente letras, números, `_` e `-`, pois o Compose as insere diretamente na URL de conexão. Não versione `.env`. O segredo JWT precisa ter pelo menos 32 bytes e não pode manter o prefixo `replace-`; `JWT_MINUTES` deve ser maior ou igual a 1.
2. Execute `docker compose up --build -d api`. Isso inicia o PostgreSQL persistente, aplica a migração com o serviço `migrate` e inicia a API quando o banco estiver pronto.
3. Execute `docker compose run --rm -it api python -m task_api.presentation.cli bootstrap-admin`; a senha será solicitada sem eco. Para transmitir uma variável já definida no terminal, acrescente `-e BOOTSTRAP_PASSWORD` antes de `api`.
4. Abra [Swagger](http://127.0.0.1:8000/docs). Use `POST /auth/login` com JSON, copie `accessToken` e cole em **Authorize** no esquema HTTP Bearer. O [ReDoc](http://127.0.0.1:8000/redoc) também documenta a API.

Para dados de demonstração, execute explicitamente `docker compose run --rm -it api python -m task_api.presentation.cli seed-demo` e digite a senha no prompt oculto. Para usar uma variável já definida no terminal, acrescente `-e DEMO_PASSWORD` antes de `api`. O seed não redefine contas preexistentes.

## Testes

Com `.env` configurado, execute `python scripts/run_compose_tests.py` (`python3` no macOS ou `uv run python` após instalar as dependências). O comando constrói a imagem, executa a suíte com PostgreSQL dedicado e exporta relatórios para `artifacts/docker/`, preservando o código de falha dos testes. O volume `test_artifacts` permite gravar os relatórios como usuário não root, sem depender das permissões de uma pasta montada do host. O [guia de execução](docs/execucao.md) inclui a alternativa que usa somente comandos Docker.

A fixture exige `APP_ENV=test`, banco com nome terminado em `_test` e nome diferente do banco da aplicação, mesmo que as URLs usem hosts ou credenciais diferentes. URLs ambíguas e opções que substituem o destino são rejeitadas. Ausência do banco causa falha. O gate aplica 60% de **linhas** sobre todo `src/task_api`; a medição complementar de branches é separada.

Na revisão local de **23/11/2026**, a suíte passou com **132 testes**, **97,53% de linhas** e **85,23% de ramificações**, usando PostgreSQL 17.12 real em Linux. Também foi verificada a revogação de sessão depois de reiniciar o processo Uvicorn. Após a publicação dos ajustes, a [CI 45300281204](https://github.com/luisasbecker/api_restful_luisabecker/actions/runs/45300281204), no commit `272b9d34e6ac5c9ead0214eafa4630f2ff8c43fc`, aprovou os jobs `test` e `docker`: **132 testes por execução da suíte e 97,53% de linhas em ambos os jobs**. O job `test` também mediu **85,23% de ramificações**; o job `docker` verificou build, Compose, CLI, fluxo HTTP e persistência após reinício. Os comandos, relatórios e limites estão em [testes](docs/testes.md) e [progresso](docs/progresso.md). Os ajustes atuais não foram executados em Windows/macOS. O vídeo de até 15 minutos continua pendente, com [roteiro disponível](docs/roteiro-demonstracao.md).

No desenvolvimento nativo: `uv sync --locked`, `uv run alembic upgrade head`, `uv run uvicorn task_api.main:create_app --factory --host 127.0.0.1 --port 8000`. Os comandos completos para PowerShell e macOS constam em [execução](docs/execucao.md). O fluxo detalhado da API está em [contratos](docs/api.md), e o roteiro para apresentação em [demonstração](docs/roteiro-demonstracao.md).

## Estrutura e decisões

`src/task_api/domain` contém entidades e políticas sem dependência externa; `application` orquestra casos de uso por portas; `infrastructure` implementa persistência e segurança; `presentation` contém schemas, rotas e CLI. SQLAlchemy usa uma sessão por unidade de trabalho e Alembic versiona o schema. Leia [arquitetura](docs/arquitetura.md), [modelagem](docs/modelagem.md) e [ADRs](docs/adr/0001-arquitetura.md).

Esta configuração é para entrega e demonstração local. Exposição pública requer HTTPS, limitação de tentativas de login, rotação de segredos, backup e revisão operacional adicional.
