# Progresso real

Atualizado em 24/09/2026.

- Branch local: `feat/task-management-api`; base documental `a109734`, implementação `0e0a24e` e correção `120129a`. Sem remote configurado, push ou PR.
- Existe API funcional com 11 operações obrigatórias, papéis, comentários, filtros, rotas auxiliares, saúde/readiness, CLI e OpenAPI. Domínio/aplicação, portas, adaptadores SQLAlchemy/UoW, JWT/sessão persistente e migração Alembic estão implementados.
- PostgreSQL 17.11 nativo/portátil no Windows validou migração, consultas, rollback, concorrência e smoke HTTP. `uv sync --locked`, Ruff e suíte integral passaram: 36 testes, 91,38% de linhas e 68,57% dos branches em medição separada. Detalhes em `testes.md`.
- Documentação em português: README, arquitetura, ADRs, modelagem Mermaid, contratos/exemplos, execução Windows/macOS e roteiro; matriz ligada a código e testes.
- Verificações pendentes: Docker/Compose indisponível neste host; workflow CI não executado no GitHub; guia macOS não executado; roteiro completo não apresentado manualmente. Nenhum deploy público ou publicação remota realizada.
- Próximo ponto de continuidade: em máquina com Docker, executar `docker compose up --build -d api` a partir de `.env` novo, validar volumes/reinício, `docker compose --profile test run --rm tests` e corrigir qualquer diferença de permissões/ambiente. Em seguida executar CI na branch publicada, se houver autorização de push. Não marcar essas etapas como concluídas antes dos logs reais.
