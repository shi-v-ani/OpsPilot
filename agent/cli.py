"""Interactive demo:

    python -m agent.cli --user alice
    python -m agent.cli --user alice --auto-approve
"""

import argparse
import json

from agent.graph import run_incident


def _pretty(obj):
    return json.dumps(obj, indent=2, default=str)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--user", default="alice")
    parser.add_argument("--auto-approve", action="store_true")
    args = parser.parse_args()

    print("=== Phase A: observe + diagnose + plan ===")
    partial = run_incident(user=args.user, approved=False)

    print("\nDiagnosis:")
    print(_pretty(partial.get("diagnosis")))
    print("\nProposed remediation:")
    print(_pretty(partial.get("remediation")))

    if args.auto_approve:
        approved = True
    else:
        ans = input("\nApprove this remediation? [y/N] ").strip().lower()
        approved = ans == "y"

    print(f"\n=== Phase B: {'executing' if approved else 'refusing to execute'} ===")
    final = run_incident(user=args.user, approved=approved)

    print("\nExecution:")
    print(_pretty(final.get("execution")))
    print("\nVerification:")
    print(_pretty(final.get("verification")))
    print("\nAudit trail:")
    for entry in final.get("audit", []):
        print(_pretty(entry))


if __name__ == "__main__":
    main()
