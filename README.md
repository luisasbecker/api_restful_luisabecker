# API de Gestão de Tarefas Colaborativas

Backend acadêmico em Python 3.13/FastAPI e PostgreSQL 17. Implementa as 11 operações obrigatórias de usuários, autenticação e tarefas, com exatamente três complementares: **papéis**, **comentários** e **filtros**. Não há frontend nem serviços externos. O mesmo banco atende todos os usuários; cada tarefa é visível apenas a criador, responsável ou administrador.

## Início rápido com Docker Compose

1. Copie `.env.example` para `.env` e substitua todas as senhas e `JWT_SECRET` por valores aleatórios. Não versione `.env`. O segredo JWT precisa ter pelo menos 32 bytes e não pode manter o prefixo `replace-`.
2. Execute `docker compose up --build -d api`. Isso inicia o PostgreSQL persistente, aplica a migração com o serviço `migrate` e inicia a API quando o banco estiver pronto.
3. Execute `docker compose run --rm -it api python -m task_api.presentation.cli bootstrap-admin`; a senha será solicitada sem eco caso `BOOTSTRAP_PASSWORD` não esteja no ambiente.
4. Abra `http://127.0.0.1:8000/docs`. Use `POST /auth/login` com JSON, copie `accessToken` e cole em **Authorize** no esquema HTTP Bearer. O ReDoc fica em `/redoc`.

Para dados de demonstração, execute explicitamente `docker compose run --rm -it api python -m task_api.presentation.cli seed-demo`. Defina `DEMO_PASSWORD` no ambiente do processo ou digite no prompt oculto. O seed não redefine contas preexistentes.

## Testes

Com `.env` configurado, `docker compose --profile test run --rm tests` executa a suíte com um serviço `test-db` e volume próprios. A fixture exige `APP_ENV=test`, URL de teste diferente da aplicação e nome do banco terminado em `_test`. Ausência do banco causa falha. O gate aplica 60% de **linhas** sobre todo `src/task_api`; a medição complementar de branches é separada.

No desenvolvimento nativo: `uv sync --locked`, `uv run alembic upgrade head`, `uv run uvicorn task_api.main:create_app --factory --host 127.0.0.1 --port 8000`. Os comandos completos para PowerShell e macOS constam em [execução](docs/execucao.md). O fluxo detalhado da API está em [contratos](docs/api.md), e o roteiro para apresentação em [demonstração](docs/roteiro-demonstracao.md).

## Estrutura e decisões

`src/task_api/domain` contém entidades e políticas sem dependência externa; `application` orquestra casos de uso por portas; `infrastructure` implementa persistência e segurança; `presentation` contém schemas, rotas e CLI. SQLAlchemy usa uma sessão por unidade de trabalho e Alembic versiona o schema. Leia [arquitetura](docs/arquitetura.md), [modelagem](docs/modelagem.md) e [ADRs](docs/adr/0001-arquitetura.md).

Esta configuração é para entrega e demonstração local. Exposição pública requer HTTPS, limitação de tentativas de login, rotação de segredos, backup e revisão operacional adicional.
