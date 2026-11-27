# Limites de segurança do controle descartável

O marco experimental concluído inclui uma **demonstração** deliberadamente restrita, não o controle genérico de serviços/sockets. A unidade controlada é fixada no código como `presence-demo.service`, instalada como arquivo do projeto pertencente ao root com `ConditionPathExists=/run/usbgate/demo-grant`. O processo executa sob identidade transitória gerenciada pelo systemd (`DynamicUser=yes`) e não realiza atividades de rede nem de aplicação.
Isso substituiu a configuração original `User=nobody` após a verificação `systemd-analyze verify` do mantenedor no Debian 13 advertir que a conta compartilhada nobody era insegura. A unidade atualizada passou em uma nova verificação estática no notebook sem avisos.

O cadastro da demonstração aceita apenas um dispositivo de armazenamento USB conectado no momento com uma impressão digital de descritores baseada em número de série não vazio e inequívoco. Clonagem de descritores, dispositivos roubados e dispositivos físicos maliciosos **não** são impedidos. Nenhum número de série bruto é armazenado; a própria impressão digital permite correlação.

A ativação verifica a unidade instalada, o timer ativo e o descritor USB atual. O worker e a ativação inicial registram a observação antes de conceder autorização. A ausência física tem tolerância de dez segundos medida desde a detecção. Uma falha de gravação da observação ignora essa tolerância e tenta o encerramento imediatamente. O comando reporta o erro de gravação mesmo quando o encerramento é bem-sucedido.

O resultado do encerramento considera tanto o arquivo de autorização quanto o serviço em execução.

- Tenta-se remover a autorização mesmo quando a unidade falha na verificação de segurança. Um erro de unlink ou link simbólico recusado é informado junto ao resultado do serviço. Uma autorização remanescente ainda pode satisfazer a condição de início da unidade.
- O worker consulta o serviço real mesmo com política ausente ou desabilitada e sem autorização. Se for necessário parar, verifica o arquivo instalado contra o manifesto e as propriedades efetivas do systemd antes de solicitar a parada. Uma verificação de segurança malsucedida bloqueia a solicitação de parada e exige revisão do operador. Após solicitá-la, o worker consulta novamente o gerenciador, inclusive quando a solicitação excedeu o tempo limite. Uma parada confirmada exige que a unidade canônica carregada informe `inactive/dead` com propriedade `Job` vazia.

`demo status` informa `service_state` como `active`, `inactive`, `transitioning`, `failed` ou `unknown`. O campo de compatibilidade `service_active` é JSON `null` para os três últimos. Um resultado desconhecido inclui diagnóstico.
Essas observações descrevem o instante da consulta ao gerenciador. Jobs posteriores, um worker travado ou um gerenciador inacessível ainda podem exigir [recuperação manual](recovery.md).

Testes de regressão offline usam arquivos temporários e respostas simuladas do systemd, incluindo comunicação interrompida e falhas simultâneas de persistência, revogação e parada. As observações físicas abaixo são anteriores a essas mudanças.
Os caminhos de falha atualizados e a temporização no notebook Debian aguardam validação em hardware.
A recuperação manual funciona independentemente de Python e USB. O único alvo de atuação da demonstração é `presence-demo.service`. Campos USB não fornecem nomes de unidades nem argumentos de subprocessos.

## Unidades efetivas, timer e udev

A autorização confia no manifesto de instalação pertencente ao root em `/var/lib/usbgate`.
A demonstração, timer, worker e regra udev de referência devem corresponder aos hashes SHA-256 instalados. A regra udev implantada deve ter bytes idênticos aos da referência verificada. Cada arquivo verificado deve ser regular, pertencer ao root e não permitir escrita por grupo ou outros. As mesmas restrições de propriedade e escrita se aplicam aos diretórios ancestrais; links simbólicos nesses caminhos são recusados.
Uma instalação local com prefixo gravável por grupo exigirá revisão administrativa. O projeto nunca corrige permissões nem sobrescreve regra modificada.

O gerenciador deve reportar o único nome esperado e o fragmento canônico sob `/etc/systemd/system/` para cada unidade, sem drop-ins, definição transitória ou recarga pendente do daemon. Tanto iniciar quanto parar a demonstração exige o tipo de serviço simples esperado, usuário dinâmico, slice do sistema, elegibilidade para controle manual e relações seguras. Uma nova partida também exige `inactive/dead` com `Job` vazio. Quando há job pendente ou o serviço está em transição, o controle revoga a autorização e pode solicitar parada após verificar novamente a unidade. Com o modo padrão de jobs do systemd, uma parada pode substituir uma partida conflitante enfileirada. O encerramento ainda exige uma nova observação de `inactive/dead` sem job. [Debian systemctl(1)](https://manpages.debian.org/trixie/systemd/systemctl.1.en.html)

As verificações de unidades fixas examinam relações diretas de transação. Permitem `Requires=` no slice normal do sistema e no target sysinit, e dependências de montagem para os caminhos raiz, `/tmp`, `/var` e `/var/tmp` usados por diretórios temporários privados. Permitem o conflito com o target de desligamento, o par timer/worker fornecido e a instalação do timer em `timers.target`. Inclusões inesperadas, requisitos reversos, propagação de parada, manutenção de atividade, ativadores de sucesso/falha, conflitos e ações de emergência causam recusa. A ordenação pura por `Before=` ou `After=` não inclui uma unidade em uma transação. A inspeção genérica de candidatos, somente para leitura, mantém seu propósito mais restrito. [Debian systemd.unit(5)](https://manpages.debian.org/trixie/systemd/systemd.unit.5.en.html)

O timer periódico deve informar `active` e `waiting` ou `running`, job vazio, `UnitFileState=enabled` e o worker esperado tanto em `Unit` quanto em `Triggers`. O link simbólico persistente em `/etc/systemd/system/timers.target.wants/` deve resolver para o fragmento verificado do timer. Um timer expirado ou habilitado apenas em tempo de execução não pode autorizar a demonstração. O worker oneshot pode ficar inativo entre execuções. Durante a configuração inicial do monitor, as verificações de arquivo e configuração efetiva precedem a ativação; a habilitação persistente é verificada posteriormente.
`monitor disable` limpa a inibição administrativa somente após confirmar que o timer está `inactive/dead` com job vazio, `UnitFileState=disabled` e nenhuma relação `WantedBy` restante. O link de inicialização deve estar ausente (um link simbólico quebrado ainda conta como presente) e o observador deve informar `inactive/dead` sem job. Uma verificação inconclusiva mantém a inibição. [Debian systemd.timer(5)](https://manpages.debian.org/trixie/systemd/systemd.timer.5.en.html)

`doctor` e `status --json` expõem `monitor_safety` como `verified` ou um diagnóstico; use sudo para ler o manifesto de instalação. `timer_active` continua descrevendo somente a atividade atual. Uma falha de monitoramento bloqueia autorização e aciona encerramento verificado na reconciliação. Uma verificação estrutural malsucedida impede que o worker pare uma demonstração ativa. Revise o fragmento, relação, regra, permissões ou habilitação indicados antes de tentar novamente a recuperação. Uma transição malsucedida do monitor mantém sua inibição.

Essas verificações amostram o estado do disco e do gerenciador. Confiam na origem da instalação, no administrador root e no gerenciador; não percorrem todo o grafo transitivo de dependências nem serializam alterações externas privilegiadas. Bytes idênticos da regra não confirmam entrega pelo udev. Testes offline cobrem recusa e recuperação com respostas simuladas do gerenciador. Propriedades efetivas no notebook físico, entrega de eventos e acionamentos apenas pelo timer após inicialização ainda precisam de validação real.

## Transições administrativas

Todos os comandos de monitor e demonstração que alteram estado adquirem primeiro `/run/usbgate/admin.lock`. Adquirem o bloqueio do observador ao ler ou modificar a autorização. O worker adquire somente o bloqueio do observador. Um comando de monitor registra marcador de inibição persistente e encerra a demonstração sob esse bloqueio, então libera o bloqueio do observador antes de solicitar ao systemd início ou parada do worker. Um worker pode terminar durante essa espera e só pode encerrar a demonstração enquanto o marcador existir. O monitor limpa o marcador após sucesso dos comandos e das verificações finais de estado.

A ativação inicial registra a observação USB e verifica a unidade fixa e o gerenciador antes de conceder a autorização. A política permanece desabilitada até confirmar o serviço ativo e verificar novamente o monitor. Um worker após interrupção anterior ao registro da política encerra qualquer autorização ou demonstração restante. Após o registro, a ativação permanece mesmo se a CLI for encerrada antes de imprimir sucesso. Uma falha de ativação reportada tenta desarmar, revogar e parar com segurança e informa os resultados.

Uma vez armada, a demonstração acompanha o estado USB observado. Uma amostra nova e elegível e um serviço confirmado inativo causam partida mesmo se a autorização já existir. Isso recupera partidas interrompidas do worker e também reverte uma parada manual do serviço enquanto o USB permanece elegível. Use `demo disable` para mantê-lo parado. Estados com falha, em transição e desconhecidos não podem autorizar partida.

A desativação registra o marcador de inibição e grava a política desabilitada antes do encerramento. Uma operação incompleta pode, portanto, deixar política desabilitada com processo ainda em execução. O status expõe `authorization_inhibited` independentemente da política e do estado do serviço. Consulte [recuperação administrativa](recovery.md#operações-administrativas-interrompidas).

Os testes de concorrência usam processos Linux separados, bloqueios reais de arquivos e barreiras de sincronização. Respostas de serviço e observações USB são simuladas. A temporização real do gerenciador Debian e a reinicialização durante uma transição aguardam validação.

## Observações no notebook físico — 2026-11-22

O mantenedor relatou as seguintes saídas do notebook Debian 13 nesta branch de rascunho:

- A **suíte completa de 41 testes passou**; `systemd-analyze verify` terminou sem saída após a mudança para usuário dinâmico.
- `sudo make install` instalou arquivos inertes, e `demo status` inicialmente informou `state=unconfigured`, sem autorização e demonstração inativa.
- A verificação preliminar somente para leitura `inspect-unit presence-demo.service` passou.
- `monitor enable` explícito informou somente observação. Uma impressão digital de armazenamento USB cadastrada explicitamente permaneceu desabilitada até `demo enable`.
- Com o pendrive conectado, `demo enable` informou sucesso e `demo status` informou habilitado, autorização presente e serviço ativo; systemd separadamente informou `active`.
- Após remoção física, `demo status` informou autorização ausente e serviço inativo; o observador registrou dispositivo `absent` e timer de segurança `active`.
- Após reconexão física, `demo status` voltou a informar autorização e serviço ativos, com systemd informando independentemente `active`.
- Com a demonstração desabilitada, o mantenedor tentou iniciar `presence-demo.service` manualmente; o serviço permaneceu inativo e a autorização ausente (`state=enrolled`).
- A reativação explícita restaurou tanto autorização quanto serviço em execução.
- Após reiniciar com pendrive conectado, SSH retornou, timer de segurança estava ativo, e autorização e serviço descartável estavam ativos.
- Uma recuperação manual independente de Python foi executada com sucesso: timer e worker parados, regra udev pertencente ao projeto removida e recarregada, autorização da demonstração revogada, serviço parado e política salva movida para outro caminho. Verificações posteriores da CLI informaram `state=unconfigured`, sem autorização, serviço e timer inativos.
- Após recuperação manual, o mantenedor executou `sudo make uninstall` seguido de `systemctl daemon-reload`; arquivos pertencentes ao manifesto foram removidos e um teste de shell posterior confirmou ausência de `/usr/local/sbin/usbgate`. O backup `/etc/usbgate/demo.json.disabled` foi intencionalmente preservado.

Essas são **observações em hardware, não prova de autenticação nem de uma fronteira rígida de segurança**.
Nenhum número de série bruto, impressão digital real ou hostname é publicado aqui. A latência exata de parada, se udev ou timer iniciou cada transição, reconexão rápida antes da expiração da tolerância, perda do timer e recuperação de política corrompida permanecem sem verificação. A exclusão do backup é deliberadamente uma escolha separada do operador, não parte da desinstalação baseada em manifesto.

## Testes ainda não estabelecidos no host físico

Essas limitações permanecem embora o ciclo de vida central da demonstração tenha sido observado fisicamente:

- Reconexão USB rápida **dentro** do intervalo de tolerância.
- Evento udev perdido com contingência comprovada somente pelo timer.
- Política corrompida, timer excluído, falhas repetidas do gerenciador, interrupção forçada e comportamento hostil com descritores clonados no notebook físico.
- Tempo máximo garantido entre remoção física e parada do processo.
- `demo reset` pela CLI após `demo disable` normal (apenas teste unitário).
- Implantação ou proteção de qualquer aplicação real existente ou múltiplas unidades/sockets (não implementado).

O backup criado pela recuperação manual é preservado deliberadamente até o administrador inspecioná-lo e excluí-lo separadamente. A desinstalação física documentada a partir do código-fonte não afirmou purgar esse backup.
Evidência de aceitação física não é certificação de segurança.

[English](../../docs/demo-safety.md) · [Visão geral do projeto](../README.md)
