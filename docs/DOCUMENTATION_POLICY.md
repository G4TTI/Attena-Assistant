# Política de documentação técnica (about.md)

Vale para todo agente que trabalhar neste repositório, inclusive subagentes, e
para pessoas que mantêm a documentação. O objetivo é localizar rápido o que uma
tarefa afeta sem tratar documento como prova de comportamento.

## Onde fica cada coisa

| Arquivo | Papel |
|---|---|
| [`about.md`](../about.md) (raiz) | Índice curto: base revisada, estado de cada domínio, arquivos compartilhados e divergências conhecidas. |
| `docs/about/<dominio>/about.md` | Um documento por domínio (15 na estrutura inicial). Formato em [`MODELO-about.md`](about/MODELO-about.md). |
| [`docs/about/build_inventory.py`](about/build_inventory.py) | Gera `INVENTARIO.json` e `ROTAS.md` por análise estática (AST/texto) dos blobs do Git; não importa nem executa o app. |
| [`docs/about/INVENTARIO.json`](about/INVENTARIO.json), [`docs/about/ROTAS.md`](about/ROTAS.md) | Saídas geradas: arquivos, funções/métodos, classes, rotas, templates e testes de uma revisão. Não editar à mão. |
| [`docs/SECURITY_AND_PRIVACY.md`](SECURITY_AND_PRIVACY.md) | Documento normativo de segurança e privacidade. O about.md de privacidade aponta para ele; não o duplica. |
| [`CLAUDE.md`](../CLAUDE.md) | Notas operacionais e armadilhas, mais o protocolo curto que remete a esta política. |

O nome `about.md` não faz nenhum arquivo ser carregado automaticamente. Leia os
documentos de propósito, e só os necessários.

## Hierarquia de evidência

- O **código na revisão atual** é a evidência do comportamento implementado.
- **Instruções explícitas do usuário e requisitos** definem o comportamento
  desejado. Se o código diverge deles, registre a divergência; não transforme um
  bug em requisito nem "corrija" o requisito para caber no código.
- **Documentação** (about.md, README, comentários, docstrings) é um mapa. Sem
  confirmação no código, é hipótese.

Ao escrever, rotule o nível de cada afirmação relevante:

| Rótulo | Significa |
|---|---|
| Lido | Confirmado lendo o código da revisão registrada (cite arquivo e símbolo). |
| Testado | Teste executado de fato: comando, revisão, data e resultado. |
| Validado em ambiente | Exercitado no ambiente de teste (navegador, WAHA, Google...), com data e o que foi visto. |
| Hipótese | Inferência ainda não confirmada. |
| Pendente / lacuna | Ainda não analisado, ou sem como confirmar. |

Nunca declare testes executados ou integrações validadas quando só leu o código.

## Ao começar uma tarefa

1. Leia o [`about.md`](../about.md) raiz e escolha **somente** os domínios
   afetados, mais as dependências compartilhadas que eles apontam e que a tarefa
   toca. Não leia todos os domínios por padrão.
2. Confira a base de cada documento usado: a revisão e as fontes declaradas.
   Data sozinha não prova atualidade. Com histórico disponível, compare desde a
   base registrada, por exemplo:
   `git log --oneline <base>..HEAD -- <fontes do documento>`.
   Se houve mudança nas fontes, releia esses trechos antes de confiar no texto.
   Sem histórico (cópia sem `.git`, clone raso), releia o escopo e declare a
   limitação.
3. Confirme no código as afirmações que vão orientar a mudança.
4. Antes de alterar, identifique o que pode ser afetado:
   - contratos (rotas, parâmetros, respostas, fragmentos/targets HTMX, JS);
   - autorização (sessão, dono do recurso, papel admin/owner, CSRF) e
     isolamento por usuário;
   - dados persistidos (tabelas, campos, migrações) e privacidade (cifra,
     retenção, logs; ver `SECURITY_AND_PRIVACY.md`);
   - integrações (WAHA, Google Calendar, gateway de pagamento) e jobs de fundo;
   - efeitos colaterais (envio de mensagem, cobrança, expurgo) e os testes que
     cobrem ou deveriam cobrir isso.

## Ao concluir uma alteração funcional

- Atualize só os about.md dos domínios impactados, o índice raiz se o estado ou
  a divisão mudou, e regenere o inventário quando funções, classes, rotas,
  templates ou testes mudaram:
  `python3 -I docs/about/build_inventory.py` (lê o commit `HEAD`; faça o commit
  do código antes, ou passe `--rev`).
- Inclusão ou remoção de função, rota, campo, regra, estado, job, template ou
  dependência precisa aparecer no domínio correspondente.
- Ao revisar um documento contra o código, atualize "Base e verificação"
  (commit, data, método, estado). Não altere documento só para trocar a data.
- Mudança sem impacto documental: encerre com uma justificativa curta no
  relatório final, sem tocar nos documentos.

## Arquivos compartilhados

Arquivos como `web/routes.py`, `main.py`, `models.py`, `base.html` e
`_components.html` servem a vários domínios. A divisão por seção/símbolo está no
índice raiz. Cada regra é descrita **uma vez**, no domínio dono do símbolo; os
outros domínios usam link relativo. A tela pode pertencer a um domínio e a regra
de negócio a outro (ex.: troca de senha é tela de Configurações e regra de
Autenticação).

## Delegação a subagentes

Ao delegar, passe ao subagente: a revisão (SHA), os caminhos dos about.md
relevantes, as fontes a ler, os invariantes que não podem quebrar (isolamento
por usuário, privacidade/cifra, admin nunca decifra conteúdo, nenhum segredo em
documento) e a exigência de rotular evidências como acima. O agente principal
revisa referências cruzadas, duplicações e a coerência final.

## Conteúdo proibido em documentação

Nunca copie `.env`, bancos, backups, cookies, chaves, tokens, QR codes, senhas
ou dados de clientes. Documente **nomes** de variáveis e use exemplos fictícios
(`usuario@example.com`, `+55 11 90000-0000`). Não cole implementações inteiras:
descreva e aponte arquivo/símbolo.

## Relatório final de cada tarefa

Informe: documentos consultados; documentos atualizados (ou a justificativa para
não atualizar); validações realmente feitas (leitura, testes com resultado,
validação em ambiente); pendências concretas.

## Estados de um documento de domínio

- **pendente**: estrutura criada, conteúdo não analisado.
- **parcial**: parte do escopo verificada; o que falta está listado.
- **verificado**: todo o escopo conferido contra a revisão registrada.
