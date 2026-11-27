# Recuperação, diagnóstico e remoção

Esta página documenta a **demonstração descartável pertencente ao projeto**, não a recuperação de serviços Linux arbitrários. O procedimento original foi testado manualmente no notebook físico Debian 13 em 22/11/2026. A ordem revisada e o reforço atual de segurança ainda exigem validação real.

A demonstração não é um mecanismo de autenticação criptográfica. A recuperação nunca deve exigir o pendrive USB nem um interpretador Python funcional. Mantenha ao menos um caminho independente de acesso pelo console antes de usá-la em um host headless remoto.

## A. Verificar o estado sem alterá-lo

Se o inicializador instalado funcionar:

```sh
sudo /usr/local/sbin/usbgate doctor
sudo /usr/local/sbin/usbgate status --json
sudo /usr/local/sbin/usbgate demo status
```

Independentemente da CLI:

```sh
sudo systemctl is-active usbgate-reconcile.timer
sudo systemctl is-active usbgate-reconcile.service
sudo systemctl is-active presence-demo.service
sudo journalctl -u usbgate-reconcile.service -n 60 --no-pager
sudo journalctl -t usbgate -n 60 --no-pager
```

`is-active` normalmente retorna um código de saída diferente de zero quando uma unidade está inativa. O projeto normalmente não altera outros serviços do sistema.

## B. Desativação normal (Python e CLI disponíveis)

Se a demonstração estiver cadastrada (armada ou desarmada):

```sh
sudo /usr/local/sbin/usbgate demo disable
sudo /usr/local/sbin/usbgate demo reset
sudo /usr/local/sbin/usbgate monitor disable
```

Se a demonstração nunca foi cadastrada, ignore `demo disable` e `demo reset`.
Se o monitoramento nunca foi habilitado, `monitor disable` é opcional.

A partir da mesma cópia do código-fonte utilizada para instalar:

```sh
sudo make uninstall
sudo systemctl daemon-reload
```

Não contorne uma recusa de desinstalação removendo arquivos arbitrários à força. O instalador real verifica o manifesto e exige inatividade confirmada do timer, worker e demonstração antes de excluir arquivos. Uma unidade ausente, job pendente, estado de falha ou resposta ilegível do gerenciador mantém os arquivos instalados no lugar. Inspecione o gerenciador ou restaure as definições esperadas das unidades antes de tentar novamente.

### Operações administrativas interrompidas

Verifique `sudo /usr/local/sbin/usbgate demo status` quanto à política, autorização, estado do serviço e `authorization_inhibited`. O marcador fica em `/var/lib/usbgate/authorization-inhibited`. Sobrevive à saída do processo e à reinicialização normal. Um worker que o encontra tenta o encerramento verificado. Os bloqueios em `/run` são liberados automaticamente na saída do processo.

Após corrigir a falha de sistema de arquivos ou do gerenciador reportada, tente novamente `demo disable` para uma política cadastrada e depois `monitor disable` ou `monitor enable`, conforme o estado desejado do monitoramento. Esses comandos funcionam sem o USB. Uma transição bem-sucedida do monitor limpa um marcador obsoleto somente após verificar seu resultado. Uma política armada com marcador obsoleto deve ser desarmada primeiro. Preserve o marcador durante a recuperação independente de Python abaixo. Ele pode permanecer após desinstalação manual e inibirá uma instalação posterior até que o monitoramento seja configurado com sucesso.

Se tanto a política desabilitada quanto o marcador independente não forem persistidos, uma política armada poderá autorizar uma partida posterior. Inspecione o resultado de encerramento reportado e utilize a recuperação manual se necessário. Uma parada malsucedida pode deixar um processo ativo mesmo quando a autorização futura está bloqueada. Perda súbita de energia, alterações externas por root e falhas do gerenciador não têm prazo de recuperação demonstrado.

## C. Recuperação manual sem Python

O procedimento abaixo pressupõe as unidades e relações originais do projeto. Se o worker reportar `unsafe to stop`, ou se alguma unidade ou regra do projeto divergir da configuração instalada, inspecione primeiro os fragmentos efetivos, drop-ins, relações e a regra. A parada manual de uma unidade modificada pode propagar-se para outro serviço. Resolva a divergência antes de agir; preserve regras modificadas pelo administrador e evidências. Se a remoção da autorização falhou, inspecione também o caminho da autorização: um serviço inativo ainda pode estar elegível para uma partida posterior.

```sh
sudo systemctl disable --now usbgate-reconcile.timer
sudo rm -f /etc/udev/rules.d/70-usbgate.rules
sudo udevadm control --reload
sudo systemctl stop usbgate-reconcile.service
```

Remova somente a regra verificada como pertencente ao projeto. Confirme que o worker está inativo antes de prosseguir. Preserve qualquer marcador de inibição administrativa existente.

```sh
sudo rm -f /run/usbgate/demo-grant
sudo systemctl stop presence-demo.service
sudo mv -n /etc/usbgate/demo.json /etc/usbgate/demo.json.disabled
sudo systemctl daemon-reload
```

A linha `mv` pressupõe que existe um `demo.json` ativo e que o destino `demo.json.disabled` **ainda não existe**. Se a política estiver ausente ou houver um backup existente, **inspecione primeiro e escolha um nome de backup único**; não sobrescreva dados existentes do operador. Mantenha a política salva para investigação.

Se um comando systemctl falhar, não presuma que o encerramento está completo. Inspecione `systemctl status` e `journalctl`, preserve a evidência e use a recuperação pelo console local se necessário. O sistema não pode garantir o encerramento quando o gerenciador subjacente ou o kernel está indisponível.

Verifique sem depender de Python:

```sh
sudo systemctl is-enabled usbgate-reconcile.timer
sudo systemctl is-active presence-demo.service
sudo systemctl is-active usbgate-reconcile.timer
sudo systemctl is-active usbgate-reconcile.service
sudo test ! -e /run/usbgate/demo-grant && echo "Demo grant absent"
sudo test ! -e /etc/usbgate/demo.json && echo "Active demo policy absent"
```

O timer deve reportar `disabled`, as três verificações de atividade das unidades devem reportar `inactive`, e as duas verificações de arquivos devem reportar a ausência de autorização e política ativa.

Após verificar, é possível executar `sudo make uninstall` a partir da mesma cópia do código-fonte. A **política de backup é preservada intencionalmente** e não faz parte do manifesto.

## D. Instalação inerte / atualização e falhas de integridade de arquivos

- `make install` recusa destinos ocupados, diretórios ancestrais que sejam links simbólicos e um manifesto de instalação existente. Inspecione primeiro a propriedade dos arquivos; **não sobrescreva**.
- `make uninstall` compara hashes dos arquivos instalados gerenciados com `/var/lib/usbgate/install-manifest.json`. Se um arquivo instalado tiver sido alterado, recusa sua remoção. Preserve evidências antes de reparar; não exclua o manifesto indiscriminadamente.
- O código-fonte da cópia deve corresponder à versão instalada ao usar `sudo make uninstall`. A reinstalação não é uma atualização no local: desativação, redefinição e desinstalação normais devem vir primeiro.
- `systemctl daemon-reload` é necessário após instalar ou remover arquivos de unidades. Unidades instaladas a partir do código-fonte permanecem inertes até ativação explícita.
- Não é fornecido script de limpeza forçada porque excluir arquivos arbitrários de `/etc/systemd/system` ou `/etc/udev/rules.d` é perigoso.

## E. Dados residuais e remoção opcional do repositório

A cópia do código-fonte é diferente do aplicativo instalado. O manifesto deliberadamente **não** inclui backups de políticas do operador, estado volátil de observação, logs ou dados não relacionados.

Após desinstalar completamente e verificar que os serviços do projeto estão inativos, você pode inspecionar os resíduos conhecidos:

```sh
sudo ls -la /etc/usbgate /var/lib/usbgate /run/usbgate
```

Diretórios ausentes produzirão um erro inofensivo. Revise cada item antes de remover; o backup da recuperação manual geralmente é `/etc/usbgate/demo.json.disabled`. Nunca exclua um diretório apenas porque se parece com um caminho do projeto.

Somente após confirmar que o projeto está salvo no GitHub e que sua árvore de trabalho local não tem alterações não salvas, remova opcionalmente o clone local:

```sh
cd ~
rm -rf -- "$HOME/usb-presence-gate"
```

Isso exclui permanentemente a **cópia de trabalho local**, não o repositório remoto no GitHub.

[English](../../docs/recovery.md) · [Visão geral do projeto](../README.md)
