import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def imported_roots(path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    roots = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            roots.add(node.module.split(".")[0])
    return roots


def test_subhashini_runtime_independent_modules_do_not_import_traci():
    paths = [
        *sorted((ROOT / "citybrain" / "agents").glob("*.py")),
        *sorted((ROOT / "citybrain" / "planner").glob("*.py")),
        ROOT / "citybrain" / "perception" / "state_adapter.py",
    ]
    offenders = [str(path.relative_to(ROOT)) for path in paths if "traci" in imported_roots(path)]
    assert offenders == []


def test_no_drone_agent_was_added():
    assert not (ROOT / "citybrain" / "agents" / "drone_agent.py").exists()
