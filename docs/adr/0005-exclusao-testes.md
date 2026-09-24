# ADR 0005 — Exclusão lógica e testes reais

**Decisão.** `deleted_at` oculta usuários, tarefas e comentários sem destruir autoria. E-mail continua reservado. Testes unitários dispensam banco; testes de integração usam PostgreSQL real, migração Alembic e fixture protegida por ambiente/URL/nome de banco. Cobertura de linhas e branches são medidas em execuções separadas.

**Motivo.** Histórico e revogação exigem persistência. O isolamento evita que uma fixture destrutiva toque no banco da aplicação. Trade-off: a preparação local é mais trabalhosa que um teste SQLite em memória.
