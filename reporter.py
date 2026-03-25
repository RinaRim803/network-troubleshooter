import os
import platform
import datetime

from utils import separator, timestamp


def _format_dns(dns: dict) -> list:
    lines = ["[DNS RESOLUTION]"]
    if dns["status"] == "OK":
        lines.append(f"  {dns['host']:<25} -> {dns['resolved_ip']}  [OK]")
    else:
        lines.append(f"  {dns['host']:<25} -> FAILED  [FAIL]")
        lines.append(f"  Error : {dns.get('error', 'Unknown')}")
    return lines


def _format_gateway(gw: dict) -> list:
    lines = ["[DEFAULT GATEWAY]"]
    if not gw["gateway"]:
        lines.append(f"  Could not determine gateway  [FAIL]")
    else:
        state = "Reachable" if gw["reachable"] else "Unreachable"
        lines.append(f"  {gw['gateway']:<25} {state}  [{gw['status']}]")
    return lines


def _format_internet(internet: dict) -> list:
    lines = ["[INTERNET REACHABILITY]"]
    for r in internet["results"]:
        state = "Reachable" if r["reachable"] else "Unreachable"
        lines.append(f"  {r['host']:<25} {state}")
    lines.append(f"  Overall  [{internet['status']}]")
    return lines


def _format_interfaces(interfaces: dict) -> list:
    lines = ["[ACTIVE INTERFACES]"]
    if not interfaces["interfaces"]:
        lines.append("  No active interfaces found  [FAIL]")
    else:
        for iface in interfaces["interfaces"]:
            ips = ", ".join(iface["ips"])
            lines.append(f"  {iface['name']:<20} {ips}")
        lines.append(f"  [{interfaces['status']}]")
    return lines


def _format_ip_config(ip_config: dict) -> list:
    lines = ["[IP CONFIGURATION]"]
    if not ip_config["config"]:
        lines.append("  No IP configuration found  [FAIL]")
    else:
        for c in ip_config["config"]:
            lines.append(f"  {c['interface']:<20} IP: {c['ip']}  Mask: {c['netmask']}")
    if ip_config["dns_servers"]:
        lines.append(f"  DNS Servers : {', '.join(ip_config['dns_servers'])}")
    else:
        lines.append("  DNS Servers : Not found")
    lines.append(f"  [{ip_config['status']}]")
    return lines


def _format_traceroute(traceroute: dict) -> list:
    lines = ["[TRACEROUTE]"]
    lines.append(f"  Target : {traceroute['host']}")
    if traceroute["output"]:
        # Show first 10 hops only
        for line in traceroute["output"][:12]:
            lines.append(f"  {line}")
    else:
        lines.append("  No output received")
    lines.append(f"  [{traceroute['status']}]")
    return lines


def _format_ports(ports: dict) -> list:
    lines = [f"[PORT CHECK]  (target: {ports['host']})"]
    for r in ports["results"]:
        state = "OPEN  " if r["open"] else "CLOSED"
        lines.append(
            f"  {r['port']:<5} {r['service']:<8} {state}  — {r['use_case']}"
        )
    lines.append(f"  [{ports['status']}]")
    return lines
def _format_cloud_latency(cloud: dict) -> list:
    lines = ["[CLOUD REGION LATENCY]"]

    # Ranked results
    lines.append("  Ranking (fastest to slowest):")
    for i, r in enumerate(cloud["ranked"], 1):
        ms_str = f"{r['latency_ms']}ms" if r["latency_ms"] else "N/A"
        lines.append(
            f"  {i:>2}. {r['provider']:<6} {r['region']:<35} "
            f"{ms_str:>8}  [{r['classification']}]"
        )

    # Regional issues
    if cloud["regional_issues"]:
        lines.append("")
        lines.append("  Regional issues detected:")
        for issue in cloud["regional_issues"]:
            slow = ", ".join(issue["slow_regions"])
            lines.append(
                f"  {issue['provider']} — slow regions: {slow}"
            )
            lines.append(
                f"  Note: other {issue['provider']} regions are fast "
                f"— likely a regional issue, not your network."
            )

    # Alternative suggestions
    if cloud["suggestions"]:
        lines.append("")
        lines.append("  Suggested alternatives:")
        for s in cloud["suggestions"]:
            lines.append(f"  {s['provider']} {s['slow_region']} is SLOW — consider:")
            for alt in s["alternatives"]:
                lines.append(
                    f"    -> {alt['region']:<35} {alt['latency_ms']}ms  [{alt['classification']}]"
                )

    lines.append(f"  [{cloud['status']}]")
    return lines

def _get_overall(results: dict) -> str:
    """Determine overall status — FAIL if any check failed."""
    statuses = [v["status"] for v in results.values()]
    return "FAIL - check items above" if "FAIL" in statuses else "ALL CHECKS PASSED"


def build_report(results: dict) -> tuple:
    """
    Build a formatted report string from all check results.
    Returns (report_string, overall_status).
    """
    lines = []
    lines.append(separator())
    lines.append("  NETWORK TROUBLESHOOTER REPORT")
    lines.append(f"  {timestamp()}")
    lines.append(f"  OS : {platform.system()} {platform.release()}")
    lines.append(separator())

    lines.extend(_format_dns(results["dns"]))
    lines.extend(_format_gateway(results["gateway"]))
    lines.extend(_format_internet(results["internet"]))
    lines.extend(_format_interfaces(results["interfaces"]))
    lines.extend(_format_ip_config(results["ip_config"]))
    lines.extend(_format_traceroute(results["traceroute"]))
    lines.extend(_format_ports(results["ports"]))
    lines.extend(_format_cloud_latency(results["cloud_latency"]))

    lines.append(separator())
    overall = _get_overall(results)
    lines.append(f"  OVERALL : {overall}")
    lines.append(separator())

    return "\n".join(lines), overall


def save_log(report: str) -> str:
    """Save the report to a timestamped log file in a 'logs' folder."""
    log_dir  = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
    os.makedirs(log_dir, exist_ok=True)
    filename = datetime.datetime.now().strftime("network_%Y%m%d_%H%M%S.log")
    filepath = os.path.join(log_dir, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(report)
    return filepath