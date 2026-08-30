#!/usr/bin/env python3
"""Regression checks for source-chain helper --json stdout contracts."""

from __future__ import annotations

from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
SOURCE_CHAIN_HELPERS = [
    "prepare_source_site_package.py",
    "apply_refined_source_wiki.py",
    "validate_refined_source_wiki_contract.py",
    "run_source_file_rehearsal.py",
    "make_source_confirmation_brief.py",
    "make_source_input_requirements.py",
    "make_resolved_source_input_gaps.py",
    "validate_source_confirmation_brief.py",
    "prepare_source_confirmation_next_step.py",
    "apply_source_confirmation_next_step.py",
    "apply_create_preflight_to_source_rehearsal.py",
    "apply_created_site_evidence_to_source_rehearsal.py",
    "prepare_source_next_stage.py",
    "prepare_confirmed_site_execution.py",
    "bind_created_site_to_artifacts.py",
    "prepare_created_site_schema_capture.py",
    "apply_pages_site_info_execution.py",
    "apply_taxonomy_execution.py",
    "prepare_schema_manifest_sample.py",
    "apply_manifest_sample_upload.py",
    "prepare_batch_upload_publish.py",
    "apply_batch_upload_publish.py",
    "apply_forms_media_settings.py",
    "apply_launch_acceptance.py",
    "validate_source_run_acceptance.py",
]


def test_json_stdout_branches_are_pure() -> None:
    for name in SOURCE_CHAIN_HELPERS:
        path = SCRIPT_DIR / name
        lines = path.read_text(encoding="utf-8").splitlines()
        json_lines = [index for index, line in enumerate(lines) if line.strip() == "if args.json:"]
        assert json_lines, f"{name}: expected an if args.json branch"
        for index in json_lines:
            previous = "\n".join(lines[max(0, index - 4) : index])
            assert "print(" not in previous, f"{name}: human print appears before --json branch near line {index + 1}"
            following = "\n".join(lines[index + 1 : min(len(lines), index + 4)])
            assert "json.dumps" in following, f"{name}: --json branch should print JSON directly near line {index + 1}"


if __name__ == "__main__":
    test_json_stdout_branches_are_pure()
    print("source-chain JSON stdout contract tests passed.")
