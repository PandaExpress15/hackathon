from __future__ import annotations

import ast
from pathlib import Path


def test_analysis_modules_do_not_call_eval_exec_or_os_system():
    root = Path(__file__).resolve().parents[1] / "src" / "careerproof"
    relevant = [
        "question_router.py",
        "query_plan.py",
        "query_validator.py",
        "query_executor.py",
        "analysis_engine.py",
    ]
    for filename in relevant:
        tree = ast.parse((root / filename).read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    assert node.func.id not in {"eval", "exec"}
                if isinstance(node.func, ast.Attribute):
                    assert not (
                        isinstance(node.func.value, ast.Name)
                        and node.func.value.id == "os"
                        and node.func.attr == "system"
                    )
