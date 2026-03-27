import sys
from setup import run_setup

# Verify all dependencies before importing third-party modules
if not run_setup():
    print("Dependency check failed. Exiting.")
    sys.exit(1)

from checkers import run_all_checks
from reporter import build_report, save_log

# IT Ticket System integration — optional, fails gracefully if server is not running
try:
    from integrations.network_client import create_tickets_for_failures, prompt_save_as_ticket
    TICKET_SYSTEM_ENABLED = True
except ImportError:
    TICKET_SYSTEM_ENABLED = False


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
    
    # 4. Ticket integration
    if TICKET_SYSTEM_ENABLED:
        if "FAIL" in overall:
            # Auto-create tickets for each failed check
            print("  [TICKET] Creating tickets for failed checks...")
            create_tickets_for_failures(results, report)
        else:
            # All checks passed — offer to save as a record
            prompt_save_as_ticket(report)
    else:
        print("  [TICKET] Skipped — integrations module not found.")


if __name__ == "__main__":
    main()
