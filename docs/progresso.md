# Progresso real

Atualização: **23/11/2026**.

## Estado do GitHub conferido

A implementação original foi integrada pela autora à `main` por meio do **PR #1**. A base anterior aos ajustes desta revisão era:

- Commit da `main` antes dos ajustes: `f598a538d959b12df628f90d104e12c923db6d87`.
- Árvore Git: `5b076f94a33cff0ea4f2add1220e78acabaa6817`.
- Branch de origem: `feat/task-management-api`, commit `66a441f4129fdcf8bff263a03e81f20c3e6ac1ef`.
- Os 57 arquivos da árvore após o merge correspondiam integralmente à implementação da branch.
- A [CI da main, execução 45279118209](https://github.com/luisasbecker/api_restful_luisabecker/actions/runs/45279118209), terminou com sucesso: 36 testes e 91,70% de linhas no código anterior aos ajustes deste ciclo.

A descrição histórica de uma `main` somente documental deixou de representar o repositório depois desse merge.

## Ajustes publicados neste ciclo

Foram corrigidos o envelope de erros HTTP, a correlação de logs no erro 500, a desativação do logger durante migrações, a proteção do destino do banco de testes e a duração JWT. `AppError` passou a transportar apenas informação semântica; o adaptador HTTP faz o mapeamento de status.

A CLI ganhou erros controlados, descarte de conexões e testes unitários/de integração. O Docker usa um volume próprio para relatórios, e a CI recebeu um job com construção da imagem, migrações, CLI, smoke HTTP, reinício e suíte na imagem. Os documentos distinguem a validação nativa da execução remota com Docker.

O escopo funcional permanece o estabelecido na especificação: 11 operações obrigatórias e complementares **5, 6 e 8**, além das rotas auxiliares necessárias.

## Verificação dos arquivos corrigidos

Em Linux, Python 3.13.5 e PostgreSQL 17.12 reais:

- Dependências do lock instaladas; Ruff e formatação aprovados.
- Migração em banco novo, reexecução e `alembic check` aprovados.
- **132 testes aprovados**, com **97,53% de linhas** e **85,23% de branches**, em medições separadas.
- CLI com **98,57% de cobertura de linhas automatizada**.
- Smoke HTTP nativo aprovado, incluindo repetição de bootstrap/seed e rejeição do token revogado após reinício real do processo Uvicorn.

Comandos, frações e limites constam em [testes](testes.md). A cobertura anterior do GitHub não foi reutilizada como prova destas alterações.

## Publicação e CI dos ajustes

Os ajustes foram publicados diretamente na `main` em **23/11/2026**, nos commits `d6ff3bb9e44ea2725aef8c9bd26e29ca0c3ccb29` e `272b9d34e6ac5c9ead0214eafa4630f2ff8c43fc`. A versão de código validada pela [CI 45300281204](https://github.com/luisasbecker/api_restful_luisabecker/actions/runs/45300281204) é o segundo commit, cuja árvore é `1b3fcd93578d5e26a2a70a0b8e76859ca94cb197`.

- **Job `test`: aprovado.** Ruff, formatação, migração Alembic e duas execuções de pytest aprovados, com 132 testes em cada execução. Os relatórios confirmam 987/1012 linhas (**97,53%**) e, na medição separada, 150/176 ramificações (**85,23%**).
- **Job `docker`: aprovado.** Build da imagem, inicialização por Compose, migrações, bootstrap/seed idempotentes, permissões, comentários, filtros e logout persistente após reinício verificados por HTTP. A suíte na imagem aprovou 132 testes, com 987/1012 linhas (**97,53%**); esse job não produz medição de ramificações.
- **Relatórios:** artifacts `coverage` e `coverage-docker`, com resultados conferidos. Versões do ambiente e limites estão em [testes](testes.md).

Esta atualização documental registra resultados obtidos após a publicação do código. A evidência de CI pertence ao commit `272b9d34e6ac5c9ead0214eafa4630f2ff8c43fc`, sem atribuí-la a um commit posterior da documentação.

## Entrega e continuidade

O código corrigido está publicado e os jobs `test` e `docker` foram aprovados. Permanecem as seguintes pendências:

1. Validar os ajustes atuais em Windows/macOS, caso esses ambientes sejam utilizados. A revisão nativa e a CI foram executadas em Linux.
2. Gravar e vincular o vídeo de demonstração de até 15 minutos. O roteiro existe; ele não equivale ao vídeo entregue.
3. Conferir o acesso do professor e os demais dados institucionais exigidos para a entrega.

Nenhum deploy público foi realizado.

## Histórico anterior

Em setembro de 2026 foram registrados a implementação local, a validação nativa no Windows e o push inicial autorizado. A [CI 36049791996](https://github.com/luisasbecker/api_restful_luisabecker/actions/runs/36049791996), em `d63a529`, também terminou com sucesso. Esses registros explicam a origem da implementação; o estado atual da `main` e as evidências dos ajustes estão nas seções acima.
