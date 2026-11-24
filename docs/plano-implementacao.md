# Plano de implementação executável

Data: 23/09/2026. Fonte: `especificacao.md` e `matriz-aceite.md`.

1. **Base e infraestrutura.** Inicializar Git local, branch de trabalho, projeto `uv`, configuração estrita, entidades/políticas, portas e adaptadores SQLAlchemy. Criar migração Alembic para as quatro tabelas. Testar imports entre camadas, invariantes e rollback. Validar lock e migração em PostgreSQL 17.
2. **Contas e sessões.** Implementar RF01–RF04, RF10–RF11 e AUX01–AUX03 com testes de contrato, autenticação, privacidade, revogação e concorrência do último admin (SEC01–SEC03, SEC09–SEC11, NEG01–NEG04, NEG06).
3. **Tarefas.** Implementar RF05–RF09 com testes de visibilidade e autorização por recurso, PUT integral/atômico, datas, exclusão e corrida de desativação/atribuição (SEC04–SEC08, NEG05, NEG07–NEG09, NEG13).
4. **Comentários e filtros.** Implementar RC06A–C e RC08 com testes de vínculo com pai, guest, filtros combinados, contagem e paginação no banco (NEG10–NEG12, NEG14).
5. **Execução.** Dockerfile, Compose com migração única e banco de testes isolado, CLI explícita, CI. Validar build, banco novo, persistência, bootstrap e token revogado após reinício (NFR02–NFR03, NFR07–NFR11).
6. **Documentação e revisão.** README, ADRs, diagramas, contratos/exemplos, guias Windows/macOS, roteiro. Executar Ruff, suíte integral e cobertura de linhas >=60%; branches em relatório separado. Preencher evidências reais da matriz (NFR01, NFR04–NFR06, DOC01–DOC06, DEL01–DEL02).

Em cada etapa: escrever teste de comportamento, observar falha, implementar o mínimo, executar o teste e refatorar. Se PostgreSQL/Docker/rede não estiverem disponíveis, continuar os arquivos independentes e registrar o bloqueio sem simular integração.

## Registro histórico de execução em 24/09/2026

- Etapas 1–4: código, migração e testes PostgreSQL locais executados; rastreabilidade em `matriz-aceite.md`.
- Etapa 5: lock, CLI, Uvicorn nativo e smoke HTTP executados no Windows. Docker/Compose e workflow CI foram escritos, mas não executados porque Docker não está instalado e não houve publicação da branch.
- Etapa 6: documentação e revisão local concluídas; Ruff e gate de linhas/branches executados. A validação em macOS, CI remoto e apresentação manual completa está pendente. Métricas e limites em `testes.md`.

## Ajustes após o merge — 23/11/2026

Base conferida: `main` em `f598a538d959b12df628f90d104e12c923db6d87`, após o merge do PR #1. Este ciclo prepara arquivos para a autora revisar e fazer o commit; não inclui escrita remota.

1. **Contrato HTTP e diagnóstico (NFR01, NFR05, SEC09).** Cobrir 404/405/500, preservar cabeçalhos relevantes, registrar o mesmo request ID em resposta e logs e impedir exposição de mensagens sensíveis. Remover o status HTTP dos erros das camadas internas e traduzi-los na apresentação.
2. **Configuração e proteção de testes (NFR10).** Validar a identidade efetiva do banco, impedir substituição por query string e recusar JWT com duração não positiva. Adicionar regressões para credenciais/hosts alternativos, nomes codificados e configurações malformadas.
3. **CLI e reprodução (SEC11, NFR08, NFR11).** Cobrir bootstrap/seed, falhas sanitizadas e descarte das conexões. Corrigir o destino dos relatórios Docker e adicionar CI com build, migrações, HTTP real, reinício e testes.
4. **Verificação e entrega (NFR03–NFR04, DOC01–DOC06, DEL02).** Executar os comandos possíveis, separar evidências anteriores de medições novas, corrigir os documentos desatualizados e produzir patch/pacote sobre a base exata, sem publicar credenciais.

Resultados e limites deste ciclo são registrados em `testes.md` e `progresso.md`. A existência do novo job Docker não constitui evidência de execução. O vídeo de até 15 minutos continua sendo um artefato de entrega a produzir pela autora.
