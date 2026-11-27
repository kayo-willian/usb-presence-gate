# Marco concluído; escopo futuro

**Status em 22/11/2026: marco da demonstração experimental concluído, desenvolvimento pausado.**

Este repositório possui duas capacidades implementadas:

- Um **observador de presença USB** leve e testado fisicamente.
- Um **controle de ativação explícita, testado fisicamente, para o serviço descartável fixo pertencente ao projeto `presence-demo.service`**. Inicia e interrompe essa unidade ociosa conforme a presença USB reportada, com tolerância medida a partir da detecção.

Os documentos iniciais de planejamento exploraram um controle genérico para serviços/sockets não críticos selecionados. **Esse plano foi deliberadamente reduzido neste marco** para não colocar a infraestrutura em risco. A implementação atual não cadastra serviços existentes arbitrários, não gerencia sockets e não possui autenticação real por hardware.

## Registro de aceitação física

O mantenedor relatou no Debian 13:

- 41 testes automatizados passaram e `systemd-analyze verify` não emitiu avisos.
- A varredura USB, observação, instalação inerte, cadastro, ativação explícita e remoção/reconexão física do USB foram bem-sucedidos.
- A unidade descartável parou após uma remoção processada e reiniciou após a reconexão. Uma tentativa normal de início manual sem a autorização da demonstração não a iniciou.
- Uma reinicialização com o pendrive inserido restaurou a demonstração, o timer e o SSH.
- A recuperação sem Python revogou a autorização, interrompeu a demonstração e desativou a observação; a desinstalação a partir do código-fonte removeu os arquivos gerenciados.

Essas são **observações de laboratório** reproduzíveis, não certificação de segurança, garantia temporal ou evidência para serviços arbitrários.

## Não implementado ou verificado apenas parcialmente

- Cadastro de serviços e sockets arbitrários, múltiplas políticas e aplicação completa das dependências e caminhos de ativação.
- Autenticação criptográfica por token, proteção contra falsificação de descritores USB ou roubo e segredos seguros no sistema de arquivos USB.
- Verificação em hardware de reconexão rápida dentro da tolerância, processamento de eventos apenas pelo timer, recuperação de política corrompida, inicialização sem USB, clonagem de identificadores USB e falhas graves do host/gerenciador.
- Limite máximo rígido entre a remoção física e a parada confirmada do processo, garantia de segurança ou suporte de produção.

## Possíveis extensões, não compromissos

Futuros mantenedores poderiam investigar controle genérico de serviços não críticos, verificações de integração mais rigorosas, medição do tempo de contingência, mais injeção de falhas ou desafio/resposta com suporte de hardware. Cada possibilidade exigiria nova revisão arquitetural, branch de funcionalidade, testes independentes, validação em hardware real e plano de recuperação. Nenhuma nova funcionalidade está programada.

Consulte o [README completo](../README.md), o [registro de segurança da demonstração](demo-safety.md), a [recuperação](recovery.md) e o [guia de extensão](extending.md).

Nunca use a demonstração para bloquear SSH, autenticação, rede, firewall, Docker Engine ou outra infraestrutura crítica.

[English](../../docs/completion-plan.md) · [Visão geral do projeto](../README.md)
