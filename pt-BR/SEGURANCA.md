# Política de segurança

[English](../SECURITY.md) · [Documentação em português](README.md)

> Tradução para português brasileiro. Em caso de divergência, consulte a versão original em inglês.

## Escopo e limitações

USB Presence Gate é um observador experimental de presença USB com um serviço descartável de ativação explícita. Não é autenticação criptográfica, autorização de dispositivos USB nem proteção para produção. Descritores USB podem ser copiados, e nem o arquivo de autorização temporária nem a tolerância de ausência configurada garantem o encerramento de um processo em execução.

A plataforma de referência é Debian 13 com systemd 257. A branch atual de desenvolvimento é `main`. O projeto não promete período de suporte, cronograma de correções ou SLA de resposta de segurança. As evidências históricas em hardware se aplicam somente à revisão e aos cenários testados.

## Relatar uma vulnerabilidade

Exemplos de problemas relevantes incluem atuação insegura sobre serviços, efeitos não intencionais em unidades não relacionadas, autorização inesperada após falha administrativa, contorno de verificações de integridade, tratamento inseguro de arquivos privilegiados e exposição de dados sensíveis.

Use a [página de avisos de segurança](https://github.com/kayo-willian/usb-presence-gate/security/advisories) do repositório e **Report a vulnerability** se o relato privado de vulnerabilidades estiver disponível. Caso contrário, abra uma issue pública solicitando meio de contato privado, sem detalhes de exploração, identificadores das máquinas afetadas ou segredos. Não presuma que o relato privado esteja habilitado.

Inclua o commit afetado, ambiente, limite de segurança esperado, comportamento observado, impacto, reprodução mínima com recursos simulados ou descartáveis e eventual correção sugerida. Diferencie problemas reproduzidos de hipóteses. Evite publicar números de série USB brutos, impressões digitais, nomes de hosts, IPs ou logs não sanitizados.

Dê ao mantenedor uma oportunidade razoável de investigar antes de tornar públicos detalhes exploráveis. Não teste sistemas que não sejam seus ou para os quais não tenha autorização. Não há programa de recompensas nem prazo de resposta prometido.

Bugs comuns não sensíveis devem ser relatados nas Issues do GitHub. O [guia de contribuição](CONTRIBUICAO.md) explica testes e revisão seguros. Caso uma instalação local apresente comportamento inesperado, utilize o [guia de recuperação](../docs/recovery.md) em vez de enfraquecer verificações de segurança ou controlar serviços essenciais.
