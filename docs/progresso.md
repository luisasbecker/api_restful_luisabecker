# Progresso real

Atualização: **23/11/2026**.

## Estado do GitHub conferido

A implementação foi integrada pela autora à `main` por meio do **PR #1**. A base desta revisão é:

- Commit da `main`: `f598a538d959b12df628f90d104e12c923db6d87`.
- Árvore Git: `5b076f94a33cff0ea4f2add1220e78acabaa6817`.
- Branch de origem: `feat/task-management-api`, commit `66a441f4129fdcf8bff263a03e81f20c3e6ac1ef`.
- Os 57 arquivos da árvore após o merge correspondiam integralmente à implementação da branch.
- A [CI da main, execução 45279118209](https://github.com/luisasbecker/api_restful_luisabecker/actions/runs/45279118209), terminou com sucesso: 36 testes e 91,70% de linhas no código anterior aos ajustes deste ciclo.

A descrição histórica de uma `main` somente documental deixou de representar o repositório depois desse merge.

## Ajustes preparados neste ciclo

Foram corrigidos o envelope de erros HTTP, a correlação de logs no erro 500, a desativação do logger durante migrações, a proteção do destino do banco de testes e a duração JWT. `AppError` passou a transportar apenas informação semântica; o adaptador HTTP faz o mapeamento de status.

A CLI ganhou erros controlados, descarte de conexões e testes unitários/de integração. O Docker usa um volume próprio para relatórios, e a CI recebeu um job com construção da imagem, migrações, CLI, smoke HTTP, reinício e suíte na imagem. Os documentos foram atualizados para refletir a implementação já integrada e distinguir verificações realizadas de configurações ainda não executadas.

O escopo funcional permanece o estabelecido na especificação: 11 operações obrigatórias e complementares **5, 6 e 8**, além das rotas auxiliares necessárias.

## Verificação dos arquivos corrigidos

Em Linux, Python 3.13.5 e PostgreSQL 17.12 reais:

- Dependências do lock instaladas; Ruff e formatação aprovados.
- Migração em banco novo, reexecução e `alembic check` aprovados.
- **132 testes aprovados**, com **97,53% de linhas** e **85,23% de branches**, em medições separadas.
- CLI com **98,57% de cobertura de linhas automatizada**.
- Smoke HTTP nativo aprovado, incluindo repetição de bootstrap/seed e rejeição do token revogado após reinício real do processo Uvicorn.

Comandos, frações e limites constam em [testes](testes.md). A cobertura anterior do GitHub não foi reutilizada como prova destas alterações.

## Entrega e continuidade

Neste ciclo foram preparados arquivos e patch sobre a base exata para a autora aplicar e fazer o commit. Não houve novo commit, push, PR ou merge pelo assistente. Após aplicar o pacote, a autora deve executar os comandos do guia, revisar o diff e publicar o commit; então conferir os jobs `test` e `docker` no GitHub.

Pendências que dependem dessa próxima etapa ou de artefatos da autora:

1. Executar efetivamente o build/Compose e confirmar o novo job Docker; Docker estava indisponível no ambiente desta preparação.
2. Validar o procedimento em macOS, caso esse ambiente seja utilizado. A revisão atual foi executada em Linux.
3. Gravar e vincular o vídeo de demonstração de até 15 minutos. O roteiro existe; ele não equivale ao vídeo entregue.
4. Conferir o acesso do professor e os demais dados institucionais exigidos para a entrega.

Nenhum deploy público foi realizado.

## Histórico anterior

Em setembro de 2026 foram registrados a implementação local, a validação nativa no Windows e o push inicial autorizado. A [CI 36049791996](https://github.com/luisasbecker/api_restful_luisabecker/actions/runs/36049791996), em `d63a529`, também terminou com sucesso. Esses registros explicam a origem da implementação; o estado atual da `main` e as evidências dos ajustes estão nas seções acima.
