import platform
import socket
import statistics
import subprocess
import psutil
import time
from cloud_regions import CLOUD_REGIONS, LATENCY_THRESHOLDS, REQUEST_TIMEOUT


# ─────────────────────────────────────────
# Helper
# ─────────────────────────────────────────

def _run(cmd: list) -> tuple:
    """
    Run a shell command and return (stdout, returncode).
    Captures stderr silently.
    """
    try:
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            timeout=10,
        )
        return result.stdout.decode(errors="replace"), result.returncode
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return "", 1


def _os() -> str:
    """Return the current OS name: Windows, Darwin, or Linux."""
    return platform.system()


# ─────────────────────────────────────────
# Step 1 — DNS resolution
# ─────────────────────────────────────────

def check_dns(host: str = "google.com") -> dict:
    """
    Check if DNS resolution is working by resolving a public hostname.
    Returns resolved IP on success, error message on failure.
    """
    try:
        socket.setdefaulttimeout(3)
        ip = socket.gethostbyname(host)
        return {"host": host, "resolved_ip": ip, "status": "OK"}
    except socket.gaierror as e:
        return {"host": host, "resolved_ip": None, "error": str(e), "status": "FAIL"}


# ─────────────────────────────────────────
# Step 2 — Gateway reachability
# ─────────────────────────────────────────

def _get_default_gateway() -> str | None:
    """Retrieve the default gateway IP using OS-appropriate method."""
    os_name = _os()

    if os_name == "Windows":
        out, _ = _run(["ipconfig"])
        for line in out.splitlines():
            if "Default Gateway" in line:
                parts = line.split(":")
                if len(parts) == 2:
                    gw = parts[1].strip()
                    if gw:
                        return gw

    elif os_name == "Darwin":
        out, _ = _run(["netstat", "-nr"])
        for line in out.splitlines():
            if line.startswith("default"):
                parts = line.split()
                if len(parts) >= 2:
                    return parts[1]

    else:
        # Linux
        out, _ = _run(["ip", "route"])
        for line in out.splitlines():
            if line.startswith("default"):
                parts = line.split()
                via_idx = parts.index("via") if "via" in parts else -1
                if via_idx != -1 and via_idx + 1 < len(parts):
                    return parts[via_idx + 1]

    return None


def check_gateway() -> dict:
    """
    Find the default gateway and verify it is reachable via ping.
    """
    gateway = _get_default_gateway()
    if not gateway:
        return {"gateway": None, "status": "FAIL", "error": "Could not determine default gateway"}

    os_name = _os()
    cmd = (
        ["ping", "-n", "2", gateway] if os_name == "Windows"
        else ["ping", "-c", "2", "-W", "2", gateway]
    )
    _, code = _run(cmd)
    reachable = code == 0
    return {
        "gateway":   gateway,
        "reachable": reachable,
        "status":    "OK" if reachable else "FAIL",
    }


# ─────────────────────────────────────────
# Step 3 — Internet reachability
# ─────────────────────────────────────────

def check_internet(hosts: list = None) -> dict:
    """
    Check internet reachability by pinging public DNS servers.
    Tries each host in order and returns on first success.
    """
    if hosts is None:
        hosts = ["8.8.8.8", "1.1.1.1"]

    os_name  = _os()
    results  = []

    for host in hosts:
        cmd = (
            ["ping", "-n", "2", host] if os_name == "Windows"
            else ["ping", "-c", "2", "-W", "2", host]
        )
        _, code = _run(cmd)
        reachable = code == 0
        results.append({"host": host, "reachable": reachable})
        if reachable:
            break

    overall = any(r["reachable"] for r in results)
    return {
        "results": results,
        "status":  "OK" if overall else "FAIL",
    }


# ─────────────────────────────────────────
# Step 4 — Active network interfaces
# ─────────────────────────────────────────

def check_interfaces() -> dict:
    """
    List active network interfaces with their IP addresses.
    Excludes loopback (127.x) and link-local (169.254.x) addresses.
    """
    interfaces = []
    stats = psutil.net_if_stats()
    addrs = psutil.net_if_addrs()

    for name, stat in stats.items():
        if not stat.isup:
            continue
        ips = []
        for addr in addrs.get(name, []):
            if addr.family == socket.AF_INET:
                ip = addr.address
                if not ip.startswith("127.") and not ip.startswith("169.254."):
                    ips.append(ip)
        if ips:
            interfaces.append({"name": name, "ips": ips})

    status = "OK" if interfaces else "FAIL"
    return {"interfaces": interfaces, "status": status}


# ─────────────────────────────────────────
# Step 5 — IP configuration
# ─────────────────────────────────────────

def check_ip_config() -> dict:
    """
    Retrieve IP configuration details per interface:
    IP address, subnet mask, and DNS servers.
    """
    addrs      = psutil.net_if_addrs()
    dns_servers = _get_dns_servers()
    config     = []

    for iface, addr_list in addrs.items():
        for addr in addr_list:
            if addr.family == socket.AF_INET:
                ip = addr.address
                if ip.startswith("127.") or ip.startswith("169.254."):
                    continue
                config.append({
                    "interface": iface,
                    "ip":        ip,
                    "netmask":   addr.netmask or "N/A",
                })

    return {
        "config":      config,
        "dns_servers": dns_servers,
        "status":      "OK" if config else "FAIL",
    }


def _get_dns_servers() -> list:
    """Retrieve configured DNS servers using OS-appropriate method."""
    os_name = _os()

    if os_name == "Windows":
        out, _ = _run(["ipconfig", "/all"])
        servers = []
        for line in out.splitlines():
            if "DNS Servers" in line:
                parts = line.split(":")
                if len(parts) == 2:
                    dns = parts[1].strip()
                    if dns:
                        servers.append(dns)
        return servers

    elif os_name == "Darwin":
        out, _ = _run(["scutil", "--dns"])
        servers = []
        for line in out.splitlines():
            line = line.strip()
            if line.startswith("nameserver"):
                parts = line.split(":")
                if len(parts) == 2:
                    servers.append(parts[1].strip())
        return list(dict.fromkeys(servers))  # deduplicate

    else:
        # Linux — read /etc/resolv.conf
        servers = []
        try:
            with open("/etc/resolv.conf") as f:
                for line in f:
                    if line.startswith("nameserver"):
                        parts = line.split()
                        if len(parts) == 2:
                            servers.append(parts[1])
        except OSError:
            pass
        return servers


# ─────────────────────────────────────────
# Step 6 — Traceroute
# ─────────────────────────────────────────

def check_traceroute(host: str = "8.8.8.8") -> dict:
    """
    Run a traceroute to a public host to identify where packets are dropped.
    Uses tracert on Windows, traceroute on macOS/Linux.

    Notes:
    - Timeout is set to 60s to allow tracert to complete all hops.
    - Status is determined by output presence, not returncode —
      tracert/traceroute may return non-zero even on partial success
      (e.g. hops with * * * no-response).
    """
    os_name = _os()
    cmd = (
        ["tracert", "-h", "10", host] if os_name == "Windows"
        else ["traceroute", "-m", "10", host]
    )

    try:
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            timeout=60,   # tracert can take up to 30-60s for 10 hops
        )
        out = result.stdout.decode(errors="replace")
    except subprocess.TimeoutExpired:
        out = ""
    except FileNotFoundError:
        out = ""

    lines = [l for l in out.splitlines() if l.strip()]

    # Status: OK if we got any hop output, FAIL only if completely empty
    has_output = any(
        any(char.isdigit() for char in line)
        for line in lines
    )
    return {
        "host":   host,
        "output": lines,
        "status": "OK" if has_output else "FAIL",
    }

# ─────────────────────────────────────────
# Step 7 — Port check
# ─────────────────────────────────────────
 
# Default ports to check with their service names and common use cases
DEFAULT_PORTS = [
    {"port": 80,   "service": "HTTP",  "use_case": "Web browsing"},
    {"port": 443,  "service": "HTTPS", "use_case": "Secure web browsing"},
    {"port": 53,   "service": "DNS",   "use_case": "DNS server direct check"},
    {"port": 3389, "service": "RDP",   "use_case": "Remote Desktop"},
    {"port": 445,  "service": "SMB",   "use_case": "File sharing"},
    {"port": 22,   "service": "SSH",   "use_case": "Remote access (Linux/Mac)"},
]
 
 
def check_ports(host: str = "8.8.8.8", ports: list = None) -> dict:
    """
    Check whether common service ports are open on a target host.
    Uses socket connection attempt with a short timeout.
 
    Args:
        host  : Target host to check ports against (default: 8.8.8.8)
        ports : List of port dicts to check (default: DEFAULT_PORTS)
 
    Returns a list of results per port with open/closed status.
    """
    if ports is None:
        ports = DEFAULT_PORTS
 
    results = []
    for entry in ports:
        port    = entry["port"]
        service = entry["service"]
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(3)
            code = sock.connect_ex((host, port))
            sock.close()
            open_ = code == 0
        except OSError:
            open_ = False
 
        results.append({
            "port":     port,
            "service":  service,
            "use_case": entry["use_case"],
            "open":     open_,
            "status":   "OPEN" if open_ else "CLOSED",
        })
 
    # Overall: OK if at least HTTP or HTTPS is open
    key_ports_open = any(
        r["open"] for r in results if r["port"] in (80, 443)
    )
    return {
        "host":    host,
        "results": results,
        "status":  "OK" if key_ports_open else "FAIL",
    }

# ─────────────────────────────────────────
# Step 8 — Cloud region latency
# ─────────────────────────────────────────

def _measure_latency(host: str, port: int = 443) -> float | None:
    """
    Measure TCP connection latency to a host:port.
    Takes 3 samples and returns the median to reduce noise.
    Avoids TLS handshake overhead — closer to true network latency.
    """
    samples = []
    for _ in range(3):
        try:
            start   = time.time()
            sock    = socket.create_connection((host, port), timeout=5)
            elapsed = (time.time() - start) * 1000
            sock.close()
            samples.append(elapsed)
        except OSError:
            pass
    return round(statistics.median(samples), 1) if samples else None
    


def _classify_latency(ms: float | None) -> str:
    """Classify latency into FAST / OK / SLOW / UNREACHABLE."""
    if ms is None:
        return "UNREACHABLE"
    if ms < LATENCY_THRESHOLDS["FAST"]:
        return "FAST"
    if ms < LATENCY_THRESHOLDS["SLOW"]:
        return "OK"
    return "SLOW"


def _suggest_alternatives(results: list, current_region: str, provider: str) -> list:
    """
    Given the current best region, suggest faster alternatives
    from the same cloud provider.
    Filters out SLOW and UNREACHABLE regions.
    """
    same_provider = [
        r for r in results
        if r["provider"] == provider
        and r["region"] != current_region
        and r["latency_ms"] is not None
        and r["classification"] in ("FAST", "OK")
    ]
    # Sort by latency ascending
    return sorted(same_provider, key=lambda r: r["latency_ms"])[:3]


def check_cloud_latency() -> dict:
    """
    Measure latency to each cloud provider region endpoint.

    For each region:
    - Sends an HTTP HEAD request
    - Records response time (ms)
    - Classifies as FAST / OK / SLOW / UNREACHABLE

    Then:
    - Ranks all regions by latency (fastest first)
    - Detects if any provider has regions with mixed FAST/SLOW results
      (indicates a regional issue, not a local network problem)
    - Suggests alternative regions when the current best is SLOW
    """
    all_results = []

    for provider, regions in CLOUD_REGIONS.items():
        for region, endpoint in regions.items():
            ms             = _measure_latency(endpoint["host"], endpoint["port"])
            classification = _classify_latency(ms)
            all_results.append({
            "provider":       provider,
            "region":         region,
            "host":           endpoint["host"],
            "latency_ms":     ms,
            "classification": classification,
            })

    # Sort all results by latency (unreachable goes to the end)
    ranked = sorted(
        all_results,
        key=lambda r: r["latency_ms"] if r["latency_ms"] is not None else float("inf")
    )

    # Detect regional issues per provider
    # If same provider has both FAST and SLOW regions → likely a regional issue
    regional_issues = []
    for provider in CLOUD_REGIONS:
        provider_results = [r for r in all_results if r["provider"] == provider]
        has_fast = any(r["classification"] == "FAST" for r in provider_results)
        has_slow = any(r["classification"] in ("SLOW", "UNREACHABLE") for r in provider_results)
        if has_fast and has_slow:
            slow_regions = [
                r["region"] for r in provider_results
                if r["classification"] in ("SLOW", "UNREACHABLE")
            ]
            regional_issues.append({
                "provider":     provider,
                "slow_regions": slow_regions,
            })

    # Suggest alternatives for the slowest reachable region per provider
    suggestions = []
    for provider in CLOUD_REGIONS:
        provider_results = [r for r in all_results if r["provider"] == provider]
        slow_ones = [
            r for r in provider_results
            if r["classification"] == "SLOW"
        ]
        for slow in slow_ones:
            alternatives = _suggest_alternatives(all_results, slow["region"], provider)
            if alternatives:
                suggestions.append({
                    "provider":     provider,
                    "slow_region":  slow["region"],
                    "alternatives": alternatives,
                })

    reachable = [r for r in all_results if r["latency_ms"] is not None]
    overall = "OK" if reachable else "FAIL"

    return {
        "ranked":          ranked,
        "regional_issues": regional_issues,
        "suggestions":     suggestions,
        "status":          overall,
    }


# ─────────────────────────────────────────
# Run all checks
# ─────────────────────────────────────────

def run_all_checks() -> dict:
    """Run all network checks and return results as a single dict."""
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

