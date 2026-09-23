# Plano de implementação executável

Data: 23/09/2026. Fonte: `especificacao.md` e `matriz-aceite.md`.

1. **Base e infraestrutura.** Inicializar Git local, branch de trabalho, projeto `uv`, configuração estrita, entidades/políticas, portas e adaptadores SQLAlchemy. Criar migração Alembic para as quatro tabelas. Testar imports entre camadas, invariantes e rollback. Validar lock e migração em PostgreSQL 17.
2. **Contas e sessões.** Implementar RF01–RF04, RF10–RF11 e AUX01–AUX03 com testes de contrato, autenticação, privacidade, revogação e concorrência do último admin (SEC01–SEC03, SEC09–SEC11, NEG01–NEG04, NEG06).
3. **Tarefas.** Implementar RF05–RF09 com testes de visibilidade e autorização por recurso, PUT integral/atômico, datas, exclusão e corrida de desativação/atribuição (SEC04–SEC08, NEG05, NEG07–NEG09, NEG13).
4. **Comentários e filtros.** Implementar RC06A–C e RC08 com testes de vínculo com pai, guest, filtros combinados, contagem e paginação no banco (NEG10–NEG12, NEG14).
5. **Execução.** Dockerfile, Compose com migração única e banco de testes isolado, CLI explícita, CI. Validar build, banco novo, persistência, bootstrap e token revogado após reinício (NFR02–NFR03, NFR07–NFR11).
6. **Documentação e revisão.** README, ADRs, diagramas, contratos/exemplos, guias Windows/macOS, roteiro. Executar Ruff, suíte integral e cobertura de linhas >=60%; branches em relatório separado. Preencher evidências reais da matriz (NFR01, NFR04–NFR06, DOC01–DOC06, DEL01–DEL02).

Em cada etapa: escrever teste de comportamento, observar falha, implementar o mínimo, executar o teste e refatorar. Se PostgreSQL/Docker/rede não estiverem disponíveis, continuar os arquivos independentes e registrar o bloqueio sem simular integração.
