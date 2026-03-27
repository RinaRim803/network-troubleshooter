"""
integrations/network_client.py
IT Ticket System integration for network-troubleshooter.

Single responsibility: convert network diagnostic results into ticket
payloads and send them to the IT Ticket System API.

Public interface:
    create_tickets_for_failures(results, report)
        Called from main.py when any check returns FAIL.
        Creates one ticket per failed check.

    prompt_save_as_ticket(report)
        Called from main.py when all checks pass.
        Asks the user whether to save the run as a ticket for record-keeping.
"""

import requests

TICKET_API_URL = "http://localhost:5000/api/tickets"

# Maps each check key to a ticket title and description template
# Only checks that can actually FAIL are listed here
_FAIL_CONFIG = {
    "dns": {
        "title":       "DNS Resolution Failed",
        "description": (
            "DNS resolution check failed — unable to resolve public hostnames.\n"
            "This typically indicates a DNS server issue or complete connectivity loss.\n\n"
            "Diagnostic Report:\n{report}"
        ),
    },
    "gateway": {
        "title":       "Default Gateway Unreachable",
        "description": (
            "The default gateway is not responding to ping.\n"
            "This typically indicates a local network issue (router/switch down, bad cable).\n\n"
            "Diagnostic Report:\n{report}"
        ),
    },
    "internet": {
        "title":       "Internet Connectivity Lost",
        "description": (
            "Internet reachability check failed — unable to reach public DNS servers (8.8.8.8, 1.1.1.1).\n"
            "Gateway may be up but ISP or upstream connection is down.\n\n"
            "Diagnostic Report:\n{report}"
        ),
    },
    "interfaces": {
        "title":       "No Active Network Interface Detected",
        "description": (
            "No active network interfaces with a valid IP address were found.\n"
            "Network adapter may be disabled or disconnected.\n\n"
            "Diagnostic Report:\n{report}"
        ),
    },
    "ports": {
        "title":       "Key Ports Unreachable (HTTP/HTTPS Blocked)",
        "description": (
            "Port check failed — neither port 80 (HTTP) nor 443 (HTTPS) is reachable.\n"
            "Web traffic may be blocked by a firewall.\n\n"
            "Diagnostic Report:\n{report}"
        ),
    },
    "cloud_latency": {
        "title":       "Cloud Region Degradation Detected",
        "description": (
            "One or more cloud regions (AWS/Azure) are SLOW or UNREACHABLE.\n"
            "This is likely a regional cloud-side issue, not a local network problem.\n\n"
            "Diagnostic Report:\n{report}"
        ),
    },
}


def _has_cloud_issue(cloud_result: dict) -> bool:
    """
    Return True only when regional_issues are detected —
    meaning the same provider has both FAST and SLOW/UNREACHABLE regions.
    A single unreachable region without fast peers is not flagged.
    """
    return bool(cloud_result.get("regional_issues"))


def _send_ticket(title: str, description: str) -> dict | None:
    """
    POST a single ticket to the IT Ticket System API.
    Returns the created ticket dict, or None on failure.
    """
    payload = {
        "title":       title,
        "description": description,
        "source":      "network-troubleshooter",
    }
    try:
        response = requests.post(TICKET_API_URL, json=payload, timeout=5)
        response.raise_for_status()
        ticket = response.json()
        print(f"  [TICKET] #{ticket['id']} created — {ticket['priority']} | {ticket['category']} | {title}")
        return ticket
    except requests.exceptions.ConnectionError:
        print("  [TICKET] Skipped — IT Ticket System server is not running.")
        return None
    except requests.exceptions.RequestException as e:
        print(f"  [TICKET] Failed — {e}")
        return None


def create_tickets_for_failures(results: dict, report: str):
    """
    Create one ticket per failed check in the network diagnostic results.

    Called from main.py when any check status is FAIL:
        from integrations.network_client import create_tickets_for_failures
        create_tickets_for_failures(results, report)

    Check → ticket trigger:
        dns, gateway, internet, interfaces, ports  →  status == "FAIL"
        cloud_latency                              →  regional_issues present

    Args:
        results : dict returned by run_all_checks()
        report  : full formatted report string — attached to each ticket
    """
    standard_checks = ["dns", "gateway", "internet", "interfaces", "ports"]

    for key in standard_checks:
        result = results.get(key, {})
        if result.get("status") != "FAIL":
            continue
        cfg = _FAIL_CONFIG[key]
        _send_ticket(cfg["title"], cfg["description"].format(report=report))

    # Cloud latency — only ticket when a clear regional pattern is detected
    cloud_result = results.get("cloud_latency", {})
    if _has_cloud_issue(cloud_result):
        cfg = _FAIL_CONFIG["cloud_latency"]
        _send_ticket(cfg["title"], cfg["description"].format(report=report))


def prompt_save_as_ticket(report: str):
    """
    When all checks pass, ask the user whether to save the run as a ticket.
    Useful for keeping a record of a routine diagnostic run.

    Called from main.py when overall is ALL CHECKS PASSED:
        from integrations.network_client import prompt_save_as_ticket
        prompt_save_as_ticket(report)
    """
    answer = input("\n  Save this diagnostic run as a ticket? (y/n): ").strip().lower()
    if answer != "y":
        print("  [TICKET] Not saved.")
        return

    _send_ticket(
        title="Network Diagnostic Run — All Checks Passed",
        description=(
            "Routine network diagnostic completed with no failures detected.\n"
            "Saved for audit trail.\n\n"
            "Diagnostic Report:\n" + report
        ),
    )