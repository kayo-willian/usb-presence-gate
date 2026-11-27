# Histórico de alterações

Este documento registra alterações significativas integradas ao USB Presence Gate. As propostas ficam nas issues e pull requests. O código identifica a versão atual como `0.1.0`. As datas abaixo marcam etapas do desenvolvimento, não lançamentos separados com tags.

## [Sem lançamento]

### Adições

- Guia de contribuição, código de conduta, política de comunicação de problemas de segurança e modelos de issue e pull request.

### Alterações

- Atualização das instruções de instalação, uso, diagnóstico, atualização, recuperação e contribuição do README e alinhamento do guia detalhado de recuperação. Nenhuma mudança no comportamento em execução.
- Verificação de segurança do systemd e do udev ([#9](https://github.com/kayo-willian/usb-presence-gate/pull/9), 2026-11-24): verificar arquivos de unidade do projeto, identidades efetivas, relações diretas de transação, habilitação persistente do timer e integridade da regra implantada contra o manifesto de instalação.
- Separação das verificações de início e parada para permitir parar uma partida pendente quando a unidade permanece estruturalmente segura; manter a inibição administrativa até confirmar desabilitação persistente do monitor.
- Adição de diagnóstico de segurança do monitor e verificação estática em CI das três unidades systemd fornecidas.

### Correções

- Consistência administrativa ([#8](https://github.com/kayo-willian/usb-presence-gate/pull/8), 2026-11-23): serializar operações administrativas, usar inibição persistente de autorização, registrar ativação após partida bem-sucedida, desarmar antes da parada e recuperar partidas interrompidas.
- Reconciliação em caso de falha ([#7](https://github.com/kayo-willian/usb-presence-gate/pull/7), 2026-11-23): tentar encerramento diante de falhas na persistência de observações, distinguir estados systemd, informar separadamente resultados de revogação e parada, verificar serviços ativos sem autorização, reforçar verificações de desinstalação e isolar o inicializador privilegiado.

### Validação

- Suíte de regressão offline ampliada de 41 para 116 testes nos três PRs de reforço de segurança. O CI mais recente também passou na verificação estática de unidades. Essas alterações ainda exigem validação real no Debian 13; nenhum novo resultado em hardware é implícito.

## 2026-11-22 — Marco experimental

### Adições

- Observação somente para leitura de descritores USB com indicação de identidade baseada apenas em identificadores, fraca e ambígua.
- Observação opcional via udev e systemd periódico com estado volátil e tolerância de ausência de dez segundos a partir da detecção.
- Inspeção conservadora somente para leitura de candidatos systemd e um controle de serviço descartável cadastrado explicitamente.
- Instalação inerte, remoção baseada em manifesto e recuperação independente de Python.
- Evidências do notebook físico e documentação da demonstração suportada, limitações, modelo de ameaças e adaptação do código-fonte.

### Validação

- Os testes históricos no notebook cobriram ciclo normal da demonstração, remoção/reconexão, recusa de início manual sem autorização, reinicialização com pendrive conectado, recuperação de emergência e desinstalação baseada em manifesto após recuperação. Consulte as [evidências em hardware](docs/seguranca-da-demonstracao.md) para o escopo exato.

[Sem lançamento]: https://github.com/kayo-willian/usb-presence-gate/commits/main/

[English](../CHANGELOG.md) · [Visão geral do projeto](README.md)
