# Matriz de requisitos e critérios de aceite

Referência normativa: `docs/especificacao.md`, versão 1.0.
Estado inicial: **nenhum item abaixo foi implementado ou validado por este pacote**. Esta matriz é um plano de verificação, não um relatório de execução.

O Codex deverá conservar os identificadores e preencher evidências depois da implementação: arquivo/caso de uso, teste com nome real, comando/resultado e seção de documentação. Marcar um requisito como concluído exige comportamento e evidência, não apenas existência de um arquivo. Não substituir requisitos por mocks na integração.

## Requisitos obrigatórios e complementares

| ID | Requisito | Evidência objetiva de aceite | Tipo principal |
|---|---|---|---|
| RF01 | POST /users | 201; nome/e-mail/senha válidos; papel user; hash não exposto; extra role rejeitado; e-mail normalizado | HTTP + banco |
| RF02 | GET /users/{id} | Próprio/admin veem perfil; terceiro só id/nome; inexistente/excluído retorna 404 | HTTP |
| RF03 | PUT /users/{id} | Próprio/admin atualizam nome e e-mail; representação incompleta 422; alteração alheia 403; papel/senha rejeitados | HTTP + unitário |
| RF04 | DELETE /users/{id} | 204; conta desativada; histórico preservado; tarefas abertas desatribuídas; sessões revogadas | HTTP + banco |
| RF05 | POST /tasks | 201; criador autenticado; pending; responsável opcional; atribuição a usuário ativo; validação de campos | HTTP + unitário |
| RF06 | GET /tasks/{id} | Criador/responsável/admin leem; outro autenticado recebe 404; excluída retorna 404 | HTTP |
| RF07 | GET /tasks?assignedTo={userId} | Filtra por responsável sem ampliar visibilidade, inclusive no total e páginas | HTTP + banco |
| RF08 | PUT /tasks/{id} | Atualiza os seis campos editáveis; PUT completo; campos do servidor bloqueados; status autorizado por ator | HTTP + unitário |
| RF09 | DELETE /tasks/{id} | Criador/admin excluem logicamente; responsável não criador não exclui; comentários ficam inacessíveis | HTTP + banco |
| RF10 | POST /auth/login | 200 e JWT verificável; erro genérico 401 para senha errada, conta ausente e desativada | HTTP + segurança |
| RF11 | POST /auth/logout | 204 sem corpo; sessão atual revogada; próxima requisição 401; outro token da conta ainda válido | HTTP + banco |
| RC05 | Papéis/permissões | admin, user e guest com matriz aplicada; role atual lida do banco; sem escalada por payload | HTTP + unitário |
| RC06A | Criar comentário | POST aninhado 201; conteúdo validado; autoria/timestamp no servidor; guest proibido | HTTP |
| RC06B | Ler comentários | GET aninhado paginado; somente tarefa visível; ordem estável; excluídos ocultos | HTTP + banco |
| RC06C | Excluir comentário | Autor autorizado/admin; criador da tarefa não ganha exclusão alheia; commentId de outro pai retorna 404 | HTTP + banco |
| RC08 | Filtros avançados | AND entre assignedTo/status/priority/dueBefore; datas limite e fuso; sem vazamento na paginação | HTTP + banco |
| AUX01 | Diretório de usuários | GET /users autenticado, paginado, somente id/nome de ativos | HTTP |
| AUX02 | Gestão de papéis | PUT /users/{id}/role apenas admin; proteção do último admin | HTTP + concorrência |
| AUX03 | Troca de senha | PUT /users/{id}/password apenas próprio, senha atual válida; revoga todas as sessões; novo login funciona | HTTP + banco |
| AUX04 | Saúde e documentação | /health, /ready, /docs, /redoc e /openapi.json acessíveis conforme contrato; ready 503 se banco indisponível | HTTP |

## Segurança, regras de borda e consistência

| ID | Cenário obrigatório | Resultado esperado | Tipo principal |
|---|---|---|---|
| SEC01 | Ausência, assinatura alterada, algoritmo inválido, expiração, audiência/emissor incorretos e claims ausentes | 401; nenhum acesso ao recurso | Segurança parametrizada |
| SEC02 | JWT válido criptograficamente com jti desconhecido/revogado ou conta desativada | 401 | HTTP + banco |
| SEC03 | Revogação após reiniciar/recriar a aplicação usando o mesmo banco | Token revogado continua inválido; persistência não depende de memória | Integração |
| SEC04 | Usuário adivinha UUID de tarefa ou comentário de outra pessoa | 404 e nenhuma modificação/leitura indevida | HTTP |
| SEC05 | Guest é responsável ou criador de registro histórico | Só leitura de colaboração; mudanças/comentários/deleções negados; autocuidado permitido | HTTP |
| SEC06 | Responsável faz PUT mudando status e título simultaneamente | 403; nenhum campo aplicado | HTTP + banco |
| SEC07 | Responsável faz PUT mudando só status e reenviando os outros campos intactos | 200; campos não autorizados preservados | HTTP |
| SEC08 | Query com assignedTo de outro usuário ou vários filtros | Interseção com recursos visíveis; total não revela recursos alheios | HTTP + banco |
| SEC09 | Senha/token enviado em requisição inválida | Segredos ausentes da resposta de validação, logs e traceback exposto | Teste de captura |
| SEC10 | Campos extras de autoria, role, completedAt ou hash | 422; sem mass assignment | HTTP parametrizado |
| SEC11 | Primeiro administrador | Bootstrap explícito, sem segredo fixo, sem promoção silenciosa de conta existente | CLI + banco |
| NEG01 | E-mail duplicado com diferença de caixa/espaço ou após soft delete | 409; unicidade no banco | HTTP + banco |
| NEG02 | Corrida entre dois cadastros do mesmo e-mail | Uma criação; outro conflito 409; banco consistente | Concorrência |
| NEG03 | Exclusão ou rebaixamento do último administrador | 409; preservação do administrador ativo | HTTP + unitário |
| NEG04 | Dois administradores se removem/rebaixam concorrentemente | Pelo menos um administrador permanece; transação rejeitada é revertida | Concorrência PostgreSQL |
| NEG05 | Atribuição e desativação concorrentes do responsável | Não sobra tarefa aberta atribuída a usuário desativado | Concorrência PostgreSQL |
| NEG06 | Falha durante exclusão de usuário | Nenhuma desativação/desatribuição/revogação parcial é confirmada | UoW + banco |
| NEG07 | Conclusão direta, repetição de done e reabertura | completedAt atribuído uma vez; repetição preserva; reabertura limpa | Unitário + HTTP |
| NEG08 | PUT integral idêntico | Estado, completedAt e updatedAt preservados | Unitário + HTTP |
| NEG09 | Reabertura com responsável histórico desativado | 409 até enviar null/usuário ativo; nenhuma alteração parcial | HTTP |
| NEG10 | Limite dueBefore e prazos nulos/com offsets | Comparação exclusiva em UTC; null excluído; offset normalizado | Banco + HTTP |
| NEG11 | Página inválida, pageSize fora do limite, enum/UUID/data inválidos e query desconhecida | 422 consistente | HTTP parametrizado |
| NEG12 | Consulta sem resultados e página além da última | 200; items vazio e metadados corretos | HTTP |
| NEG13 | Desatribuição/reatribuição | Antigo responsável perde leitura salvo criador/admin; comentário antigo não concede acesso | HTTP |
| NEG14 | Exclusão de pai e IDs de comentários cruzados | Todas as operações respeitam acesso ao pai e a associação comment.task_id | HTTP |

## Não funcionais, documentação e reprodução

| ID | Requisito | Critério objetivo | Evidência |
|---|---|---|---|
| NFR01 | Arquitetura | Domínio sem frameworks/ORM; aplicação só domínio/portas; adaptadores mapeiam; rotas sem persistência direta | Testes de imports e revisão de código |
| NFR02 | PostgreSQL/migrações | Alembic cria schema novo com PK/FK/UNIQUE/CHECK/índices; sem create_all como atalho | Testes PostgreSQL e revisão da migração |
| NFR03 | pytest e integração real | Suíte completa com banco dedicado; banco ausente causa falha, não skip/fallback | Saída integral da execução |
| NFR04 | Cobertura | >=60% de linhas de todo src/task_api; meta 80%; ramificações reportadas separadamente | XML, HTML, JSON e comando real |
| NFR05 | Logs/erros | Logs estruturados e requestId; erro coerente por categoria; sem segredos | Captura de logs e testes HTTP |
| NFR06 | OpenAPI | Todos os endpoints, schemas, bearer JWT, status e exemplos; login JSON coerente com Swagger | Inspeção/teste do schema e demonstração |
| NFR07 | Dependências reproduzíveis | pyproject e uv.lock coerentes; sync locked funciona; versões reais registradas | Comando com código de saída zero |
| NFR08 | Docker/execução | Build limpo, banco saudável, migração única, API pronta, persistência em reinício e testes isolados | Logs de comandos e smoke test |
| NFR09 | Windows/macOS | Comandos PowerShell e zsh/bash; sem dependência obrigatória de Make/WSL; distinguir validado de previsto | Guias revisados; execução no SO disponível |
| NFR10 | Proteção do banco de testes | APP_ENV/test URL/sufixo corretos; configuração insegura recusada antes de limpar | Testes das salvaguardas |
| NFR11 | CI | Lint, formatação, migrações, PostgreSQL, testes e gate; artifacts; sem ignorar falhas | Workflow e run real quando executado |
| DOC01 | Visão geral/instalação | README permite entender e iniciar o projeto a partir de clone limpo | Revisão executando comandos |
| DOC02 | Decisões arquiteturais | ADRs explicam escolhas e alternativas sem afirmar padrões ausentes | Correspondência documento/código |
| DOC03 | Modelo de dados | ER Mermaid, tabelas, chaves, constraints e índices iguais às migrações | Revisão cruzada |
| DOC04 | Fluxo de requisições | Diagramas e exemplos corretos, incluindo atualização completa e fluxo de autenticação | Exemplos executados |
| DOC05 | Configuração/deploy | Variáveis, Docker, nativo, bootstrap, seed, preservação de dados e limites de produção | Guia e smoke test |
| DOC06 | Estratégia/métricas | docs/testes.md registra resultados reais, data, versões, comando e commit quando disponível | Relatório apoiado nos artifacts |
| DEL01 | Demonstração colaborativa | Contas distintas, atribuição, restrição, conclusão, comentário, filtro e logout demonstráveis | Roteiro executado |
| DEL02 | Entrega Git | Branch e commits verificáveis; sem segredos, histórico destruído ou merge automático | git status/log/diff e busca por segredos |

## Registro de execução a preencher pelo implementador

Criar uma seção por execução relevante, contendo data, ambiente, comando, código de saída, identificadores desta matriz cobertos, nomes reais dos testes e limitações. As primeiras entradas só podem ser feitas depois dos respectivos comandos. Não preencher percentuais ou quantidade de testes com metas.
