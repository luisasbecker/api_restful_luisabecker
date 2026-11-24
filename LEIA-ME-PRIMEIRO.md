# Comece pelo projeto implementado

Este repositório contém a API de Gestão de Tarefas Colaborativas, com código, migração PostgreSQL, testes automatizados, configuração Docker e documentação. A implementação foi integrada à `main` pelo PR #1 em 23/11/2026, no commit `f598a538d959b12df628f90d104e12c923db6d87`.

O antigo conteúdo deste arquivo orientava a criação inicial da API. Para executar e avaliar a implementação atual, use os documentos abaixo.

| Documento | Finalidade |
|---|---|
| [README](README.md) | Objetivo, arquitetura e início rápido |
| [Execução](docs/execucao.md) | Configuração, Docker, comandos nativos, administrador e demonstração |
| [Contrato HTTP](docs/api.md) | Endpoints, permissões, corpos e erros |
| [Arquitetura](docs/arquitetura.md) e [modelo de dados](docs/modelagem.md) | Decisões, camadas, transações e diagrama do banco |
| [Testes](docs/testes.md) | Estratégia, comandos, resultados medidos e limites |
| [Matriz de aceite](docs/matriz-aceite.md) | Relação entre requisitos, código e testes |
| [Progresso](docs/progresso.md) | Histórico e pendências de validação/entrega |
| [Roteiro](docs/roteiro-demonstracao.md) | Preparação do vídeo de até 15 minutos |

Os três requisitos complementares selecionados são **5 — papéis e permissões**, **6 — comentários em tarefas** e **8 — filtros avançados**. A interface Swagger está em `/docs`; o projeto entrega somente o backend.

`docs/especificacao.md`, `AGENTS.md` e `PROMPT_CODEX.md` registram as decisões e instruções de desenvolvimento. Novas alterações devem preservar os requisitos já implementados e partir do estado atual do código.

Configure os segredos em `.env`, conforme `.env.example`, e mantenha esse arquivo fora do Git. O guia de testes explica o banco isolado e a geração dos relatórios. A situação do vídeo e das verificações Docker/macOS está explicitamente registrada em `docs/progresso.md`; um roteiro não substitui o vídeo final.
