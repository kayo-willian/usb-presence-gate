# Verificações no notebook

Em 22/11/2026 o mantenedor relatou Debian GNU/Linux 13.8 (trixie), Python 3.13.5, systemd 257 (257.13-1~deb13u1) e kernel 6.12.117+deb13-amd64 no notebook de testes.

| Verificação | Estado | Evidência ou próxima observação |
| --- | --- | --- |
| H1 — python3 está instalado e informa a versão 3.13.5 | verificado em hardware | Relato do notebook acima. |
| H1 — importação de `tomllib` e leitura de `CLOCK_BOOTTIME` | verificado em hardware | Consulte a transcrição abaixo. |
| Observação USB, remoção e tolerância | verificado em hardware | O mantenedor observou o dispositivo presente, ausência pendente, ausência após 10 segundos e retorno; o journald confirmou as transições. O isolamento dos mecanismos de acionamento ainda não foi medido. |
| Reinicialização com o USB já conectado | verificado em hardware | Após reinicialização física, serviço da demonstração e timer voltaram a ficar ativos com USB ainda conectado e SSH permaneceu disponível. |
| Reconexão rápida dentro da tolerância de 10 segundos | não testado | Exige teste físico separado de temporização; não pode ser inferido de uma reconexão posterior. |
| Encerramento do serviço descartável fornecido `presence-demo.service` | verificado em hardware | A remoção física do USB interrompeu a demonstração após observação; um início manual normal sem autorização a deixou inativa. |
| Encerramento de serviço/socket arbitrário | não implementado | A CLI não possui cadastro geral nem controle de sockets. |

## Evidência H1 no notebook

O mantenedor executou este comando no notebook de testes em 22/11/2026.

```console
$ python3 -c 'import time, tomllib; print("tomllib OK"); print("CLOCK_BOOTTIME", time.clock_gettime(time.CLOCK_BOOTTIME))'
tomllib OK
CLOCK_BOOTTIME 44825.708116314
```

G1 e os experimentos S3/S4 foram descontinuados. O registro anterior está disponível no histórico Git.

[English](../../docs/hypotheses.md) · [Visão geral do projeto](../README.md)
