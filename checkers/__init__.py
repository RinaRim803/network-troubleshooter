# Checkers package.
# Exposes a single entry point: run_all_checks()
# which aggregates results from all individual checker modules.

from checkers.network_checker import (
    check_dns,
    check_gateway,
    check_internet,
    check_interfaces,
    check_ip_config,
    check_traceroute,
    check_ports,
)
from checkers.cloud_checker import check_cloud_latency


def run_all_checks() -> dict:
    """
    Run all network and cloud checks.
    Returns a single dict with results keyed by check name.
    To add a new check: import the function above and add it here.
    """
    return {
        "dns":           check_dns(),
        "gateway":       check_gateway(),
        "internet":      check_internet(),
        "interfaces":    check_interfaces(),
        "ip_config":     check_ip_config(),
        "traceroute":    check_traceroute(),
        "ports":         check_ports(),
        "cloud_latency": check_cloud_latency(),
    }
