import platform
import socket
import subprocess
import psutil


# ─────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────

def _run(cmd: list, timeout: int = 10) -> tuple:
    """
    Run a shell command and return (stdout, returncode).
    Captures stderr silently.
    """
    try:
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            timeout=timeout,
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
                parts   = line.split()
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

    os_name = _os()
    results = []

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
    stats      = psutil.net_if_stats()
    addrs      = psutil.net_if_addrs()

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

    return {
        "interfaces": interfaces,
        "status":     "OK" if interfaces else "FAIL",
    }


# ─────────────────────────────────────────
# Step 5 — IP configuration
# ─────────────────────────────────────────

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
        return list(dict.fromkeys(servers))

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


def check_ip_config() -> dict:
    """
    Retrieve IP configuration details per interface:
    IP address, subnet mask, and DNS servers.
    """
    addrs       = psutil.net_if_addrs()
    dns_servers = _get_dns_servers()
    config      = []

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


# ─────────────────────────────────────────
# Step 6 — Traceroute
# ─────────────────────────────────────────

def check_traceroute(host: str = "8.8.8.8") -> dict:
    """
    Run a traceroute to a public host to identify where packets are dropped.
    Uses tracert on Windows, traceroute on macOS/Linux.

    Notes:
    - Timeout is set to 60s to allow all hops to complete.
    - Status is based on output presence, not returncode — tracert may
      return non-zero when hops respond with * * * (no response).
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
            timeout=60,
        )
        out = result.stdout.decode(errors="replace")
    except (subprocess.TimeoutExpired, FileNotFoundError):
        out = ""

    lines      = [l for l in out.splitlines() if l.strip()]
    has_output = any(any(ch.isdigit() for ch in line) for line in lines)

    return {
        "host":   host,
        "output": lines,
        "status": "OK" if has_output else "FAIL",
    }


# ─────────────────────────────────────────
# Step 7 — Port availability
# ─────────────────────────────────────────

# Default ports to check with service names and common use cases
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
    Uses a TCP socket connection attempt with a short timeout.
    Overall OK if port 80 or 443 is open.
    """
    if ports is None:
        ports = DEFAULT_PORTS

    results = []
    for entry in ports:
        port = entry["port"]
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
            "service":  entry["service"],
            "use_case": entry["use_case"],
            "open":     open_,
            "status":   "OPEN" if open_ else "CLOSED",
        })

    key_ports_open = any(r["open"] for r in results if r["port"] in (80, 443))
    return {
        "host":    host,
        "results": results,
        "status":  "OK" if key_ports_open else "FAIL",
    }
