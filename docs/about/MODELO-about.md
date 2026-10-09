# [Domínio] — about.md

> Modelo a preencher a partir da implementação. Os campos entre colchetes não constituem fatos sobre o sistema.

## Base e verificação

- Repositório: G4TTI/Attena-Assistant.
- Commit/ref revisado: [SHA completo e referência].
- Data da revisão: [data real].
- Método: [leitura estática / testes executados, identificados abaixo].
- Mudanças locais incluídas: [nenhuma / arquivos e escopo].
- Estado: [verificado / parcial, com escopo pendente].

## Responsabilidade

[O que o domínio faz, seus limites e como participa da jornada do usuário.]

## Fontes e pontos de entrada

| Arquivo / símbolo | Responsabilidade | Relações |
|---|---|---|
| [caminho e símbolo reais] | [responsabilidade] | [domínios e dependências] |

## Contratos de telas e APIs

| Método / rota ou ação | Autorização | Entrada / validação | Saída / erro | Efeito colateral |
|---|---|---|---|---|
| [valor confirmado] | [dono, papel, sessão, CSRF] | [campos e regras] | [JSON/HTML/redirect, status] | [DB, API externa, job] |

Inclua contratos HTMX/JavaScript quando existirem: fragmentos, targets, eventos, atualização automática, cancelamento de requisições e estado de seleção. Não presuma equivalência entre REST e interface.

## Funções, fluxo e regras

- [Função/classe]: [entrada → processamento → retorno], validações, erros e efeitos.
- [Fluxo completo]: tela/rota → serviço → persistência/integração → resposta.
- [Regras e estados confirmados, incluindo transições e concorrência quando relevantes].

As funções auxiliares podem constar em tabela ou inventário anexo. Todas devem ter fonte e domínio identificáveis; não copie implementações inteiras.

## Dados, autorização e dependências

- Tabelas/campos lidos e gravados: [nomes, sem dados reais].
- Isolamento e papéis: [checagens reais].
- Criptografia/retenção: [o que realmente é cifrado, quando é apagado e o que permanece].
- Integrações/configuração: [nomes de variáveis, defaults comprovados e falhas esperadas].
- Dependências compartilhadas: [links relativos para outros abouts].

## Testes e evidência

| Arquivo / teste | Cenário | Evidência disponível |
|---|---|---|
| [caminho::símbolo] | [cenário] | [somente lido / executado + resultado] |

Não foi executado: [explicitar]. Pendências de validação: [explicitar].

## Cuidados e lacunas

- Comportamento confirmado: [fato e fonte].
- Divergência encontrada: [implementação versus comentário/documento].
- Hipótese ou risco a investigar: [condição e efeito possíveis, sem afirmar exploração].
- Operações com efeitos: [por exemplo, bootstrap, migração, envio ou cobrança].

## Quando atualizar

[Mudanças nos arquivos/símbolos, rotas, regras, dados, integrações, estados, templates ou testes que invalidam este documento.]

Documentos relacionados: [links relativos reais].
