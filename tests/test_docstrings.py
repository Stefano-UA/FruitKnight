"""Enforces the Sphinx field-syntax docstring policy on the whole code base."""

from __future__ import annotations

import ast
import re
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src" / "fruit_knight"
ARTICLE = re.compile(r":(?:param\s+\w+|return|raises\s+[\w.]+):\s*(?:The|A|An)\b", re.IGNORECASE)


def _returns_value(func: ast.AST) -> bool:
    """Check whether a function returns something other than ``None``.

    :param func: function definition node.
    :type func: ast.AST
    :return: True when a ``return <value>`` statement exists directly in this function.
    :rtype: bool
    """
    stack = list(ast.iter_child_nodes(func))
    while stack:
        node = stack.pop()
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)):
            continue  # nested scopes have their own returns
        if isinstance(node, ast.Return) and node.value is not None and not (
            isinstance(node.value, ast.Constant) and node.value.value is None
        ):
            return True
        stack.extend(ast.iter_child_nodes(node))
    return False


def _violations() -> list[str]:
    """Collect docstring policy violations.

    :return: human-readable problems, empty when compliant.
    :rtype: list[str]
    """
    problems: list[str] = []
    for path in sorted(SRC.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        rel = path.relative_to(SRC.parent)
        if path.name != "__init__.py" or path.stat().st_size > 0:
            if ast.get_docstring(tree) is None:
                problems.append(f"{rel}: missing module docstring")
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                doc = ast.get_docstring(node)
                if not doc:
                    problems.append(f"{rel}:{node.lineno} class {node.name}: missing docstring")
                elif ARTICLE.search(doc):
                    problems.append(f"{rel}:{node.lineno} class {node.name}: article in field")
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                where = f"{rel}:{node.lineno} {node.name}"
                doc = ast.get_docstring(node)
                if not doc:
                    problems.append(f"{where}: missing docstring")
                    continue
                args = node.args
                names = [a.arg for a in args.posonlyargs + args.args + args.kwonlyargs if a.arg not in ("self", "cls")]
                names += [a.arg for a in (args.vararg, args.kwarg) if a is not None]
                for name in names:
                    if f":param {name}:" not in doc:
                        problems.append(f"{where}: missing :param {name}:")
                    if f":type {name}:" not in doc:
                        problems.append(f"{where}: missing :type {name}:")
                if _returns_value(node) and (":return:" not in doc or ":rtype:" not in doc):
                    problems.append(f"{where}: missing :return:/:rtype:")
                if ARTICLE.search(doc):
                    problems.append(f"{where}: field description starts with an article")
    return problems


def test_docstrings_follow_sphinx_field_policy() -> None:
    """Every module, class, function and method is documented with concise Sphinx fields."""
    problems = _violations()
    assert not problems, "\n".join(problems[:60])
