"""Valida a resposta JSON de um classificador de solicitações de delivery.

Uso:
    python validator.py [caminho_do_arquivo.json]

Se nenhum caminho for informado, lê "output.json" no diretório atual.
Códigos de saída:
    0 - JSON válido
    1 - JSON lido, mas com erros de validação
    2 - Arquivo inexistente, ilegível ou com JSON malformado
"""

import json
import sys

ALLOWED_CATEGORIES = (
    "Atraso na entrega",
    "Pedido incompleto",
    "Problema com pagamento",
    "Cancelamento",
    "Outros",
)
ALLOWED_PRIORITIES = ("baixa", "média", "alta")
REQUIRED_FIELDS = (
    "category",
    "priority",
    "summary",
    "next_action",
    "needs_human_review",
    "confidence",
)

EXIT_OK = 0
EXIT_INVALID = 1
EXIT_READ_ERROR = 2


def _type_name(value):
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "booleano"
    if isinstance(value, (int, float)):
        return "número"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return "lista"
    if isinstance(value, dict):
        return "objeto"
    return type(value).__name__


def _validate_enum(data, field, allowed, errors):
    value = data[field]
    if not isinstance(value, str):
        errors.append(
            f"'{field}' deve ser string, mas recebeu {_type_name(value)}: {value!r}."
        )
    elif value not in allowed:
        options = ", ".join(f"'{a}'" for a in allowed)
        errors.append(f"'{field}' inválido: {value!r}. Valores aceitos: {options}.")


def _validate_non_empty_string(data, field, errors):
    value = data[field]
    if not isinstance(value, str):
        errors.append(
            f"'{field}' deve ser string, mas recebeu {_type_name(value)}: {value!r}."
        )
    elif not value.strip():
        errors.append(f"'{field}' não pode ser vazio ou conter apenas espaços.")


def validate(data):
    """Retorna a lista de mensagens de erro (vazia se o JSON for válido)."""
    errors = []

    if not isinstance(data, dict):
        return [f"O JSON raiz deve ser um objeto, mas recebeu {_type_name(data)}."]

    missing = [f for f in REQUIRED_FIELDS if f not in data]
    for field in missing:
        errors.append(f"Campo obrigatório ausente: '{field}'.")

    if "category" not in missing:
        _validate_enum(data, "category", ALLOWED_CATEGORIES, errors)

    if "priority" not in missing:
        _validate_enum(data, "priority", ALLOWED_PRIORITIES, errors)

    for field in ("summary", "next_action"):
        if field not in missing:
            _validate_non_empty_string(data, field, errors)

    if "needs_human_review" not in missing:
        value = data["needs_human_review"]
        if not isinstance(value, bool):
            errors.append(
                "'needs_human_review' deve ser booleano (true/false), "
                f"mas recebeu {_type_name(value)}: {value!r}."
            )

    if "confidence" not in missing:
        value = data["confidence"]
        # bool é subclasse de int em Python, então precisa ser excluído explicitamente.
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            errors.append(
                "'confidence' deve ser um número entre 0 e 1, "
                f"mas recebeu {_type_name(value)}: {value!r}."
            )
        elif not (0 <= value <= 1):  # NaN também falha aqui
            errors.append(
                f"'confidence' deve estar entre 0 e 1 (inclusive), mas recebeu {value!r}."
            )

    return errors


def _reject_constant(name):
    raise ValueError(f"valor não permitido em JSON padrão: {name}")


def load_json(path):
    # utf-8-sig aceita arquivos com ou sem BOM (comum no PowerShell do Windows).
    with open(path, encoding="utf-8-sig") as f:
        # Rejeita NaN/Infinity, que o módulo json aceita por padrão.
        return json.load(f, parse_constant=_reject_constant)


def main(argv=None):
    # Garante acentos corretos em qualquer terminal (ex.: Git Bash no Windows).
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")

    argv = sys.argv[1:] if argv is None else argv
    path = argv[0] if argv else "output.json"

    try:
        data = load_json(path)
    except FileNotFoundError:
        print(f"ERRO: arquivo não encontrado: {path}", file=sys.stderr)
        return EXIT_READ_ERROR
    except json.JSONDecodeError as e:
        print(
            f"ERRO: JSON malformado em {path} (linha {e.lineno}, coluna {e.colno}): {e.msg}",
            file=sys.stderr,
        )
        return EXIT_READ_ERROR
    except (OSError, UnicodeDecodeError, ValueError) as e:
        print(f"ERRO: não foi possível ler {path}: {e}", file=sys.stderr)
        return EXIT_READ_ERROR

    errors = validate(data)
    if errors:
        print(f"FALHA: {path} contém {len(errors)} erro(s):", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        return EXIT_INVALID

    print(f"OK: {path} é válido.")
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
