# Contrato HTTP

JSON usa camelCase; IDs são UUID v4 e instantes incluem UTC. Todas as rotas protegidas recebem `Authorization: Bearer <accessToken>`. O Swagger usa HTTP Bearer, pois `/auth/login` recebe JSON `{email,password}`. Campos extras de corpo são rejeitados. Respostas paginadas seguem `{items,total,page,pageSize,totalPages}`.

| Método/rota | Acesso | Resultado principal |
|---|---|---|
| POST `/users` | público | 201, perfil e `Location`; papel inicial `user` |
| GET `/users/{id}` | autenticado | 200, perfil próprio/admin ou `{id,name}` para terceiro |
| PUT `/users/{id}` | próprio/admin | 200; corpo completo `{name,email}` |
| DELETE `/users/{id}` | próprio/admin | 204; desativa conta e sessões |
| POST `/auth/login` | público | 200; `accessToken`, `tokenType`, `expiresIn`, `expiresAt` |
| POST `/auth/logout` | autenticado | 204; revoga a sessão atual |
| POST `/tasks` | user/admin | 201, tarefa pendente e `Location` |
| GET `/tasks/{id}` | criador/responsável/admin | 200; invisível/excluída: 404 |
| GET `/tasks` | autenticado | 200, filtros e paginação com visibilidade no banco |
| PUT `/tasks/{id}` | criador/admin; responsável só status | 200; seis campos editáveis obrigatórios |
| DELETE `/tasks/{id}` | criador/admin | 204; exclusão lógica |
| POST `/tasks/{id}/comments` | user/admin com acesso | 201; `{content}` |
| GET `/tasks/{id}/comments` | autenticado com acesso | 200 paginado |
| DELETE `/tasks/{id}/comments/{commentId}` | autor/admin com acesso | 204 |
| GET `/users` | autenticado | diretório mínimo paginado |
| PUT `/users/{id}/role` | admin | 200; `{role}` |
| PUT `/users/{id}/password` | próprio | 204; `{currentPassword,newPassword}` |
| GET `/health`, `/ready` | público | 200; `/ready` retorna 503 se banco falhar |

`POST /tasks` recebe `title`; opcionais: `description`, `assignedTo`, `priority` (`medium` padrão) e `dueAt`. O status inicial é `pending`. `PUT /tasks/{id}` exige sempre `title`, `description`, `status`, `priority`, `assignedTo`, `dueAt`; campos anuláveis devem aparecer com `null` ao limpar. Um responsável com papel `user` reenviará os cinco demais valores sem alterações para modificar apenas status. A tentativa de mudar status e título simultaneamente retorna 403 sem atualização parcial.

`GET /tasks` aceita `assignedTo`, `status`, `priority`, `dueBefore`, `page` e `pageSize`; filtros combinam por AND. `dueBefore=2026-10-01` exclui tarefas com `dueAt >= 2026-10-01T00:00:00Z` e sem prazo. `page` começa em 1, `pageSize` vai de 1 a 100. Query desconhecida retorna 422. Tarefas usam `createdAt DESC,id`; comentários usam `createdAt ASC,id`; diretório usa `name,id`.

Erros usam `{error:{code,message,details},requestId}` e `X-Request-ID`. Falta/erro de token: 401 com `WWW-Authenticate: Bearer`; permissão negada em recurso visível: 403; recurso ausente, excluído ou tarefa invisível: 404; conflito de e-mail/último admin/reatribuição histórica: 409; dados inválidos: 422. O corpo do erro não inclui o valor recebido nem detalhes internos do banco. Exemplos sem credenciais reais estão em [`examples/api.http`](../examples/api.http).

## Roteamento, falhas inesperadas e correlação

O mesmo envelope também se aplica a rotas inexistentes (**404 / NOT_FOUND**), métodos não permitidos (**405 / METHOD_NOT_ALLOWED**, preservando `Allow`) e falhas inesperadas (**500 / INTERNAL_ERROR**). O servidor gera um UUID próprio para cada requisição; não reutiliza um `X-Request-ID` recebido do cliente. O valor em `requestId` é igual ao cabeçalho da resposta e ao identificador registrado nos logs, inclusive no erro 500.

Cada requisição gera `http_request`, com método, modelo da rota, status, duração e usuário quando disponível. Uma falha inesperada gera também `unexpected_error`, com o tipo da exceção e a localização no código: nome do arquivo, função e linha. Mensagem original da exceção, valores de entrada, traceback textual, código-fonte, variáveis locais, SQL e credenciais não são incluídos. Uma URL sem rota correspondente aparece como `unmatched` no log, sem copiar o caminho fornecido pelo cliente.

Os erros semânticos da aplicação são convertidos em HTTP na composição da API. A CLI apresenta mensagens controladas e encerra com código diferente de zero em caso de erro, sem imprimir detalhes de validação ou conexão que possam conter segredos.
