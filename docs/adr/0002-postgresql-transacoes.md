# ADR 0002 — PostgreSQL e transações

**Decisão.** PostgreSQL 17 é o único banco de integração. Alembic define o schema; a UoW confirma operações inteiras. Advisory lock transacional serializa alterações que podem remover o último admin. Bloqueio de linha do responsável coordena atribuição e desativação.

**Motivo.** Constraints, locks e consultas filtradas no banco são necessários para as invariantes concorrentes. SQLite não oferece evidência equivalente. Trade-off: a suíte integral exige um serviço PostgreSQL acessível.
