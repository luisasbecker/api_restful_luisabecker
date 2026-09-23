# Como usar este pacote

Preparado para `luisasbecker/api_restful_luisabecker`, em 23/09/2026.

**Este pacote contém especificação e instruções de implementação. Não contém uma API implementada, dependências instaladas, testes executados ou alterações publicadas no GitHub.**

A integração consultada retornou repositório vazio e permissão de leitura sem push. O anexo mencionado na conversa não estava disponível; foi utilizado o enunciado transcrito e todas as respostas da autora. Nenhuma decisão depende de um documento que não foi lido.

## Conteúdo

| Arquivo | Uso |
|---|---|
| AGENTS.md | Instruções permanentes para o agente no repositório |
| docs/especificacao.md | Escopo, stack, arquitetura, contratos, regras de negócio, segurança, dados e entrega |
| docs/matriz-aceite.md | Critérios verificáveis para rastrear requisitos, testes e documentação |
| PROMPT_CODEX.md | Pedido de implementação incremental a copiar para o Codex |
| LEIA-ME-PRIMEIRO.md | Este guia e planejamento de uma semana |

## Preparação

Use o Codex em um ambiente local com acesso ao clone. Windows 11 ou macOS são os ambientes preferenciais. Instale/configure Git, o cliente Codex escolhido e Docker Desktop conforme a documentação oficial de cada produto; Python/uv locais serão necessários apenas para o caminho nativo. Não envie senha do GitHub, personal access token, chave privada ou segredo de aplicação para uma conversa.

Clone o repositório no terminal (PowerShell no Windows ou Terminal no macOS):

```text
git clone https://github.com/luisasbecker/api_restful_luisabecker.git
cd api_restful_luisabecker
```

O aviso de repositório vazio é esperado somente se o remoto continuar sem commits. Não execute clone de novo dentro de um clone existente.

Extraia **o conteúdo** do pacote nessa pasta, preservando os caminhos. AGENTS.md e PROMPT_CODEX.md devem ficar diretamente na raiz; a pasta docs deve ficar ao lado deles, não dentro de uma segunda pasta do mesmo nome do repositório.

Abra essa pasta no Codex. Leia a especificação e o prompt; ao enviar o prompt, esses documentos serão o escopo da implementação solicitada. Copie o trecho entre INÍCIO DO PROMPT e FIM DO PROMPT de PROMPT_CODEX.md, sem as linhas delimitadoras.

O prompt manda o agente primeiro inspecionar Git e registrar um plano, depois implementar incrementalmente. Não exige instalação em máquina virtual nem frontend. Mantenha habilitadas as aprovações de segurança do ambiente para comandos que precisem delas.

## Resultado esperado do Codex

Uma branch `feat/task-management-api` com código, migrações, testes, documentação e configuração de execução. Se o repositório não tiver commits, o agente deve estabelecer uma base documental local antes de criar a branch. A publicação remota depende das credenciais e permissões reais; não é realizada por este pacote e não deve ser presumida.

Os comandos de aplicação, Docker e pytest encontrados na especificação são **contratos para o projeto a ser criado**. Eles não funcionam somente com este pacote documental. Após a implementação, siga o README efetivamente produzido e confira as evidências de execução.

## Organização sugerida da semana

Este é um planejamento para a autora, não uma promessa de execução automática ou de entrega futura.

| Dia | Foco | Evidência esperada |
|---|---|---|
| 1 | Revisar especificação, ambiente, estrutura e migrações | Banco inicial e primeiros testes |
| 2 | Usuários, JWT, sessões e permissões iniciais | Cadastro/login/logout e testes negativos |
| 3 | CRUD de tarefas, atribuição e estados | Fluxo com dois usuários e testes |
| 4 | Papéis completos, comentários e filtros | Três complementares funcionais |
| 5 | Integração, concorrência e segurança | Matriz técnica coberta e cobertura medida |
| 6 | Docker/CI, documentação e diagramas | Execução a partir de ambiente limpo |
| 7 | Revisão, correções finais e demonstração | Suíte final e entrega verificada |

Testes e documentação acompanham o desenvolvimento desde o primeiro dia; os dias finais são de consolidação. Preserve uma margem para erros de ambiente e correções. O critério acadêmico informado é >=60% de cobertura; 80% é meta técnica, não resultado medido.

## Demonstração mínima para conferir

O roteiro implementado deve permitir criar duas contas distintas, fazer login, criar tarefa como uma pessoa, atribuí-la à outra, consultar como responsável, negar acesso de terceiro, concluir, comentar, combinar filtros e fazer logout com invalidação do token. Também deve demonstrar administrador e convidado, soft delete e documentação Swagger.

## Conferência da entrega

Verifique que todos os itens obrigatórios e os complementares 5, 6 e 8 da matriz têm evidências; que o repositório não contém .env, senhas ou tokens; e que o relatório distingue testes executados, ambiente validado e pendências. Não aceite percentuais de cobertura ou resultados de CI sem os respectivos relatórios.
