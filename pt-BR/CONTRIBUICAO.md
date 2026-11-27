# Como contribuir com o USB Presence Gate

[English](../CONTRIBUTING.md) · [Documentação em português](README.md)

> Tradução para português brasileiro. Em caso de divergência, consulte a versão original em inglês.

Contribuições são bem-vindas. Você pode fazer um fork deste repositório, experimentar de forma independente, relatar um bug, melhorar a documentação ou enviar um pull request. O projeto utiliza a licença [MIT](../LICENSE); estas diretrizes regem contribuições ao repositório original, não o que você pode fazer com seu próprio fork sob essa licença.

## Escopo do projeto

USB Presence Gate é um observador experimental de descritores USB e um mecanismo de controle com ativação explícita para um serviço descartável no Debian 13 headless. Não é autenticação, produto de segurança nem gerenciador de serviços de uso geral. Leia o [README](README.md), os [limites de segurança](docs/demo-safety.md), o [guia de recuperação](docs/recovery.md) e as [instruções do mantenedor](../AGENTS.md) antes de alterar o comportamento.

Contribuições úteis incluem relatos de bugs reproduzíveis, testes de regressão, precisão da observação USB, uso limitado de recursos, tratamento seguro de falhas, documentação e observações em hardware verificadas de forma independente. Discuta mudanças arquiteturais, novas dependências ou ampliação do controle de serviços em uma issue antes da implementação. Uma funcionalidade proposta não representa compromisso de integração.

## Primeiros passos

Utilize uma conta comum em uma máquina Linux de desenvolvimento. A plataforma de referência é Debian 13 com systemd 257 e Python 3.13. A suíte offline também admite testes com Python 3.12. Não são necessários dispositivo USB, root, systemd em execução, Docker, VM ou pacotes Python de terceiros para os testes offline.

1. Faça um fork pelo botão **Fork** do GitHub e clone seu fork.
2. Adicione o repositório original como remoto upstream e crie uma branch específica.

   ```sh
   git clone https://github.com/YOUR-USERNAME/usb-presence-gate.git
   cd usb-presence-gate
   git remote add upstream https://github.com/kayo-willian/usb-presence-gate.git
   git fetch upstream
   git switch -c fix/descriptive-name upstream/main
   ```

3. Execute os testes existentes antes de modificar o código.

   ```sh
   make test
   python3 -m compileall -q src bin tests
   ./bin/usbgate --help
   ```

4. Faça a menor alteração coerente, adicione testes de regressão quando aplicável e execute novamente toda a suíte. Em alterações exclusivamente documentais, confira links, comandos, precisão técnica e diff.
5. Revise suas alterações, faça commit, envie a branch ao seu fork e abra um pull request para a branch `main` deste repositório.

   ```sh
   git diff --check
   git status --short
   git add -- path/to/changed-file
   git commit -m "fix: describe the change"
   git push -u origin fix/descriptive-name
   ```

Substitua o nome de usuário, a branch e o caminho de arquivo dos exemplos pelos seus. Use os prefixos de branch `docs/`, `fix/` ou `feature/`, conforme apropriado. Mantenha commits descritivos e evite alterações não relacionadas.

## Requisitos de segurança

- Restrinja a atuação da demonstração ao serviço fornecido `presence-demo.service`. O observador só pode gerenciar suas próprias unidades fixas de monitoramento e sua regra.
- Nunca interfira em SSH, rede, firewalls, autenticação, PAM, configuração de inicialização, Docker, registros de logs, unidades systemd não relacionadas ou autorização USB do kernel.
- Nunca monte nem acesse o conteúdo do sistema de arquivos USB. Trate descritores e impressões digitais como identificadores não confiáveis e falsificáveis; nunca os use como comandos shell, caminhos ou nomes arbitrários de unidades.
- Preserve a identidade e integridade verificadas das unidades, o tratamento explícito de estados desconhecidos, bloqueios administrativos, inibição de autorização, rollback, timer de contingência, revogação de autorização temporária e verificação de parada segura.
- Preserve a recuperação independente de Python e as verificações de propriedade baseadas no manifesto. Não contorne recusas excluindo arquivos à força ou enfraquecendo verificações de segurança.
- Mantenha baixo o consumo de recursos, preserve a arquitetura baseada na biblioteca padrão e não introduza daemon residente ou novas dependências sem discussão prévia.
- Não afirme que desconectar um dispositivo garante a parada em dez segundos. A tolerância começa na detecção, e falhas podem deixar o processo ativo.

Para testes unitários e de integração, use diretórios temporários, observações USB simuladas, respostas controladas do gerenciador e injeção determinística de falhas. Teste caminhos de falha e operações bem-sucedidas. Para alterações concorrentes, demonstre a ordenação com bloqueios reais e sincronização explícita quando viável. Não pare serviços reais nem altere hardware real na suíte offline.

Experimentos reais são opcionais. Caso opte por validar em seu próprio host descartável de testes, leia primeiro o guia de recuperação, mantenha uma sessão SSH separada e acesso ao console local e nunca teste com uma carga crítica. Não afirme que houve validação em hardware com base em simulação ou revisão anterior. Informe commit exato, plataforma, procedimento, resultado e limitações restantes.

## Relatos e propostas de alterações

Pesquise issues e pull requests existentes antes de abrir outro. Use o modelo de relato de bug ou proposta de funcionalidade. Para bugs, inclua commit, sistema operacional, versões de Python e systemd, passos de reprodução, comportamento esperado e observado e saída sanitizada. Para propostas, explique problema, alternativas, escopo e implicações de segurança.

Não publique números de série USB reais, impressões digitais, nomes de hosts, endereços IP, credenciais ou logs privados. Utilize identificadores fictícios nos testes e exemplos. Relate suspeitas de vulnerabilidades por [SEGURANCA.md](SEGURANCA.md), não por um relato público de exploração.

## Checklist de revisão

Antes de enviar um pull request:

- Explique o problema, a solução, o comportamento afetado e as concessões envolvidas.
- Mantenha documentação técnica interna, ajuda da CLI, comentários do código, commits e descrições de PR em inglês. Traduções dos documentos comunitários ficam em `pt-BR/` e devem acompanhar os originais.
- Use código legível, focado e de acordo com as convenções existentes.
- Preserve a cobertura de regressão existente; adicione testes que falhariam antes da correção de um bug.
- Relate exatamente a validação realizada, inclusive falhas e verificações não executadas. Uma suíte offline aprovada não comprova segurança em hardware.
- Atualize a documentação afetada e a seção Unreleased do [CHANGELOG.md](CHANGELOG.md) para alterações visíveis ao usuário ou significativas para segurança.
- Declare assistência relevante de IA no PR, incluindo quais partes ela ajudou a produzir. Verifique as alterações propostas; não invente autoria, resultados de testes ou atribuição ao projeto original.
- Envie somente trabalhos que tenha direito de contribuir sob a licença MIT. Preserve avisos de direitos autorais e identifique materiais externos e suas licenças.

PRs são revisados antes do merge. O mantenedor pode solicitar alterações ou recusar propostas fora do escopo. Não faça merge em nome do mantenedor nem reescreva histórico compartilhado sem aprovação. Não há garantia de prazos de revisão ou resposta.

Siga o [código de conduta](CODIGO_DE_CONDUTA.md) nas discussões do projeto. Divergências técnicas respeitosas são bem-vindas.
