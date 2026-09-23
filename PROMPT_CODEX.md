# Prompt de implementação para o Codex

Copie o conteúdo entre as linhas de início e fim abaixo para o Codex, com este pacote já copiado para a raiz do clone. Os documentos referenciados precisam estar presentes; este prompt não substitui a especificação.

--- INÍCIO DO PROMPT ---

Atue como engenheiro de software sênior com foco em arquitetura, padrões, APIs RESTful, segurança e testes em Python.

Implemente a API de Gestão de Tarefas Colaborativas no repositório local correspondente a `luisasbecker/api_restful_luisabecker`. A entrega é acadêmica, individual, somente backend, com prazo de uma semana. Leia integralmente `AGENTS.md`, `docs/especificacao.md` e `docs/matriz-aceite.md`. Adoto esses documentos como especificação deste pedido, incluindo as decisões técnicas e regras de borda neles definidas.

O trabalho inclui código funcional, persistência PostgreSQL, migrações, testes executados, documentação e configuração de execução/CI. Não entregue apenas um plano, scaffold, exemplos soltos ou pseudocódigo. Não reinicie perguntas sobre escolhas já resolvidas. Para detalhe técnico não bloqueante, escolha a solução mais simples que preserve a especificação e documente a decisão. Não amplie o escopo.

## Condições de execução

1. Confirme diretório, Git, branch, remotes e arquivos existentes antes de alterar. Não assuma que o remoto ainda está vazio. Preserve alterações não relacionadas.
2. Se não houver commit, estabeleça uma base local mínima documental em main e depois use `feat/task-management-api`. Se houver base, crie a branch a partir dela. Não invente identidade Git, não use force-push, não apague histórico e não faça merge automático.
3. Registre um plano incremental em `docs/plano-implementacao.md`, com entregáveis e verificações por etapa. Neste pedido, execute o plano após registrá-lo, sem aguardar nova confirmação das escolhas de escopo já expressas; preserve as aprovações obrigatórias de segurança do ambiente.
4. Para cada comportamento, escreva testes, implemente, execute e só então avance/refatore. Mantenha `docs/progresso.md` com estado real e ponto de continuidade. Não descreva ação futura como realizada.
5. Use documentação oficial para resolver compatibilidade. Gere uv.lock com versões estáveis de fato disponíveis. Nunca invente versões, APIs, resultados de testes ou requisitos do professor.
6. Se uma ferramenta de execução não estiver acessível, registre exatamente o bloqueio e as verificações que ficaram pendentes. Continue o trabalho independente possível. Não substitua PostgreSQL por SQLite e não oculte falhas com skip, mock de integração ou continue-on-error.
7. O GitHub desta conversa pode ter apenas leitura. Trabalhe no clone local; push e PR somente com autorização e credenciais efetivas do ambiente. Sem permissão, conclua os arquivos locais e informe como publicá-los, sem afirmar que o remoto foi alterado.

## Escopo imutável

Python 3.13, FastAPI, PostgreSQL 17, SQLAlchemy 2 síncrono, psycopg 3, Alembic, Pydantic 2, PyJWT, pwdlib/Argon2id, pytest/pytest-cov, Ruff, uv e Docker Compose. Clean Architecture enxuta em monólito modular. Domínio e aplicação independentes de framework e ORM, com Repository, Unit of Work e injeção de dependências. Os únicos três complementares são 5 (papéis), 6 (comentários) e 8 (filtros).

Manter os 11 endpoints obrigatórios de usuários, tarefas e autenticação. Implementar comentários aninhados, gestão de papel e senha, diretório mínimo de usuários, saúde/readiness e documentação OpenAPI conforme a especificação. Sem frontend ou integração externa.

## Ordem de implementação e verificações

### Etapa 1 — Fundação e modelo

Criar projeto instalável com src/task_api, dependências/lock, configuração, factory, Ruff, pytest e testes arquiteturais. Escrever modelos de domínio, enums e políticas. Implementar adaptadores SQLAlchemy, UoW e migração de users, tasks, comments e auth_sessions, com constraints e índices justificados. Preparar PostgreSQL de desenvolvimento e testes isolados.

Aceite: migrações em banco novo, configuração validada, rollback testado, dependências das camadas verificadas e testes unitários executando sem banco. Não usar create_all em vez de Alembic na integração.

### Etapa 2 — Usuários, sessões e segurança

Implementar cadastro público user, perfis com projeção mínima para terceiros, edição, diretório, soft delete, bootstrap de admin, gestão de papel e troca de senha. Implementar login JSON e JWT com sessão persistente; logout revoga só o jti atual; senha/desativação revogam todas as sessões. Validar claims, assinatura, conta ativa e papel atual. Concluir erro padronizado e logs sem segredos.

Aceite: RF01–RF04, RF10–RF11, AUX01–AUX03 e testes de autenticação/mass assignment/privacidade pertinentes. Incluir testes de senha/hash e revogação persistente, não apenas expiração.

### Etapa 3 — Tarefas e permissões por recurso

Implementar RF05–RF09, autorização criador/responsável/admin e guest somente leitor. PUT envia os seis campos editáveis, mas responsável user só pode modificar status. Atualização proibida é totalmente revertida. Implementar estados, timestamps, atribuição/desatribuição, soft delete e regras do usuário desativado. Autorizações de tarefa invisível retornam 404; ação proibida em recurso visível retorna 403.

Aceite: criar, atribuir, consultar, alterar, concluir, reabrir e excluir com atores diferentes; completedAt/updatedAt idempotentes em repetição; exclusão do usuário não destrói histórico.

### Etapa 4 — Comentários, filtros e robustez transacional

Implementar RC06 e RC08. Comentários sempre validam acesso e vínculo com a tarefa pai; autor/admin excluem conforme papel atual. Filtros combinados são executados no banco antes da contagem e paginação, com dueBefore exclusivo em UTC. Proteger último admin e corrida atribuição/desativação em transações corretas, sem SQL no domínio.

Aceite: todos os cenários RC, SEC e NEG da matriz. Testar corridas críticas contra PostgreSQL usando conexões/transações independentes. Não basear validação de concorrência apenas em testes sequenciais.

### Etapa 5 — Execução reproduzível e integração contínua

Finalizar Dockerfile, Compose, .env.example, .dockerignore, .gitignore, bootstrap/seed explícitos e GitHub Actions. Migrar uma única vez antes da API, usar healthchecks e ambiente de testes separado. Adicionar comandos nativos para PowerShell e macOS, sem WSL/Make obrigatórios. Nunca expor portas de desenvolvimento desnecessariamente fora de localhost.

Aceite: build, banco novo, migrações, bootstrap, inicialização, Swagger, persistência após reinício e teste isolado. Não afirmar validação em Windows/macOS se a execução ocorreu apenas em Linux; guias podem ser preparados, mas a distinção deve constar no relatório.

### Etapa 6 — Documentação, revisão e entrega

Produzir toda a documentação exigida na especificação: visão geral, arquitetura e ADRs, ER/camadas/sequência em Mermaid, contratos e exemplos .http/JSON seguros, execução/deploy local Windows/macOS, estratégia e métricas reais de testes, rastreabilidade e roteiro de demonstração.

Revisar a implementação contra a matriz, executar Ruff e suíte pytest completa com PostgreSQL real. Cobertura de linhas >=60% de todo src/task_api, meta 80%, sem exclusões artificiais. Relatar ramificações separadamente. Reexecutar verificações após correções finais.

O comando de gate de linhas, com configuração global SEM ativar branches, deve ser equivalente a:

uv run pytest --cov=src/task_api --cov-report=term-missing --cov-report=xml:artifacts/coverage.xml --cov-report=html:artifacts/htmlcov --cov-report=json:artifacts/coverage-lines.json --cov-fail-under=60

Guardar relatório complementar de branches em arquivo distinto. Configurar CI para falhar com teste, lint, migração ou limite de linhas reprovados. Não confundir a métrica combinada de linhas/branches com a cobertura de linhas exigida.

Revise especificamente: vazamento em erros Pydantic; token revogado após restart; guest com autoria histórica; filtros/contagens de tarefas invisíveis; commentId pertencente a outro pai; PUT misturando alterações permitidas e proibidas; último admin em concorrência; exclusão/atribuição em concorrência; credenciais nos exemplos; fixture tentando limpar banco de aplicação.

## Condições de conclusão

Não considerar concluído apenas porque arquivos existem. Entregar os 11 endpoints, os três complementares, regras de segurança, banco/migrações, documentação fiel e execução testada. Até existir medição, cobertura é “não medida”, nunca “80%” por ser meta.

Ao final, responda em português com:
- Arquivos e funcionalidades implementados, arquitetura e padrões realmente presentes.
- Comandos executados e respectivos resultados; quantidade de testes e cobertura real de linhas/branches.
- Ambiente e versões efetivamente validados; verificações não executadas e motivo.
- Passos exatos para iniciar, criar admin, demonstrar a API e executar testes.
- Pendências reais, sem escondê-las nem declarar deploy/produção prontos.
- Branch, commits e estado de publicação; URL de PR somente se de fato criado. Nunca faça merge automaticamente.

--- FIM DO PROMPT ---
