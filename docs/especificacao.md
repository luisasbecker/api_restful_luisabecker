# Especificação — API de Gestão de Tarefas Colaborativas

Versão: 1.0 — 23/09/2026.
Repositório-alvo: `luisasbecker/api_restful_luisabecker`.
Natureza deste arquivo: especificação para implementação; não comprova código, testes ou deploy realizados.

## 1. Contexto, origem e resultado esperado

Trabalho individual de Engenharia de Software — Arquitetura e Padrões, com prazo informado de uma semana. O enunciado transcrito na conversa e as respostas da autora constituem a origem dos requisitos. O anexo mencionado não estava disponível para consulta; não foram presumidas exigências adicionais desse anexo.

Entregar exclusivamente uma API backend em Python e PostgreSQL, com todos os 11 endpoints obrigatórios, exatamente três complementares, arquitetura justificada, testes com pytest, documentação OpenAPI, logs, tratamento de erros e instalação reproduzível em Windows 11 e macOS. Um único ambiente compartilhado de colaboração; não existem organizações, projetos, equipes ou isolamento por locatário no modelo.

Escolhas confirmadas pela autora: Python, PostgreSQL, backend somente, acesso às tarefas por criador/responsável/administrador, cadastro público com papel inicial de usuário, responsável único e opcional, exclusão lógica, logout da sessão atual, UUID, contratos consistentes, pytest e desenvolvimento orientado pelo Codex. As escolhas técnicas e regras de borda abaixo completam as decisões delegadas à análise técnica.

## 2. Complementares escolhidos e limites de escopo

Implementar **5 — Papéis e permissões**, **6 — Comentários em tarefas** e **8 — Filtros avançados**. A combinação favorece demonstração de autorização, sub-recursos, consultas e testes sem credenciais de serviços externos.

Alternativas consideradas: métricas também seriam viáveis, mas há maior ambiguidade entre endpoint analítico, dashboard e relatórios; notificações por log reduziriam esforço, porém acrescentariam menos ao domínio que comentários. Calendários, webhooks e armazenamento externo acrescentariam configuração, credenciais e falhas de terceiros. Não integrar esses recursos nesta entrega.

Fora de escopo: frontend, métricas/dashboard de produtividade, CSV/PDF de relatórios, calendário, Slack/Discord, anexos, e-mail/push, refresh tokens, recuperação de senha, confirmação de e-mail, organizações, microsserviços, mensageria, Redis, Kubernetes e event sourcing. Swagger não é um frontend de produto. Logs técnicos não equivalem ao complementar de notificações de negócio.

## 3. Stack e gestão de dependências

- Python **3.13**, FastAPI, Pydantic 2 e pydantic-settings.
- PostgreSQL **17**, SQLAlchemy 2 em modo síncrono, psycopg 3 com pacote binário e Alembic.
- PyJWT para emissão/validação JWT; pwdlib com Argon2id para senhas.
- pytest, pytest-cov, HTTPX/TestClient e Ruff.
- uv, `pyproject.toml` e `uv.lock` como fonte única de dependências; Docker Compose para aplicação, banco e execução isolada de testes; GitHub Actions para integração contínua.

Python 3.13 e PostgreSQL 17 são escolhas de compatibilidade e escopo, não afirmações de serem as versões mais recentes. Resolver versões estáveis compatíveis dos pacotes no ambiente de implementação, gerar e versionar o lockfile e registrar versões realmente testadas. Não usar versões de desenvolvimento nem declarar compatibilidade não verificada. Não criar simultaneamente outro arquivo de dependências mantido manualmente.

Usar rotas `def` quando realizarem I/O síncrono. Não chamar sessões síncronas diretamente em rotas `async def` que bloqueiem o event loop. Uvicorn serve a aplicação. Não compartilhar uma Session entre requisições concorrentes.

## 4. Arquitetura e padrões

### 4.1 Decisão

Monólito modular com Clean Architecture enxuta. MVC/camadas tradicionais seriam possíveis, mas escolhemos explicitar a independência do domínio. Uma arquitetura distribuída não traz benefício necessário para o escopo acadêmico individual.

Estrutura de referência; evitar arquivos ou classes vazias só para reproduzir a árvore:

```text
src/task_api/
  domain/                 # Entidades, enums, invariantes, políticas e erros próprios
  application/
    ports/                # Interfaces de repositórios, UoW, relógio, senha e tokens
    use_cases/            # Usuários, autenticação, tarefas e comentários
    dto/                  # Objetos simples de entrada/saída, sem framework
  infrastructure/
    persistence/          # Modelos ORM, mapeamento, repositórios e UoW SQLAlchemy
    security/             # Implementações de hash e tokens
    settings.py
    logging.py
  presentation/
    http/                 # Rotas, schemas Pydantic, autenticação e handlers de erro
    cli.py                # Bootstrap de administrador e dados de demonstração
  bootstrap.py            # Composição e injeção das implementações
  main.py                 # Factory e ponto de entrada da aplicação
alembic/
tests/
  unit/
  integration/
  architecture/
docs/
```

Dentro de cada camada, separar responsabilidades de usuários, autenticação, tarefas e comentários. Uma organização equivalente é aceitável se as dependências e os testes arquiteturais mantiverem a regra abaixo; registrar desvios justificados.

### 4.2 Regra de dependência

`domain` usa somente biblioteca padrão. `application` usa domínio e seus próprios contratos; não importa FastAPI, Pydantic, SQLAlchemy, psycopg ou implementações de infraestrutura. Modelos ORM e schemas HTTP não são entidades do domínio. Adaptadores convertem os objetos nas fronteiras. As rotas chamam casos de uso, sem consultas ORM diretas.

Padrões aplicados por necessidade concreta: Repository para persistência; Unit of Work para transações; injeção de dependências para ligar adaptadores; casos de uso/serviços de aplicação para orquestração; DTOs/schemas para fronteiras; políticas explícitas para autorização. Não criar um repositório genérico universal, service locator global, Singleton de sessão ou hierarquias artificiais.

Uma operação de escrita pertence a uma única UoW. Repositórios não executam commit independente. O caso de uso confirma a operação completa; exceções produzem rollback e fechamento da sessão. Exclusão de usuário, desatribuição de tarefas e revogação de sessões devem ser atômicas.

Adicionar testes arquiteturais que inspecionem imports internos e externos, incluindo imports relativos, e impeçam dependências proibidas.

## 5. Convenções HTTP

Rotas do enunciado sem prefixo obrigatório `/api/v1`. Não substituir `PUT` por `PATCH`. JSON em camelCase; código e banco em snake_case. Identificadores UUID v4 gerados no servidor. Todos os instantes têm fuso e são persistidos em UTC; respostas usam ISO 8601 com `Z` ou deslocamento UTC explícito.

Para `PUT`, todos os campos da representação editável daquele recurso são obrigatórios. Campos anuláveis devem ser enviados explicitamente como `null` para limpeza. IDs, autoria, hashes, papel em cadastro, timestamps e dados de sessão nunca são alteráveis por mass assignment. Configurar schemas para rejeitar campos extras.

Criar: 201 e cabeçalho Location quando aplicável. Ler/atualizar/login: 200. Excluir, trocar senha e logout: 204 sem corpo. UUID/formato/validação inválidos: 422. Autenticação ausente, inválida, expirada ou revogada: 401 com `WWW-Authenticate: Bearer`. Recurso visível com ação proibida: 403. Recurso ausente, excluído ou tarefa não visível: 404. E-mail duplicado e violação da proteção do último administrador: 409.

Erros usam envelope consistente, sem dados sensíveis:

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Dados inválidos.",
    "details": [{"field": "title", "reason": "Campo obrigatório."}]
  },
  "requestId": "uuid-gerado-no-servidor"
}
```

`details` pode ser lista vazia. Não copiar o campo `input` nem valores de `ctx` dos erros Pydantic para respostas/logs: podem conter senhas. Erros inesperados retornam mensagem genérica, nunca traceback ou SQL. O servidor gera `X-Request-ID` por requisição e o associa aos logs; não confiar cegamente em um identificador recebido do cliente.

## 6. Endpoints e contratos

### 6.1 Usuários — quatro rotas obrigatórias

**POST /users** — público. Corpo: `name`, `email`, `password`. Nome após trim de 2 a 120 caracteres; e-mail validado, normalizado por trim/lowercase e único inclusive entre excluídos. Senha de 12 a 128 caracteres, sem trim e sem regra artificial de composição. Retorna perfil sem senha/hash e atribui sempre `role=user`. Campo `role` extra é rejeitado, mesmo se um administrador chamar esta rota.

**GET /users/{id}** — autenticado. Próprio usuário ou administrador recebe `{id,name,email,role,createdAt,updatedAt}`. Outros autenticados recebem somente `{id,name}`. Usuário inexistente/desativado retorna 404. OpenAPI deve descrever ambos os formatos, sem expor e-mail por engano.

**PUT /users/{id}** — próprio usuário ou administrador. Corpo completo: `name`, `email`. Não aceita senha ou papel. Retorna perfil atualizado. Convidado pode administrar seu próprio perfil; a restrição de somente leitura aplica-se aos recursos colaborativos, não a autenticação e autocuidado da conta.

**DELETE /users/{id}** — próprio usuário ou administrador. Soft delete e regras da seção 9. Exceção do último administrador retorna 409. Repetição após exclusão retorna 404 quando autenticada por outra conta válida; o próprio token desativado passa a retornar 401.

### 6.2 Autenticação — duas rotas obrigatórias

**POST /auth/login** — público. Corpo JSON `{email,password}`. Resposta `{accessToken,tokenType:"bearer",expiresIn,expiresAt}`. Credenciais incorretas, e-mail inexistente ou conta desativada recebem a mesma mensagem genérica 401. Normalizar e-mail como no cadastro, nunca a senha.

**POST /auth/logout** — autenticado, sem corpo. Revoga apenas a sessão identificada pelo JWT apresentado. Retorna 204; reutilização do mesmo token em qualquer rota protegida, inclusive novo logout, retorna 401. Outro token válido do mesmo usuário continua utilizável.

No OpenAPI usar esquema HTTP bearer JWT compatível com login JSON. Não configurar formulário OAuth2 que prometa aceitar JSON, nem exigir `username` se o contrato é `email`. No Swagger: executar login, copiar `accessToken` e usar Authorize.

### 6.3 Tarefas — cinco rotas obrigatórias

**POST /tasks** — usuário ou administrador. Corpo: `title` obrigatório; `description=null`, `assignedTo=null`, `priority=medium`, `dueAt=null` opcionais. Status inicial sempre `pending`; `createdBy` vem do ator autenticado. Título após trim de 1 a 200 caracteres, descrição de até 5000 caracteres, prioridade `low|medium|high`, responsável único ativo ou null. `dueAt`, quando informado, exige data e hora com offset; prazos no passado são permitidos.

**GET /tasks/{id}** — somente criador, responsável ou administrador. Tarefa excluída/invisível retorna 404. Resposta: `{id,title,description,status,priority,createdBy,assignedTo,dueAt,completedAt,createdAt,updatedAt}`.

**GET /tasks?assignedTo={userId}** — a rota `/tasks` também permite consulta sem filtros e combinação dos filtros da seção 8. Aplica visibilidade antes de contar e paginar; passar o ID de outra pessoa não dá acesso adicional.

**PUT /tasks/{id}** — corpo completo com `title`, `description`, `status`, `priority`, `assignedTo`, `dueAt`. Autorização por diferença entre os valores atuais e os valores normalizados recebidos: criador/admin podem alterar esses campos; responsável com papel user pode alterar somente status, reenviando os demais campos sem mudanças. Se houver uma única alteração proibida, rejeitar tudo com 403; não aplicar parcialmente. Convidado não modifica tarefas mesmo se for criador ou responsável.

**DELETE /tasks/{id}** — criador com papel user ou administrador. Soft delete, sem apagar fisicamente comentários. Tarefa e seus comentários deixam de ser acessíveis pela API normal, inclusive para administrador. Não oferecer restauração nesta entrega.

### 6.4 Rotas dos comentários — complementar 6

**POST /tasks/{id}/comments** — 201; corpo `{content}` com texto simples de 1 a 2000 caracteres após trim. Usuário ou administrador com acesso à tarefa pode comentar. Autor e horário são obtidos no servidor.

**GET /tasks/{id}/comments** — autenticado com acesso à tarefa, inclusive convidado. Paginação da seção 8; ordenação por `createdAt` crescente e ID como desempate. Item `{id,taskId,authorId,content,createdAt}`.

**DELETE /tasks/{id}/comments/{commentId}** — 204; autor com papel user ou administrador, ambos ainda com acesso à tarefa. Outros usuários não podem excluir comentários alheios, nem o criador da tarefa por essa condição isolada. Comentário não associado ao taskId da URL retorna 404. Soft delete. Sem edição, anexos, menções ou respostas aninhadas.

### 6.5 Três rotas auxiliares para tornar as regras utilizáveis

**GET /users** — diretório de usuários ativos para descoberta de IDs na atribuição; qualquer autenticado; retorna somente `{id,name}` por item, nunca e-mail. Paginação; ordenação estável por nome e ID. Esta rota não libera leitura de tarefas alheias.

**PUT /users/{id}/role** — somente administrador; corpo, por exemplo, `{"role":"guest"}`, aceitando somente admin, user ou guest. Retorna perfil. Papel atualizado vale na próxima autorização, pois será consultado no banco. Não permitir que remoções/rebaixamentos concorrentes eliminem o último administrador ativo.

**PUT /users/{id}/password** — somente o próprio usuário, de qualquer papel, com corpo `{currentPassword,newPassword}`. Verificar senha atual; erro de confirmação retorna 403 genérico. Nova senha obedece à política do cadastro. Revogar todas as sessões desse usuário, inclusive a usada nessa requisição, e retornar 204; exigir novo login. Administrador não redefine senha de terceiros por esta rota. Sem recuperação de senha nesta entrega.

Rotas operacionais: **GET /health** para vitalidade e **GET /ready** para conectividade do banco; sem segredos na resposta. Readiness indisponível retorna 503. Swagger `/docs`, ReDoc `/redoc` e `/openapi.json` devem refletir os contratos efetivos.

São 11 operações obrigatórias, 3 de comentários e 3 auxiliares de usuários, além de documentação e saúde. Os filtros e a autorização complementam rotas existentes.

## 7. Papéis, visibilidade e evolução das tarefas

O mesmo ambiente não implica acesso irrestrito. Por tarefa, leitura é `admin OU createdBy=ator OU assignedTo=ator`. Listagens e contagens usam exatamente esse predicado. Não criar membros/ACLs adicionais.

| Ação colaborativa | Admin | User criador | User responsável não criador | Guest com visibilidade |
|---|---|---|---|---|
| Ler tarefa e comentários | Sim | Sim | Sim | Sim |
| Criar tarefa | Sim | Sim | Sim, como nova tarefa própria | Não |
| Editar conteúdo, prioridade e prazo | Sim | Sim | Não | Não |
| Atribuir, reatribuir ou desatribuir | Sim | Sim | Não | Não |
| Alterar status | Sim | Sim | Sim | Não |
| Excluir tarefa | Sim | Sim | Não | Não |
| Comentar | Sim | Sim | Sim | Não |
| Excluir comentário | Qualquer comentário visível | Somente o próprio | Somente o próprio | Não |

Atribuição não eleva papel. Um convidado ativo pode receber uma tarefa para acompanhá-la, mas continua somente leitor; conclusão/edição cabem ao criador ou administrador. Esta é a forma mínima de oferecer leitura restrita a convidados sem introduzir uma tabela de participantes.

Trocar o responsável remove a visibilidade do antigo responsável, a menos que ele também seja criador/admin; a autoria de comentário não concede acesso permanente à tarefa. Sempre verificar acesso ao pai antes de operar comentários.

Estados `pending`, `in_progress`, `done`. São permitidas transições entre quaisquer dois estados diferentes, incluindo conclusão direta e reabertura. Entrada em done registra `completedAt`; saída de done limpa esse campo. Repetir PUT com done preserva a data de conclusão. Repetição integral sem alterações preserva `updatedAt`. Não aceitar completedAt vindo do cliente. A reatribuição isolada não muda o status nem a conclusão.

## 8. Filtros, paginação e datas

`GET /tasks` aceita `assignedTo` (UUID), `status`, `priority`, `dueBefore` (data `YYYY-MM-DD`), `page` e `pageSize`. Filtros combinam-se por AND com a regra de visibilidade. Query parameters desconhecidos devem produzir 422 para evitar erros silenciosos de digitação.

`dueBefore=2026-10-01` significa `due_at < 2026-10-01T00:00:00Z`; limite exclusivo. Tarefas sem prazo não entram nesse filtro. Datas/horas ingênuas no corpo são rejeitadas. Não converter segundo o fuso local da máquina.

`page >= 1`, padrão 1; `pageSize` entre 1 e 100, padrão 20. Resposta paginada `{items,total,page,pageSize,totalPages}`. Sem resultados: items vazio, total 0, totalPages 0. Página além da última retorna items vazio, mantendo total. Não retornar erro por filtros válidos sem correspondência. O filtro assignedTo não precisa confirmar existência do usuário: resultados são a interseção com tarefas visíveis, preservando consulta de históricos.

Tarefas ordenadas por `createdAt` decrescente e `id` como desempate. Não adicionar parâmetro de ordenação livre ou interpolar SQL. Comentários e diretório usam as ordenações fixas já definidas. Aplicar WHERE antes de COUNT, LIMIT e OFFSET. Nunca filtrar apenas em memória depois da paginação.

## 9. Exclusão lógica, integridade e concorrência

`deleted_at` em usuários, tarefas e comentários, inicialmente null. Não apagar o usuário e não reutilizar seu e-mail. Consultas normais ocultam excluídos por padrão, não por um filtro opcional que o cliente possa remover.

Ao excluir usuário, na mesma transação: verificar autorização e proteção do último administrador; desativar conta; revogar todas as sessões; remover assignedTo das tarefas não excluídas e não concluídas que estavam atribuídas a ele, atualizando seus timestamps. Preservar createdBy, comentários e vínculos de tarefas concluídas para histórico. Não deletar tarefas em cascata. Tarefas abertas cujo criador foi removido continuam acessíveis ao responsável atual e ao administrador; sem responsável, continuam administráveis pelo administrador.

Uma atribuição nova ou alterada exige usuário ativo. Tarefa concluída pode manter referência histórica a responsável desativado se assignedTo não mudar. Para reabrir essa tarefa, o criador/admin deve enviar assignedTo null ou um usuário ativo; do contrário retornar 409 e não atualizar nenhum campo.

Exclusão de tarefa mantém dados de comentários no banco, mas todas as rotas de comentários daquele pai retornam 404. Exclusão de comentário não altera tarefa.

Proteger unicidade de e-mail com restrição no banco e traduzir corrida de cadastros para 409. Proteger o último administrador no banco/na transação, não só por `count` fora de seção crítica: usar bloqueio transacional compartilhado por todas as operações de mudança de papel, exclusão de admin e bootstrap (por exemplo, advisory transaction lock no adaptador PostgreSQL). Não colocar SQL PostgreSQL no domínio. Testar a corrida entre dois administradores tentando se remover/rebaixar.

Proteger a corrida entre atribuir e desativar usuário, de modo que a conclusão de ambas as transações não deixe tarefa aberta atribuída a usuário desativado. Definir ordem de bloqueios ou outra estratégia transacional e cobri-la por teste de integração. Conflitos detectados devem reverter a operação, não produzir dados parciais.

## 10. Autenticação e segurança

JWT de acesso: duração padrão de 30 minutos, configurável. HS256 fixado pela configuração do servidor, segredo aleatório de pelo menos 32 bytes, sem valor padrão utilizável. Validar assinatura, algoritmo permitido, expiração, emissor, audiência e claims obrigatórias `sub`, `jti`, `iat`, `nbf`, `exp`, `iss`, `aud`. Não aceitar algoritmo declarado pelo token como decisão de confiança. `sub` é UUID do usuário em string; `jti` é UUID único.

Cada login cria uma linha em `auth_sessions`. Não armazenar JWT completo nem senha em claro. Cada requisição protegida valida o token e verifica sessão existente, correspondente ao usuário, não revogada, não expirada, e usuário ativo. Obter papel atual no banco; não depender de um papel antigo no token. Sessão inexistente também torna o token inválido.

Logout marca `revoked_at`; nova requisição usando o token falha inclusive após reiniciar o processo ou em outra instância da API conectada ao mesmo banco. É autenticação JWT com controle persistente de sessão, não uma implementação totalmente stateless. Essa concessão é deliberada para ter logout real sem Redis.

Hash de senha com Argon2id por biblioteca especializada. Preferir configuração recomendada da biblioteca, verificando algoritmo/parâmetros compatíveis com orientação atual da OWASP. Para e-mail inexistente no login, considerar verificação contra hash fictício válido para reduzir diferença de tempo, sem criar conta. Não escrever primitivas criptográficas próprias.

Primeiro administrador via CLI explícita, recebendo nome/e-mail/senha por ambiente ou entrada oculta; nunca pela API pública. Bootstrap não redefine senha nem promove conta existente silenciosamente. Reexecução para o mesmo administrador não altera credenciais. Se já houver um administrador ativo diferente, criação/promoção adicional usa a rota autenticada. Bootstrap e seed não executam automaticamente no startup.

Segredos somente em ambiente; `.env` ignorado no Git e Docker build. `.env.example` contém placeholders reconhecidos como inválidos. Testes usam segredos exclusivamente de teste. Não publicar tokens ou senhas nos exemplos de requisições. CORS desabilitado por padrão, sem wildcard com credenciais.

O alvo é uma entrega acadêmica reproduzível localmente. Não declarar prontidão para produção pública: documentar necessidade de HTTPS, limitação de tentativas de login, gestão/rotação de segredos, backups e hardening antes de exposição externa. Não implementar serviços externos para cumprir essa observação.

## 11. Modelo relacional

| Tabela | Campos principais e integridade |
|---|---|
| users | id UUID PK; name; email normalizado UNIQUE; password_hash; role com CHECK; created_at; updated_at; deleted_at nullable |
| tasks | id UUID PK; title; description nullable; status e priority com CHECK; created_by FK users NOT NULL; assigned_to FK users nullable; due_at/completed_at nullable; created_at; updated_at; deleted_at nullable |
| comments | id UUID PK; task_id FK tasks; author_id FK users; content; created_at; deleted_at nullable |
| auth_sessions | jti UUID PK; user_id FK users; created_at; expires_at; revoked_at nullable |

Instantes em `TIMESTAMP WITH TIME ZONE`. FK de usuários/tarefas sem cascata destrutiva; tamanhos e nulabilidade devem concordar com o contrato. Constraint de consistência entre status e completed_at: done exige data de conclusão; outros estados exigem null. Usar enums Python com colunas textuais e CHECKs nomeados para facilitar migrações; não depender de enum nativo PostgreSQL.

Índices iniciais justificados: unicidade email; filtros e visibilidade de tarefas (created_by, assigned_to, status, priority, due_at, created_at com índices simples/compostos pertinentes, preferencialmente parciais para não excluídas); comentários por task_id/created_at; sessões por user_id e expires_at. Não criar todas as combinações possíveis. Documentar os índices realmente criados.

Alembic é a fonte versionada do schema, inclusive testes de integração. Não usar `Base.metadata.create_all()` como substituição das migrações na execução normal ou nos testes de integração.

## 12. Logs e erros

Logs estruturados em JSON para stdout: instante, nível, evento, requestId, método, rota, status e duração; userId quando disponível. Registrar operações relevantes e falhas de autenticação sem identificadores pessoais desnecessários. Nunca registrar Authorization, senha/hash, JWT, corpo de login, conteúdo dos comentários, DSN com credenciais ou parâmetros SQL sensíveis.

Desabilitar echo SQL e configurar ocultação de parâmetros do SQLAlchemy. Tratamento centralizado de exceções de domínio, autenticação, validação, restrições conhecidas e erros inesperados. Não converter qualquer Exception em 400/200. Transações falhas devem ser revertidas. Testar que respostas e logs não vazam os segredos usados no teste.

## 13. Testes, cobertura e evidências

pytest obrigatório. Testes unitários do domínio/casos de uso/políticas com portas falsas, relógio controlável e sem banco/rede; testes de integração de repositórios, migrações, autenticação e HTTP contra **PostgreSQL real** dedicado; testes arquiteturais das dependências.

O comando padrão da suíte completa falha se o banco de testes estiver indisponível. Não usar SQLite, fallback em memória ou skips automáticos para declarar sucesso de integração. O modo somente unitário pode existir e deve ser nomeado explicitamente; não equivale à validação da API completa.

A configuração exige TEST_DATABASE_URL diferente de DATABASE_URL, APP_ENV=test e banco de nome terminado em `_test` para operações destrutivas de fixture. Usar credenciais isoladas e recusar limpeza quando as salvaguardas não forem satisfeitas. Aplicar migrações em banco novo, isolar cada teste, cobrir rollback e não executar testes dependentes de ordem.

**Mínimo obrigatório de cobertura de linhas: 60% de todo `src/task_api`; meta de trabalho: 80%.** Incluir código não importado no denominador. Não excluir arbitrariamente infraestrutura, rotas, segurança, CLI ou main. Migrações, documentação e testes não integram esse denominador, mas possuem verificações próprias.

Comando de aceite para cobertura de linhas, após existir a implementação:

```text
uv run pytest --cov=src/task_api --cov-report=term-missing --cov-report=xml:artifacts/coverage.xml --cov-report=html:artifacts/htmlcov --cov-report=json:artifacts/coverage-lines.json --cov-fail-under=60
```

Nesse comando não ativar branch coverage na configuração global, pois ela altera o cálculo do percentual agregado. Produzir medição complementar de ramificações em execução separada com `--cov-branch`, relatório próprio e sem confundi-la com a cobertura de linhas exigida. A aprovação de linhas continua obrigatória; relatório adicional não a substitui. Registrar os dois percentuais conforme sua definição.

GitHub Actions executa lint, formatação em modo de checagem, migrações e suíte completa com PostgreSQL, aplica o limite de linhas e publica XML/HTML/JSON como artifacts. Falhas não podem ser ignoradas com continue-on-error. Dependências resolvidas pelo lockfile.

`docs/testes.md` deve conter comando exato, ambiente/versões, data, commit testado quando disponível, total de testes e percentuais **medidos**. Até haver execução, escrever explicitamente “não executado”; jamais inventar métricas. Demonstrar todos os cenários da matriz de aceite.

## 14. Execução, deploy local e documentação final

Caminho principal: Docker Compose com PostgreSQL persistente, serviço de migrações de execução única e API dependente de banco saudável e migrações concluídas. Não gerar tabelas automaticamente nem aplicar migrações concorrentes por worker. Mapear as portas de desenvolvimento para 127.0.0.1 no host; o processo dentro do container pode escutar em 0.0.0.0. Serviços de teste usam banco/volume isolado, nunca o volume da aplicação. Nomear serviços de maneira clara, por exemplo db, migrate, api, test-db e tests.

Caminho alternativo: Python/uv nativos e somente banco em Docker. Documentar PowerShell para Windows 11 e zsh/bash para macOS, incluindo diferenças entre host `localhost` e hostname do banco dentro da rede Compose. Não exigir Make, bash ou WSL para comandos essenciais no Windows. Não fixar plataforma amd64 sem necessidade, para permitir macOS Apple Silicon; registrar o que foi efetivamente testado.

Disponibilizar `.env.example`, Dockerfile sem execução como root, `.dockerignore`, `.gitignore`, configuração de Ruff, pyproject e uv.lock. Documentar aplicação de migrações, bootstrap-admin, seed de demonstração idempotente, execução de testes, limpeza exclusiva de banco de testes, preservação de volume e encerramento sem perda dos dados.

Seed apenas em development/test, mediante comando explícito e senha de demonstração fornecida em ambiente. Não sobrescrever contas/senhas existentes e não inserir credenciais conhecidas no Git. Deve permitir demonstração com administrador, usuários distintos e convidado.

Documentação a produzir no repositório, em português:

- README.md: objetivo, escopo, três complementares, pré-requisitos, instalação, execução, Swagger, testes e visão rápida da arquitetura.
- docs/arquitetura.md: limites das camadas, fluxo de dependências, padrões efetivamente usados, justificativas e trade-offs.
- docs/adr/: decisões curtas sobre arquitetura, PostgreSQL/transações, JWT/sessões, complementares, exclusão e testes; não declarar padrões ausentes no código.
- docs/modelagem.md: diagrama ER em Mermaid, campos, chaves, nulabilidade, constraints e índices realmente implementados.
- docs/api.md e examples/: contratos e exemplos seguros em arquivo `.http`/JSON, login, tarefa, atribuição, atualização completa, conclusão, comentário, filtros e logout; sem tokens reais.
- docs/execucao.md: guias Windows/macOS, Docker e nativo, variáveis, migrações, limitações de deploy e diagnóstico de erros comuns.
- docs/testes.md: estratégia, comandos e evidências reais; docs/roteiro-demonstracao.md para apresentação reproduzível.
- docs/matriz-aceite.md: cada requisito associado ao código, teste e documento, sem marcação fictícia de conclusão.

Diagramas adicionais em Mermaid: componentes/camadas e sequência de criação/atualização de tarefa com autenticação, autorização, UoW e persistência. Não exige exportar PDF institucional, pois isso não foi solicitado.

## 15. Estratégia Git e conclusão

Inspecionar o estado real do repositório antes de agir. Se não houver nenhum commit, criar um commit local mínimo de especificação/documentação em main para estabelecer uma base; então desenvolver na branch `feat/task-management-api`. Se main já existir, preservá-la. Não reescrever histórico, usar force-push ou misturar arquivos não relacionados.

Commits locais pequenos por etapa, com identidade Git já configurada; nunca inventar nome/e-mail para assinar commits. Publicação remota e abertura de pull request somente com credenciais e autorização disponíveis no ambiente; não presumir que a integração de leitura desta conversa possui escrita. Não realizar merge automático. Se não houver permissão de publicação, manter os arquivos locais e indicar comandos restantes com precisão.

Considerar a implementação concluída somente após validar rotas, autorização, três complementares, migrações de banco novo, execução documentada, testes completos com cobertura de linhas >=60%, logs sem vazamentos e documentação coerente. Meta de 80% não substitui cenários críticos. Declarar separadamente: implementado, executado/validado, não verificado e pendente.

## 16. Referências técnicas primárias

As regras de negócio deste documento são decisões do projeto, não prescrições das fontes. Referências consultadas em 23/09/2026, para fundamentar mecanismos e padrões:

1. Robert C. Martin, The Clean Architecture — `https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html`.
2. FastAPI, Security / JWT — `https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/` e `https://fastapi.tiangolo.com/reference/security/`.
3. SQLAlchemy 2, Session Basics — `https://docs.sqlalchemy.org/en/20/orm/session_basics.html`.
4. PostgreSQL, Constraints / Versioning — `https://www.postgresql.org/docs/17/ddl-constraints.html` e `https://www.postgresql.org/support/versioning/`.
5. OWASP, REST Security — `https://cheatsheetseries.owasp.org/cheatsheets/REST_Security_Cheat_Sheet.html`.
6. OWASP, Password Storage — `https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html`.
7. pytest / pytest-cov — `https://docs.pytest.org/en/stable/how-to/fixtures.html` e `https://pytest-cov.readthedocs.io/en/latest/config.html`.
8. uv, Locking and syncing — `https://docs.astral.sh/uv/concepts/projects/sync/`.
9. OpenAI, instruções AGENTS.md — `https://developers.openai.com/codex/guides/agents-md/`.
