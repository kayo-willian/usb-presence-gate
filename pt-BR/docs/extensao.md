# Extensão da demonstração descartável (não um controle genérico de serviços)

**Estado atual: marco experimental concluído; desenvolvimento ativo pausado.**
O notebook real com Debian 13 testou somente a unidade descartável fornecida.

## O que pode e não pode ser feito hoje

| Objetivo | Disponível agora? |
| --- | --- |
| Observar dispositivos USB sem abrir seus sistemas de arquivos | Sim |
| Cadastrar um descritor inequívoco de armazenamento USB para a demonstração | Sim |
| Iniciar/parar a unidade fornecida `presence-demo.service` conforme a presença física | Sim |
| Substituir o processo `sleep` fornecido em um **fork separado de desenvolvimento** | Adaptação possível do código-fonte; não testada |
| Cadastrar um aplicativo já instalado com `usbgate enroll my-app.service` | **Esse comando não existe** |
| Controlar várias unidades arbitrárias ou sockets | **Não implementado** |
| Proteger SSH, rede, firewall, autenticação ou Docker Engine | **Explicitamente fora do escopo** |
| Comprovar autenticidade USB com arquivo de chave ou criptografia em hardware | **Não implementado** |

O comando `inspect-unit` da CLI é uma **verificação preliminar conservadora e somente para leitura**. Não cadastra, vincula nem controla a unidade inspecionada.

## Adaptação do código-fonte: uma carga de teste não crítica em primeiro plano

Um mantenedor que compreenda os limites de segurança pode criar um fork separado para experimentar um processo em primeiro plano sob seu próprio controle, **não crítico e descartável**, no lugar de `sleep`. Isso **não** é uma maneira oficialmente suportada de proteger um serviço systemd existente; modificar a demonstração invalida as evidências originais de hardware.

1. Crie uma **nova branch ou fork** a partir de uma cópia de trabalho limpa. Não edite diretamente a unidade instalada `/etc/systemd/system/presence-demo.service`.
2. Abra `packaging/systemd/presence-demo.service` na cópia do código-fonte.
3. Altere **apenas** o programa de `ExecStart=` para um programa descartável, auditado independentemente, executado em primeiro plano e com caminho absoluto. Por exemplo, `ExecStart=/usr/local/bin/my-disposable-worker` é um **marcador de exemplo**: não funcionará até que você forneça e revise esse executável. Não execute dessa forma um daemon essencial existente nem uma unidade de serviço.
4. Preserve `ConditionPathExists=/run/usbgate/demo-grant`, `DynamicUser=yes`, `NoNewPrivileges=yes` e as demais propriedades de isolamento. Se sua carga precisar de privilégios elevados, acesso à rede ou dados persistentes, **não enfraqueça essas configurações apenas para fazê-la funcionar**. Essa carga está fora da demonstração mínima.
5. Revise dependências da unidade, ciclo de vida do processo, tratamento de sinais, comportamento de reinicialização e qualquer possível acesso a SSH, rede ou serviços do sistema. A verificação preliminar estática **não é suficiente** para uma nova carga.
6. Execute as verificações antes de instalar em um **host de testes** isolado:

   ```sh
   make test
   systemd-analyze verify packaging/systemd/presence-demo.service
   ```

7. Se uma revisão anterior estiver instalada, primeiro realize sua desativação, redefinição e desinstalação normais a partir da cópia correspondente do código-fonte. Reinstale a partir do código modificado somente em uma máquina de testes. O manifesto instalado registra hashes dos arquivos de unidade gerenciados e o controle recusa deliberadamente edições silenciosas no local.
8. Repita a **matriz completa de testes físicos** para a nova carga: ausência/presença, remoção/tolerância, retorno, recusa de início manual, reinicialização, acionamento udev perdido, falha do systemd, recuperação de emergência sem Python e desinstalação baseada em manifesto. Se um teste não puder ser concluído, documente-o como não verificado. Nunca considere uma nova carga coberta pelas evidências existentes de `sleep`.

Isso substitui o processo de demonstração **dentro de uma única unidade fixa**, cujo nome continua sendo `presence-demo.service`. **Não adiciona outros serviços**.

## O que um controle genérico real de serviços exigiria

Uma versão futura poderia introduzir cadastro explícito, por unidade, de unidades systemd de serviço/socket próprias e não críticas. Isso constitui **novo design de produto**, não uma alteração na documentação. Exigiria:

1. Verificação de nomes canônicos e aliases, além de inspeção transitiva de dependências e propagação de parada; manter uma lista rigorosa de serviços críticos proibidos.
2. Integração reversível de unidades pertencentes ao projeto, sem modificar definições de serviços não relacionados e sem assumir automaticamente o controle de unidades em execução.
3. Integridade durável do cadastro e estado aplicado, incluindo transições interrompidas, identidades USB duplicadas e recuperação manual controlada.
4. Prevenção e detecção de caminhos alternativos de ativação (sockets, timers, paths, dependências, partidas manuais), com resultados de parada verificados.
5. Testes de falha específicos do host, reinicialização/reversão e medição da latência do evento até a parada em um alvo descartável antes de envolver dados reais.

**Nenhuma dessas funcionalidades genéricas está implementada na versão atual.** Abrir um futuro PR de desenvolvimento não exige manter esse experimento instalado em um servidor doméstico.

## Arquivos USB e autenticação

Nenhum arquivo ou segredo no pendrive é necessário. Arquivos em mídias flash comuns podem ser copiados; simplesmente adicionar um arquivo de chave não forneceria autenticação genuína baseada em hardware. Essa funcionalidade exigiria um modelo de ameaças e protocolo separados e não faz parte do escopo atual.

[English](../../docs/extending.md) · [Visão geral do projeto](../README.md)
