# Progresso real

Atualizado em 24/09/2026.

- Branch `feat/task-management-api`; base documental `a109734`, implementação `0e0a24e`, correção `120129a` e documentação `d63a529`. Remote `origin` configurado para `https://github.com/luisasbecker/api_restful_luisabecker.git`. Push autorizado de `main` e `feat/task-management-api` executado com código 0; hashes confirmados por `git ls-remote`. Nenhum PR ou merge realizado.
- Existe API funcional com 11 operações obrigatórias, papéis, comentários, filtros, rotas auxiliares, saúde/readiness, CLI e OpenAPI. Domínio/aplicação, portas, adaptadores SQLAlchemy/UoW, JWT/sessão persistente e migração Alembic estão implementados.
- PostgreSQL 17.11 nativo/portátil no Windows validou migração, consultas, rollback, concorrência e smoke HTTP. `uv sync --locked`, Ruff e suíte integral passaram: 36 testes, 91,38% de linhas e 68,57% dos branches em medição separada. Detalhes em `testes.md`.
- Documentação em português: README, arquitetura, ADRs, modelagem Mermaid, contratos/exemplos, execução Windows/macOS e roteiro; matriz ligada a código e testes.
- CI disparada pelo push: [execução 36049791996](https://github.com/luisasbecker/api_restful_luisabecker/actions/runs/36049791996), commit `d63a529`, encerrada com `success`. Dependências, Ruff, migração, testes/gate de linhas, relatório de branches e upload dos artifacts concluídos com sucesso no runner Linux com PostgreSQL 17.
- Verificações pendentes: Docker/Compose indisponível neste host; guia macOS não executado; roteiro completo não apresentado manualmente. Nenhum deploy público realizado.
- Próximo ponto de continuidade: em máquina com Docker, executar `docker compose up --build -d api` a partir de `.env` novo, validar volumes/reinício, `docker compose --profile test run --rm tests` e corrigir qualquer diferença de permissões/ambiente. Não marcar essas etapas como concluídas antes dos logs reais.
