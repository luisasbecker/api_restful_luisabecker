# ADR 0003 — JWT com sessão persistente

**Decisão.** Emitir JWT HS256 de duração curta com claims obrigatórias e `jti`, e persistir cada login em `auth_sessions`. Toda rota protegida verifica a assinatura, os claims, a sessão, a conta ativa e o papel atual no banco. Logout revoga somente o jti presente; troca de senha/desativação revogam todos.

**Motivo.** O requisito de logout real e revogação após reinício não é atendido por JWT puramente stateless. Trade-off: cada requisição autenticada lê o banco. Não há refresh token nesta entrega.
