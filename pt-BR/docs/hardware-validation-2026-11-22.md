# Validação física no notebook Debian 13 — 2026-11-22

> **Referência histórica de observação somente (PR #4).** Este arquivo preserva a sessão inicial do observador e não deve ser interpretado como o estado completo da validação da demonstração descartável posterior. Consulte as [evidências físicas da demonstração](demo-safety.md) para os testes subsequentes.

Este é um registro conciso de evidências dos comandos executados pelo mantenedor no notebook físico headless via SSH, **antes do commit subsequente de reforço de segurança**. Identificadores e endereços foram omitidos intencionalmente.

## Ambiente

- Host: Positivo Motion; Intel Atom x5-Z8350; 2 GB DDR3; Debian 13 headless.
- Python 3.13.5; systemd ativo; sysfs USB disponível.
- Pendrive da classe de 14,6 GiB com número de série USB reportado e classe de interface `08`.
- O observador não montou o dispositivo USB e nenhum serviço externo ao projeto foi cadastrado ou controlado.

## Observações

| Procedimento | Resultado fornecido pelo mantenedor |
| --- | --- |
| `make test` | 10 testes unitários passaram (0 falhas). |
| `PYTHONPATH=src python3 -m usbgate.cli scan` | Dispositivo de armazenamento reconhecido com classe `08`, `identifier-only` e impressão digital sanitizada. |
| `PYTHONPATH=src python3 -m usbgate.cli doctor` | Python/systemd/sysfs disponíveis; pacote, observador e timer inicialmente ausentes. |
| `sudo make install` | Arquivos inertes instalados; observador permaneceu desabilitado. |
| `/usr/local/sbin/usbgate doctor` | CLI instalada executou; pacote instalado; timer e observador ainda não habilitados. |
| `sudo /usr/local/sbin/usbgate monitor enable` | Bem-sucedido; `status --json` informou `observe`, timer ativo e dispositivo USB `present`, aplicação da política falsa. |
| Remoção física | `status --json` informou o alvo `absent`; demais entradas USB continuaram `present`. |
| `sudo journalctl -t usbgate -n 30 --no-pager` | `device_absence_pending` às 13:57:47, `device_absent` às 13:57:57 e `device_returned` às 13:59:13 (horário local). |
| Reconexão física | A mesma impressão digital retornou a `present` com `absent_since: null`. |
| `sudo /usr/local/sbin/usbgate monitor disable` | Bem-sucedido; `doctor` informou observador desabilitado, timer inativo e estado em cache ainda disponível. |
| `sudo make uninstall` e `sudo systemctl daemon-reload` | Bem-sucedido; verificações após desinstalação mostraram inicializador, unidades systemd, regra udev e manifesto removidos. |

## O que estes resultados não estabelecem

- Não se afirma autenticação criptográfica, identidade única de hardware ou resistência a descritores USB clonados.
- O teste **não comprovou separadamente qual mecanismo de acionamento** (udev ou timer periódico) iniciou cada reconciliação.
- Inicialização com pendrive inserido, reconexão rápida dentro da tolerância, segundo dispositivo expondo descritores idênticos, falhas simuladas repetidas e interrupções de energia continuam sendo testes separados.
- Não há controle de serviço ou socket neste PR. SSH, rede, PAM e firewall estavam fora do escopo.
- O patch subsequente de reforço de segurança passou separadamente nos testes unitários do GitHub Actions e na compilação do código-fonte. Seu comportamento de instalação alterado ainda não foi retestado no hardware físico.

Este documento registra uma única sessão concluída, não uma certificação geral de revisões futuras.

[English](../../docs/hardware-validation-2026-11-22.md) · [Visão geral do projeto](../README.md)
