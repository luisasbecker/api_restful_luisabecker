# ADR 0005 — Exclusão lógica e testes reais

**Decisão.** `deleted_at` oculta usuários, tarefas e comentários sem destruir autoria. E-mail continua reservado. Testes unitários dispensam banco; testes de integração usam PostgreSQL real, migração Alembic e fixture protegida por ambiente/URL/nome de banco. Cobertura de linhas e branches são medidas em execuções separadas.

**Motivo.** Histórico e revogação exigem persistência. O isolamento evita que uma fixture destrutiva toque no banco da aplicação. Trade-off: a preparação local é mais trabalhosa que um teste SQLite em memória.

**Reforço em 23/11/2026.** A comparação de URLs inteiras não identificava conexões ao mesmo banco usando outro usuário ou nome de host. Antes de migrar/limpar testes, o guard exige nomes de banco distintos, mesmo em servidores diferentes, além de `APP_ENV=test` e sufixo `_test`. As URLs exigem host e nome explícitos, driver `postgresql+psycopg` e um conjunto restrito de opções; parâmetros capazes de substituir o destino são recusados. Nomes de banco percent-encoded são recusados para manter a identidade verificada igual à enviada pelo parser SQLAlchemy.

**Concessão.** Essa validação conservadora também recusa bancos distintos em servidores diferentes que compartilhem o mesmo nome e algumas formas válidas de DSN PostgreSQL. Para o ambiente acadêmico, usar nomes explícitos diferentes é simples e reduz o risco de uma fixture executar `TRUNCATE` no destino errado. Credenciais e permissões separadas continuam recomendadas; a salvaguarda não substitui o isolamento do banco.
