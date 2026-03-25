import sys
from setup import run_setup

# Verify all dependencies before importing third-party modules
if not run_setup():
    print("Dependency check failed. Exiting.")
    sys.exit(1)

from checkers import run_all_checks
from reporter import build_report, save_log


def main():
    print("Running network troubleshooter...\n")

    # 1. Run all checks
    results = run_all_checks()

    # 2. Build and print report
    report, overall = build_report(results)
    print(report)

    # 3. Save log
    log_path = save_log(report)
    print(f"\nLog saved -> {log_path}\n")


if __name__ == "__main__":
    main()
