# Roteiro de demonstração

1. Inicie os serviços e confirme `/health`, `/ready`, `/docs` e `/openapi.json`. Execute o bootstrap do admin e o seed explícitos conforme `execucao.md`; não mostre senhas/tokens na gravação.
2. Faça login JSON como criador e cole o token no **Authorize** do Swagger. Consulte `GET /users` para localizar o responsável. Crie uma tarefa com `POST /tasks` e atribua-a; anote o UUID e confirme status `pending`.
3. Faça login como responsável em outra sessão. `GET /tasks/{id}` deve responder 200; uma conta alheia deve receber 404. Envie PUT completo alterando só `status` para `done`, com os outros cinco valores intactos. Repita: `completedAt` e `updatedAt` permanecem iguais.
4. Ainda como responsável, altere `title` junto com `status`: 403 e nenhuma atualização. Como criador, comente na tarefa e mostre `GET /tasks/{id}/comments`. O convidado atribuído pode ler, mas não comentar ou editar.
5. Liste tarefas com `assignedTo`, `status`, `priority` e `dueBefore`; mostre a contagem restrita ao ator. Troque o responsável e confirme que o antigo responsável perde a visibilidade, exceto se também for criador/admin.
6. Execute `POST /auth/logout` e repita uma rota protegida com o mesmo token: 401. Outro login ainda válido da conta permanece utilizável. Reiniciar a aplicação não restaura o token revogado.
7. Mostre `docs/modelagem.md`, `docs/arquitetura.md`, os testes e a medição real em `docs/testes.md`. Não apresente o ambiente como produção pública.
