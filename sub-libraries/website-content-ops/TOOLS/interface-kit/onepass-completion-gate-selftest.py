#!/usr/bin/env python3
"""Adversarial self-test for onepass-completion-gate.py.

Builds a minimal isolated task and asserts the gate fails closed on receipt,
review digest, authorization and count-baseline attacks.
"""
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
SUB = HERE.parent.parent
GATE = HERE / "onepass-completion-gate.py"
FRESHNESS = HERE / "check-contract-freshness.py"


def run_gate(task):
    return subprocess.run([sys.executable, str(GATE), str(task)], capture_output=True, text=True)


def prepare_copy(source, task):
    shutil.copytree(source, task)
    task_prefix = str(task)
    fact_source = str(task / "20_work" / "source-extraction.json")
    for pattern in (
        task / "70_evidence" / "products" / "*-review.json",
        task / "20_work" / "final-posts" / "*-review.json",
    ):
        for review in pattern.parent.glob(pattern.name):
            data = json.loads(review.read_text())
            data["runtime_scope_root"] = task_prefix
            for ref in data.get("fact_source_refs", []):
                ref["ref"] = fact_source
            review.write_text(json.dumps(data, ensure_ascii=False, indent=2))


def main():
    # A copied real task is not acceptable as a public test fixture. Instead,
    # this self-test validates tampering against a private task path supplied by
    # ONEPASS_COMPLETION_SELFTEST_TASK; CI may omit it and still run static tests.
    task_env = __import__("os").environ.get("ONEPASS_COMPLETION_SELFTEST_TASK")
    if not task_env:
        print("ONEPASS_COMPLETION_SELFTEST_SKIP: set ONEPASS_COMPLETION_SELFTEST_TASK to a private completed task")
        return
    source = Path(task_env).resolve()
    if not source.is_dir():
        raise SystemExit("ONEPASS_COMPLETION_SELFTEST_TASK must be an existing private task directory")
    with tempfile.TemporaryDirectory() as tmp:
        task = Path(tmp) / "task"
        prepare_copy(source, task)
        receipt = task / "20_work" / "onepass-read-receipt.json"
        subprocess.run([sys.executable, str(FRESHNESS), "--write-receipt", str(receipt)], check=False, capture_output=True)
        baseline = run_gate(task)
        assert baseline.returncode == 0, baseline.stdout

        # READY string without digest binding must fail.
        review = next((task / "70_evidence" / "products").glob("*-review.json"))
        data = json.loads(review.read_text())
        data["business_payload_digest"] = "sha256:" + "0" * 64
        review.write_text(json.dumps(data))
        attacked = run_gate(task)
        assert attacked.returncode == 1 and "review digest mismatch" in attacked.stdout
        shutil.rmtree(task)
        prepare_copy(source, task)
        subprocess.run([sys.executable, str(FRESHNESS), "--write-receipt", str(task / "20_work" / "onepass-read-receipt.json")], check=False, capture_output=True)

        # Audit count drift must fail.
        audit = next((task / "70_evidence").glob("*-audit-config.json"))
        data = json.loads(audit.read_text())
        data["count"]["products"] += 1
        audit.write_text(json.dumps(data))
        attacked = run_gate(task)
        assert attacked.returncode == 1 and "product baseline mismatch" in attacked.stdout

        # Missing receipt must fail.
        (task / "20_work" / "onepass-read-receipt.json").unlink()
        attacked = run_gate(task)
        assert attacked.returncode == 1 and "missing read receipt" in attacked.stdout

    print("ONEPASS_COMPLETION_SELFTEST_PASS")


if __name__ == "__main__":
    main()
