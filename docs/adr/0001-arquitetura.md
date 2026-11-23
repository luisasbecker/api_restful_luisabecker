# ADR 0001 — Monólito modular e portas

**Decisão.** Usar domínio puro, casos de uso em `application`, adaptadores em `infrastructure` e entrega HTTP/CLI em `presentation`. Repositórios e UoW são portas; SQLAlchemy as implementa.

**Motivo.** A tarefa acadêmica precisa mostrar fronteiras e padrões sem custo operacional de microsserviços. Uma estrutura tradicional com ORM nas rotas reduziria arquivos, mas dificultaria testar políticas e transações isoladamente. Trade-off: mapeamento explícito adiciona código.
