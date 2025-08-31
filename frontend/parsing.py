"""Parsing utilities for converting PyTorch nn.Module code into an intermediate graph.

Current approach (MVP):
1. Attempt to exec the provided code in a restricted namespace to locate subclasses of nn.Module.
2. Instantiate the first discovered module class (if possible) without arguments.
3. Perform a forward pass with a dummy input if an `example_input` or shape hint is found (future work).
4. Fallback to static AST parsing to extract `nn.` layer assignments as a simple ordered list.

The intermediate representation (IR) is intentionally simple:
{
  "nodes": [ {"id": str, "type": str, "label": str } ],
  "edges": [ {"source": id, "target": id, "label": optional str } ],
  "meta": {"detected_module": str}
}

Security: we avoid passing user code to powerful builtins; this is still a risk area and should
be sandboxed further for production (e.g., via subprocess with time/resource limits).
"""

from __future__ import annotations

import ast
import builtins
import types
import uuid
from dataclasses import dataclass
from typing import Dict, List, Any

SAFE_BUILTINS = {k: getattr(builtins, k) for k in [
    "abs", "min", "max", "range", "len", "print", "float", "int", "str", "list", "dict", "set", "tuple"
]}


def _find_module_classes(tree: ast.AST) -> List[ast.ClassDef]:
    classes = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            for base in node.bases:
                if isinstance(base, ast.Attribute) and base.attr == "Module":
                    classes.append(node)
                elif isinstance(base, ast.Name) and base.id in {"Module", "nn.Module"}:
                    classes.append(node)
    return classes


def _simple_layer_sequence_from_class(cls_node: ast.ClassDef) -> List[Dict[str, str]]:
    layers: List[Dict[str, str]] = []
    for node in cls_node.body:
        if isinstance(node, ast.FunctionDef) and node.name == "__init__":
            for stmt in node.body:
                if isinstance(stmt, ast.Assign):
                    target_names = [t.attr for t in stmt.targets if isinstance(t, ast.Attribute)]
                    if not target_names:
                        continue
                    if isinstance(stmt.value, ast.Call):
                        callee = ast.unparse(stmt.value.func) if hasattr(ast, 'unparse') else getattr(stmt.value.func, 'id', 'Layer')
                        if callee.startswith("nn."):
                            layer_type = callee.split("nn.", 1)[1]
                            for name in target_names:
                                layers.append({
                                    "id": str(uuid.uuid4())[:8],
                                    "type": layer_type,
                                    "label": f"{name}: {layer_type}",
                                })
    return layers


def parse_pytorch_code_to_graph(code: str) -> Dict[str, Any]:
    """Parse PyTorch nn.Module source code into a lightweight graph IR.

    This MVP prioritizes robustness over completeness. Edges are inferred linearly.
    """
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return {"nodes": [], "edges": [], "meta": {"error": "syntax_error"}}

    module_classes = _find_module_classes(tree)
    if not module_classes:
        return {"nodes": [], "edges": [], "meta": {"warning": "no nn.Module subclass found"}}

    primary = module_classes[0]
    layers = _simple_layer_sequence_from_class(primary)
    nodes = layers
    edges = []
    for i in range(len(nodes) - 1):
        edges.append({"source": nodes[i]["id"], "target": nodes[i + 1]["id"], "label": "flow"})

    return {
        "nodes": nodes,
        "edges": edges,
        "meta": {"detected_module": primary.name, "node_count": len(nodes)},
    }


__all__ = ["parse_pytorch_code_to_graph"]
