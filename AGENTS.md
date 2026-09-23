# Instruções do projeto — API de tarefas colaborativas

## Fonte de verdade

Leia `docs/especificacao.md` e `docs/matriz-aceite.md` antes de editar o produto. A especificação consolida as respostas da autora; não reinicie o questionário de requisitos. O prompt em `PROMPT_CODEX.md` estabelece a tarefa de implementação. Havendo conflito real com uma nova instrução explícita da autora, preserve a instrução nova e registre a mudança.

## Escopo e arquitetura

Python 3.13, FastAPI, PostgreSQL 17, SQLAlchemy 2 síncrono, psycopg 3, Alembic, Pydantic 2, PyJWT, pwdlib/Argon2id, pytest, pytest-cov e Ruff. Gerencie dependências com uv, pyproject.toml e uv.lock. Exatamente os complementares 5, 6 e 8: papéis, comentários e filtros. Somente backend, monólito modular, um ambiente compartilhado.

Domínio independente de bibliotecas externas; aplicação depende apenas do domínio e portas próprias. Não importar ORM/framework nas camadas internas. Rotas sem SQL e sem regras de negócio. Repositórios não fazem commit: UoW controla atomicidade. Mapear explicitamente DTO HTTP, entidade e modelo ORM. Testar as fronteiras arquiteturais.

## Invariantes que não podem ser simplificadas

- Manter os 11 endpoints do professor, inclusive PUT, atribuição e logout real.
- Cadastro público nunca concede admin; papel separado do perfil.
- Toda tarefa e comentário exige autorização do recurso, não só presença de JWT.
- Filtros, totais e paginação respeitam visibilidade no banco.
- Responsável user altera apenas status; PUT completo com outras mudanças proibidas falha por inteiro.
- Guest só lê colaboração; pode cuidar da própria conta e fazer logout.
- Logout revoga sessão persistente; senha e desativação revogam todas as sessões da conta.
- Exclusão lógica não apaga autoria/histórico nem reutiliza e-mail.
- Proteger último admin ativo, inclusive contra concorrência.
- Não deixar tarefa aberta atribuída a usuário desativado após operações concorrentes.
- CompletedAt é controlado pelo servidor e idempotente em PUT repetido.
- Nenhuma senha/token/raw input de validação aparece em erros ou logs.

## Forma de trabalhar

Antes de implementar, inspecione Git, registre um plano executável por etapas em `docs/plano-implementacao.md` e relacione os testes ao aceite. A autora já delegou escolhas técnicas complementares: resolva detalhes não bloqueantes de forma conservadora e documente-os; não amplie o escopo.

Implemente incrementalmente com testes primeiro sempre que viável: cenário que falha, implementação, testes, refatoração. Evite mudanças paralelas em contratos compartilhados. Mantenha `docs/progresso.md` com o que existe, o que foi testado e o próximo ponto de continuidade. Não diga que está pronto se só há um scaffold.

Não interrompa os controles de segurança do ambiente para prosseguir. Operações destrutivas fora de banco de testes, escrita remota e alterações de credenciais exigem as permissões normais. Não modificar arquivos do usuário que não pertencem a esta tarefa.

## Verificações obrigatórias

A suíte completa usa PostgreSQL real isolado. Sem SQLite/fallback em memória para integração, sem skip automático por falta de banco. Um modo unitário isolado não comprova integração. Fixtures destrutivas exigem APP_ENV=test, TEST_DATABASE_URL distinta da aplicação e banco com sufixo `_test`.

Cobertura de linhas de todo src/task_api: mínimo 60%, meta 80%. Relatório de branches é complementar, não substitui o gate de linhas. Não excluir arbitrariamente código, apagar testes, enfraquecer asserções ou reduzir limites para obter aprovação. Testar segurança, negativos e transações, não só happy path.

Quando a implementação existir, executar e registrar, ajustando apenas comandos realmente necessários à configuração:

```text
uv sync --locked
uv run ruff check .
uv run ruff format --check .
uv run alembic upgrade head
uv run pytest --cov=src/task_api --cov-report=term-missing --cov-report=xml:artifacts/coverage.xml --cov-report=html:artifacts/htmlcov --cov-report=json:artifacts/coverage-lines.json --cov-fail-under=60
```

Aplicar migrações e testar em ambientes/bancos corretos. Também validar os comandos Docker documentados, banco novo, persistência após reinício, bootstrap-admin e a rejeição de token após logout/reinício.

## Documentação e Git

Documentação em português; código e campos internos em inglês; JSON em camelCase. README, ADRs, ER e fluxos Mermaid, guia Windows/macOS, exemplos, testes medidos e roteiro de demonstração devem corresponder à implementação.

Trabalhar em feat/task-management-api. Em repositório sem commits, é permitido somente um bootstrap local documental em main antes da branch. Não inventar identidade de commit, não usar force-push nem merge automático. Não publicar segredos. Push/PR só quando autorizados e possíveis; ausência de acesso remoto não impede trabalhar no clone local.

## Relato final

Informar arquivos e funcionalidades implementados, comandos executados, códigos de saída, quantidade de testes, cobertura real de linhas e de branches quando medida, revisão de segurança, pendências, ambiente validado e estado do Git. Não afirmar testes, suporte de sistema operacional, push, PR ou deploy sem evidência.
