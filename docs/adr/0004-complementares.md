# ADR 0004 — Três complementares

**Decisão.** Implementar apenas 5 (papéis), 6 (comentários) e 8 (filtros). Comentários são sub-recursos de tarefa, sem respostas em árvore. Filtros se combinam no SQL com autorização por tarefa.

**Motivo.** Esses recursos demonstram controle de acesso, associação com pai e consulta/paginação sem serviços de terceiros. Métricas, notificações e anexos ampliariam escopo ou dependências.
