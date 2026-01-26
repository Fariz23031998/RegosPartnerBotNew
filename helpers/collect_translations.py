from pathlib import Path
import ast
import json

SKIP_DIRS = {
    "venv",
    ".venv",
    "__pycache__",
    "node_modules",
}


def collect_translations(project_path: str) -> dict[str, str]:
    project_path = Path(project_path).resolve()
    results: dict[str, str] = {}

    for py_file in _iter_python_files(project_path):
        try:
            tree = ast.parse(py_file.read_text(encoding="utf-8"))
        except SyntaxError:
            continue

        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue

            if not isinstance(node.func, ast.Name) or node.func.id != "t":
                continue

            if not node.args or not isinstance(node.args[0], ast.Constant):
                continue

            key = node.args[0].value
            if not isinstance(key, str):
                continue

            default_value = None
            for kw in node.keywords:
                if kw.arg == "default":
                    default_value = _extract_string(kw.value)

            if default_value:
                results[key] = default_value

    return results


def _iter_python_files(root: Path):
    for path in root.iterdir():
        if path.is_dir():
            if path.name in SKIP_DIRS:
                continue
            yield from _iter_python_files(path)
        elif path.is_file() and path.suffix == ".py":
            yield path


def _extract_string(node: ast.AST) -> str | None:
    """
    Extract string value from:
    - "text"
    - f"text {var}"
    - "a" + "b"
    - f"a" + f"b"
    """
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value

    if isinstance(node, ast.JoinedStr):
        parts = []
        for part in node.values:
            if isinstance(part, ast.Constant):
                parts.append(part.value)
            elif isinstance(part, ast.FormattedValue):
                if isinstance(part.value, ast.Name):
                    parts.append(f"{{{part.value.id}}}")
                else:
                    parts.append("{...}")
        return "".join(parts)

    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        left = _extract_string(node.left)

translations = collect_translations(r"C:\Projects\RegosPartnerBotNew")

for k, v in translations.items():
    print(k)
    print(v)
    print("-" * 40)

with open("translations.json", "w", encoding="utf-8") as f:
    json.dump(translations, f, indent=4, ensure_ascii=False)
