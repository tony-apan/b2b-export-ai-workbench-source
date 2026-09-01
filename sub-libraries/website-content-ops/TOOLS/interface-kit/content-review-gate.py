#!/usr/bin/env python3
"""CLI wrapper for content_review_gate (ISS-102).

  digest <business-payload.json>
  verify <business-payload.json> <review-record.json> <object_type> <operation> <site_key> <site_id> <target_id-or-null>
"""
import sys
import content_review_gate as gate


def main():
    if len(sys.argv) < 3:
        print(__doc__); return 2
    if sys.argv[1] == "digest":
        try:
            print(gate.payload_digest(gate.load_json_strict(sys.argv[2]))); return 0
        except Exception as exc:
            print(f"CONTENT_REVIEW FAIL: {exc}"); return 1
    if sys.argv[1] == "verify" and len(sys.argv) == 9:
        try:
            payload = gate.load_json_strict(sys.argv[2])
            target = None if sys.argv[8] == "null" else sys.argv[8]
            rc, _ = gate.verify_payload_record(
                payload, sys.argv[3], expected_object_type=sys.argv[4],
                expected_operation=sys.argv[5], expected_site_key=sys.argv[6],
                expected_site_id=sys.argv[7], expected_target_id=target)
            return rc
        except Exception as exc:
            print(f"CONTENT_REVIEW FAIL: {exc}"); return 1
    print(__doc__); return 2


if __name__ == "__main__":
    sys.exit(main())
