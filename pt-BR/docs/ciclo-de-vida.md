> **Proposta histórica de design, não o ciclo de vida da demonstração implementada.** Este documento descreve uma arquitetura genérica anterior (incluindo BindsTo/After e ideias de múltiplas políticas) que não foi implementada no marco experimental concluído. Para comandos reais e comportamento suportado, consulte o [README](../README.md), a [segurança da demonstração](seguranca-da-demonstracao.md) e a [recuperação](recuperacao.md).

# Esboço do ciclo de vida

## Decisões de design do MVP

- Usar `BindsTo=` e `After=` para cada serviço ou socket cadastrado. Omitir `Requisite=` para manter uma única dependência responsável por incluir o gate na transação. Excluir os arquivos de autorização pertencentes ao projeto antes de solicitar paradas emergenciais dos gates. Após o fechamento, verificar gate, membros e jobs pendentes. Interromper explicitamente membros cadastrados ainda ativos, verificar novamente e informar encerramento incompleto.
- Uma ação fixa `RUN+=` do udev enfileira uma reinicialização não bloqueante do worker na adição/remoção USB. Usar `StartLimitIntervalSec=0` para evitar que a limitação de partidas suprima uma varredura posterior. Persistir a primeira ausência, aguardar a tolerância restante e então reexaminar. Durante a aplicação da política, o timer de segurança interno também agenda varreduras periódicas para que um evento udev perdido seja verificado novamente. Escolher o intervalo no notebook. Somente unidades `.service` e `.socket` podem ser cadastradas em uma política.
- Uma política é proprietária de cada unidade. Recusar números de série ausentes ou ambíguos no cadastro. A revogação remove a elegibilidade sem tolerância. Outro dispositivo válido na mesma política pode manter uma autorização existente. `on_present=start` atua somente na transição para autorizado.

Essas decisões são planejadas e não testadas no notebook (`untested`).

## Estados

| Estado | Evidência que o operador deve observar | Comportamento permitido |
| --- | --- | --- |
| S0 instalado | Arquivos instalados, sem monitor habilitado, drop-ins pertencentes ao projeto ou autorizações vigentes. Configuração e snapshots preservados podem existir. | Inerte. A instalação não habilita nem inicia. |
| S1 observando | Observador habilitado, zero unidades cadastradas e zero autorizações vigentes. O timer de segurança interno é opcional em S1. Informar se está habilitado e ativo. | Auditar mudanças. Um snapshot preparado é inerte. |
| S2 aplicando política | O timer de segurança interno deve estar habilitado e ativo durante todo S2. Drop-ins marcados inventariam as unidades cadastradas e concordam com a geração aplicada e as relações efetivas do gerenciador. | Reconciliar apenas políticas habilitadas e verificar resultados. |
| DEGRADED | Artefatos esperados ausentes, estado inconsistente do gerenciador ou falha na verificação de integridade. Pode sobrepor S2 ou transição parcial. | Suspender novas autorizações, excluir arquivos de autorização pertencentes ao projeto, parar os gates e verificar encerramento. Informar exposição não verificada. Um snapshot ausente não estabelece S0. |

**Habilitar.** Estabelecer S1 primeiro. Antes de armar a primeira política, verificar se o timer de segurança interno está habilitado e ativo. Se falhar, permanecer em S1. Validar e preparar uma geração aplicada durável, mantendo a predecessora para inspeção do operador. Recusar cadastros órfãos ou propriedade sobreposta. Sob o bloqueio compartilhado de transição, inspecionar dispositivos presentes, membros ativos e jobs pendentes antes de habilitar. Exigir --allow-stop explícito se habilitar interromperia um membro ativo cujo dispositivo está ausente. Registrar intenção suficiente para retomar mudanças interrompidas. Confirmar as dependências efetivas carregadas antes de informar S2.

**Desabilitar.** Suspender trabalhos concorrentes da política. Remover apenas drop-ins de propriedade verificada, recarregar, verificar desvinculação e jobs pendentes, parar o gate do projeto e limpar sua autorização. Se o gerenciador não confirmar a desvinculação, preservar o diagnóstico e pausar a etapa. Verificar que o membro manteve seu estado anterior. Outras políticas habilitadas permanecem em S2. Remover a última retorna a S1. Desabilitar o monitor só é permitido após desvincular todos os cadastros.

**Recuperação.** Manter duas sessões SSH e o console local disponíveis para futuros testes humanos. A recuperação manual deve funcionar sem Python, o dispositivo USB ou um snapshot legível. O design usa drop-ins marcados para inventariar cadastros. Suspender processos que abrem o gate, desvincular drop-ins verificados, recarregar e verificar relações, desarmar gates e monitoramento, então verificar S0. Com falha do gerenciador, registrar etapas incompletas. Recarregar udev após remover a regra pertencente ao projeto. Preservar configuração, registro e snapshots. Repetir a recuperação em cada ponto de interrupção. O mecanismo dead-man switch foi removido.

**Desinstalar.** Exigir S0 ou recuperação explícita. Remover somente caminhos confinados e pertencentes ao manifesto, preservar dados do operador por padrão e manter a purga como escolha destrutiva explícita separada. Comparar somente a árvore gerenciada com a referência inicial e listar dados retidos. Todas as transições, inclusive resgate local e comportamento de inicialização, não foram testadas.

[English](../../docs/lifecycle.md) · [Visão geral do projeto](../README.md)
