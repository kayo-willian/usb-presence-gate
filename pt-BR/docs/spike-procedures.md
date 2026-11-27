# Esboços de experimentos da fase 1

Estes são procedimentos de revisão para futura execução humana. O mantenedor autorizou apenas S1-lite (serviço e socket) e S2-lite (adição, remoção, inicialização com pendrive, reconexão rápida, remoção seguida de silêncio). Este documento preserva os designs originais dos testes. O mantenedor posteriormente descontinuou G1 e os experimentos S3/S4. Os esboços completos abaixo são históricos. Use somente recursos de teste descartáveis, explicitamente nomeados e não críticos. Registre o estado inicial de systemd/udev, duas sessões SSH independentes, rede funcional e console local antes de cada teste. Interrompa o teste se qualquer unidade não relacionada mudar ou se o acesso se deteriorar. Não acione uevents sintéticos em todo o sistema nem altere a autenticação do host. Organize observações de inicialização em uma janela de manutenção autorizada separadamente.

Para cada caso, cole a data, comando exato, saída bruta sanitizada, kernel, versões systemd/udev e rótulo fictício do dispositivo testado. Inclua estado desejado, timestamps monotônicos, jobs do gerenciador, status de saída, estado final real, verificações SSH/rede e limpeza dos recursos de teste. Preserve temporização e relações entre unidades ao sanitizar identificadores. Um caso omitido permanece não testado.

## S1 — Semântica do gate

1. Compare BindsTo mais After com o mesmo recurso de teste mais Requisite. Use um gate oneshot com RemainAfterExit e um arquivo de autorização descartável. Cubra um serviço e seus ativadores socket, timer e path.
2. Com o arquivo ausente e gate inativo, tente início direto do membro e cada ativação suportada. Capture resultado da condição, resultado do job, estado do gate/membro/ativadores, listener e lista de unidades com falha. Repita com o arquivo presente e depois com gate já ativo.
3. Remova o arquivo de um gate ativo, inspecione-o e solicite sua parada. Verifique que todos os membros e ativadores cadastrados terminaram de parar, incluindo uma ativação enfileirada. Teste uma partida manual posteriormente e capture o resultado. Verifique que a desvinculação preserva um membro ativo antes de parar o gate de uma política desabilitada.
4. Observe inicialização normal com e sem dispositivo, incluindo possíveis partidas antecipadas. Registre ruído da inicialização e estado SSH/rede. Sinalize qualquer intervalo de disponibilidade do serviço enquanto fechado. O responsável humano só pode selecionar uma variante se acessibilidade, encerramento e preservação do acesso corresponderem ao comportamento pretendido.

## S2 — Entrega, reinicializações e progresso

1. No modo de observação, correlacione adição/remoção física, inicialização com pendrive presente, reconexão rápida, remoção única seguida de silêncio e uma rajada limitada com entrega udev, submissões ao gerenciador e varreduras concluídas. Capture independentemente o estado físico final.
2. Organize um segundo evento durante estabilização, tolerância e verificação em recursos descartáveis. Verifique se a primeira ausência sobrevive à interrupção e se a verificação de expiração de fato ocorre. O observador lite deve demonstrar expiração da tolerância em silêncio. O futuro ciclo de aplicação S2 exige o timer de segurança. Reconecte antes da expiração e verifique que ausência obsoleta não pode parar uma política válida.
3. Meça CPU, pico de RSS, crescimento do journal, contagens de eventos/workers/conclusões, espera por bloqueio e responsividade SSH com StartLimitIntervalSec=0. Registre quando o último evento produz uma varredura concluída. Pare de aumentar a rajada se a responsividade do host piorar. Limitação de taxa zero não garante progresso.
4. Se o caminho principal falhar, compare a contingência com unidade de dispositivo marcada nos mesmos casos, verificando mapeamento e callback de remoção. Se considerar operação somente por timer, meça atraso de detecção e custo. O responsável humano seleciona o acionamento após as observações.

## S3 — Resultados assíncronos e prazos

1. Capture propriedades do gerenciador por tipo antes da submissão, enquanto jobs estão enfileirados e após conclusão. Registre parada normal, desativação lenta dentro e além do prazo, ativação malsucedida, membro mascarado/ausente, início pendente e jobs concorrentes. Use falhas restritas aos recursos de teste.
2. Exercite cada linha da tabela de verificação da [revisão](../../docs/phase0-review.md), incluindo ativador ativo, membro ativo com gate inativo, configuração efetiva obsoleta, propriedades desconhecidas e membro inativo de permissão somente. Compare o listener observado com o estado da unidade. Repita com vários membros e registre um único prazo de ponta a ponta.
3. Capture classificações de timeout e barramento indisponível por falha restrita ao recurso de teste ou dublê de teste se um caso real comprometeria o host. Marque cobertura simulada separadamente. Nunca interrompa gerenciador do host, SSH ou rede para produzir um resultado. Verifique que exposição prevalece sobre falhas simultâneas de disponibilidade.

## S4 — Encerramento emergencial e recuperação

1. Registre o inventário de instâncias de gate deliberadamente criadas, arquivos de autorização, estado carregado e jobs pendentes. Compare nenhuma correspondência, várias correspondências ativas, instâncias inativas/não carregadas e instância com partida enfileirada. Capture argumentos glob exatos, unidades selecionadas e estados subsequentes.
2. Compare saída crítica explícita do worker, timeout, reinicialização interrompida e código de saída 3. Observe se OnFailure executa em cada caso, exclui arquivos de autorização pertencentes ao projeto antes de solicitar paradas e impede reativação. Inclua um membro ativo protegido cujo drop-in descartável está ausente. O sucesso apenas da submissão do job mantém o caso aberto.
3. Introduza snapshot ausente/corrompido no cadastro descartável e retenha evidência independente de propriedade. Verifique se DEGRADED está visível, novas autorizações são inibidas e somente alvos não críticos cadastrados podem ser afetados. Registre qualquer caso de gerenciador indisponível como não verificado até haver evidência segura dentro do escopo.
4. Ensaie recuperação manual sem CLI ou dispositivo USB. Verifique desvinculação efetiva antes de parar gates, confirme estado original do membro, remova somente artefatos pertencentes aos recursos de teste e repita a recuperação. Compare a referência inicial e verifique ambas as sessões SSH, rede e console local.

**Registro histórico de decisão G1 (descontinuado).** Anexe evidências S1–S4 e observações H3–H8, anote casos ignorados, identifique o acionamento e a variante de gate escolhidos pelo responsável humano e registre exposição não resolvida com sua consequência. Um caso de segurança malsucedido exige revisão e outra observação. As fases 2 e 3 exigem decisão humana por escrito.

[English](../../docs/spike-procedures.md) · [Visão geral do projeto](../README.md)
