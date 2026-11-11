# Desafio diário #02 — Validador de saída de um classificador de delivery

Exercício do desafio diário de preparação para a vaga de **AI Builder**.

## Contexto

Um modelo de IA classifica mensagens de clientes de um app de delivery e devolve
um JSON estruturado. Modelos de linguagem nem sempre seguem o formato pedido:
podem inventar categorias, devolver `"sim"` em vez de `true` ou dar uma
confiança fora do intervalo esperado. Antes de usar essa resposta no sistema
(abrir ticket, priorizar a fila, acionar um atendente), é preciso **validar a
saída do modelo**.

Este projeto é um validador em Python, **somente com a biblioteca padrão**, que
lê a resposta do classificador e diz se ela respeita o contrato.

## Estrutura

```
.
├── validator.py      # Validador (lê o JSON, lista erros, define o código de saída)
├── output.json       # Resposta a ser validada por padrão (hoje contém um caso rejeitado)
├── examples/
│   ├── valido.json                                  # Resposta aceita
│   ├── rejeitado_confidence_fora_do_intervalo.json  # Rejeitada: confidence = 1.5
│   └── rejeitado_varios_erros.json                  # Rejeitada: 6 erros ao mesmo tempo
└── README.md
```

## Contrato da resposta

| Campo                | Regra |
|----------------------|-------|
| `category`           | Uma de: `Atraso na entrega`, `Pedido incompleto`, `Problema com pagamento`, `Cancelamento`, `Outros` |
| `priority`           | Uma de: `baixa`, `média`, `alta` |
| `summary`            | String não vazia (só espaços não vale) |
| `next_action`        | String não vazia (só espaços não vale) |
| `needs_human_review` | Booleano (`true` ou `false`) |
| `confidence`         | Número entre 0 e 1, inclusive. `true`/`false` são rejeitados, assim como `NaN` e `Infinity` |

Todos os campos são obrigatórios. Campos extras são ignorados. Os valores são
comparados exatamente, com diferença entre maiúsculas e minúsculas e acentos
(`media` sem acento é rejeitado).

## Como executar

Requisito: Python 3.8 ou superior. Não há dependências para instalar (`json` e
`sys` já vêm com o Python).

```bash
python validator.py                           # valida ./output.json
python validator.py examples/valido.json      # valida outro arquivo
```

No Windows, se `python` não funcionar, use `py validator.py`.

### Códigos de saída

| Código | Significado |
|--------|-------------|
| `0`    | JSON válido |
| `1`    | JSON lido, mas com um ou mais erros de validação |
| `2`    | Arquivo inexistente, ilegível ou com JSON malformado |

Para conferir o código depois de executar:

```bash
echo $?            # bash / Git Bash
echo $LASTEXITCODE # PowerShell
```

Como o código de saída é diferente de zero em caso de falha, o validador pode
ser usado em scripts e pipelines de CI para barrar respostas inválidas.

## Exemplo de resposta aceita

`examples/valido.json`:

```json
{
  "category": "Atraso na entrega",
  "priority": "alta",
  "summary": "Cliente relata que o pedido está 50 minutos atrasado e ainda não saiu para entrega.",
  "next_action": "Contatar o restaurante para confirmar o status do pedido e informar nova previsão ao cliente.",
  "needs_human_review": false,
  "confidence": 0.92
}
```

```
$ python validator.py examples/valido.json
OK: examples/valido.json é válido.
```

## Exemplo de resposta rejeitada

`examples/rejeitado_confidence_fora_do_intervalo.json` (mesmo conteúdo do
`output.json` atual):

```json
{
"category": "Outros",
"priority": "média",
"summary": "O cliente expressou insatisfação com o atendimento recebido.",
"next_action": "Coletar mais detalhes sobre a insatisfação e encaminhar ao setor de atendimento/suporte.",
"needs_human_review": true,
"confidence": 1.5
}
```

```
$ python validator.py examples/rejeitado_confidence_fora_do_intervalo.json
FALHA: examples/rejeitado_confidence_fora_do_intervalo.json contém 1 erro(s):
  - 'confidence' deve estar entre 0 e 1 (inclusive), mas recebeu 1.5.
```

Código de saída: `1`.

### Por que foi rejeitada

Quase toda a resposta está correta:

- `category` é `Outros`, um valor permitido;
- `priority` é `média`, com acento, um valor permitido;
- `summary` e `next_action` são textos preenchidos;
- `needs_human_review` é o booleano `true`.

O problema está só em `confidence`. Ela representa uma **probabilidade**, então
precisa estar entre 0 e 1. O valor `1.5` (150%) não existe como probabilidade.
Isso costuma indicar que o modelo misturou escalas (por exemplo, de 0 a 10 ou
porcentagem) ou simplesmente inventou o número.

Aceitar esse valor teria consequências reais. Uma regra como "enviar para
revisão humana se `confidence < 0.7`" passaria a funcionar errado, e métricas e
dashboards de confiança ficariam distorcidos. Por isso o validador **não tenta
corrigir** o número (por exemplo, limitando a 1.0). Ele rejeita a resposta para
que ela seja gerada de novo ou tratada manualmente.

Para a resposta ser aceita, basta trocar `confidence` por um valor válido, como
`0.85`.

## Outro exemplo rejeitado: vários erros de uma vez

`examples/rejeitado_varios_erros.json`:

```json
{
  "category": "Reembolso",
  "priority": "urgente",
  "summary": "",
  "needs_human_review": "sim",
  "confidence": true
}
```

```
$ python validator.py examples/rejeitado_varios_erros.json
FALHA: examples/rejeitado_varios_erros.json contém 6 erro(s):
  - Campo obrigatório ausente: 'next_action'.
  - 'category' inválido: 'Reembolso'. Valores aceitos: 'Atraso na entrega', 'Pedido incompleto', 'Problema com pagamento', 'Cancelamento', 'Outros'.
  - 'priority' inválido: 'urgente'. Valores aceitos: 'baixa', 'média', 'alta'.
  - 'summary' não pode ser vazio ou conter apenas espaços.
  - 'needs_human_review' deve ser booleano (true/false), mas recebeu string: 'sim'.
  - 'confidence' deve ser um número entre 0 e 1, mas recebeu booleano: True.
```

| Campo                | Valor recebido | Motivo da rejeição |
|----------------------|----------------|--------------------|
| `next_action`        | (ausente)      | Campo obrigatório não enviado |
| `category`           | `"Reembolso"`  | Categoria inventada pelo modelo, fora da lista |
| `priority`           | `"urgente"`    | Só existem `baixa`, `média` e `alta` |
| `summary`            | `""`           | Texto vazio não descreve a solicitação |
| `needs_human_review` | `"sim"`        | É uma string, não o booleano `true` |
| `confidence`         | `true`         | Booleano não é número. Em Python `True == 1`, por isso o validador barra esse caso de forma explícita |

O validador lista **todos** os erros de uma vez, em vez de parar no primeiro.
Isso ajuda a corrigir o prompt ou o modelo de uma só vez.

## Decisões de implementação

- **Somente biblioteca padrão:** nada para instalar, roda em qualquer Python 3.8+.
- **`bool` não conta como número:** em Python, `isinstance(True, int)` é `True`, então a checagem de `confidence` exclui booleanos explicitamente.
- **`NaN`/`Infinity` rejeitados:** o módulo `json` do Python aceita esses valores por padrão, mas eles não fazem parte do JSON padrão.
- **Arquivos com BOM aceitos:** a leitura usa `utf-8-sig`, compatível com arquivos salvos pelo PowerShell no Windows.
- **Erros em português e no `stderr`:** a mensagem de sucesso vai para o `stdout`.

## Uso como módulo

```python
from validator import validate

erros = validate({"category": "Outros", ...})
if erros:
    print(erros)
```
