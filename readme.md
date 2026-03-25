# network-troubleshooter

> **"When a user says the internet is slow, I don't guess — I run this."**

A cross-platform network diagnostic tool that checks everything from your 
local gateway to cloud region latency — and tells you exactly where the 
problem is.

---

## Scenario

A user submits a ticket: *"The internet is slow" or "I can't connect to 
the server."*

The technician manually runs ping, checks IP config, tests ports one by 
one — spending 10–15 minutes before identifying the root cause. And when 
the issue is a specific cloud region, it often gets misdiagnosed as a 
local network problem.

## Problem

Local network diagnostics alone are not enough in cloud-first environments:

1. Run `ping` manually — check connectivity
2. Run `ipconfig` — check IP and DNS config
3. Test ports one by one — check service availability
4. No visibility into cloud region performance

When a specific AWS or Azure region is degraded, it looks identical to a 
local network issue from the user's perspective. There is no quick way to 
distinguish between the two.

## Solution

A modular Python tool that runs a full network diagnostic in one command — 
from L1 local checks all the way to cloud region latency ranking.
```bash
python network_check.py
```

- DNS resolution check
- Default gateway reachability
- Internet connectivity verification
- Active interface and IP configuration
- Port availability check (HTTP, HTTPS, RDP, SMB, DNS, SSH)
- Cloud region latency ranking (AWS + Azure, 10 regions)
- Automatic detection of regional cloud issues
- Alternative region suggestions when a region is slow
- Timestamped log saved for every run

### How it works
```
python network_check.py
        |
        v
  setup.py              Validate dependencies via requirements.txt
        |
        v
  checkers.py           Run all checks in sequence
  |
  +-- Local (L1-L4)
  |   +-- DNS resolution
  |   +-- Gateway ping
  |   +-- Internet reachability
  |   +-- Interface + IP config
  |   +-- Port check
  |
  +-- Cloud
      +-- TCP latency to AWS + Azure regions (3-sample median)
      +-- Rank regions fastest to slowest
      +-- Detect regional issues
      +-- Suggest alternatives
        |
        v
  reporter.py           Build report + save timestamped log
```

### Module breakdown
```
network-troubleshooter/
├── network_check.py    # Entry point — orchestrates the full workflow
├── checkers.py         # All check functions (local + cloud)
├── cloud_regions.py    # Cloud region endpoint definitions (data only)
├── reporter.py         # Report builder and log writer
├── utils.py            # Shared helpers (separator, timestamp)
├── requirements.txt    # Dependency definitions
├── config.json         # Project metadata
├── setup.py            # Auto dependency checker and installer
├── .gitignore
└── logs/               # Auto-generated timestamped log files
```

**`network_check.py`** — Entry point. Validates dependencies, runs all 
checks, builds and saves the report.
```python
run_setup()                          # 0. validate dependencies
results         = run_all_checks()   # 1. run all checks
report, overall = build_report()     # 2. build report
save_log(report)                     # 3. save log
```

**`checkers.py`** — All check functions, local and cloud.

| Function | What it checks |
|---|---|
| `check_dns()` | DNS resolution via socket |
| `check_gateway()` | Default gateway ping |
| `check_internet()` | Public IP reachability (8.8.8.8, 1.1.1.1) |
| `check_interfaces()` | Active NICs and IP addresses |
| `check_ip_config()` | IP, subnet mask, DNS servers |
| `check_traceroute()` | Hop-by-hop path to 8.8.8.8 (max 10 hops) |
| `check_ports()` | TCP port availability for common services |
| `check_cloud_latency()` | AWS + Azure region latency ranking |

**`cloud_regions.py`** — Data-only module. Defines cloud provider region 
endpoints. Add or remove regions here without touching any logic.

| Provider | Regions | Measurement method |
|---|---|---|
| AWS | us-west-2, us-east-1, ap-northeast-1, ap-southeast-2, eu-west-1 | TCP socket to DynamoDB endpoint |
| Azure | westus2, eastus, japaneast, australiaeast, northeurope | TCP socket to Blob Storage endpoint |

**`reporter.py`** — Assembles all check results into a formatted report 
and saves it as a timestamped log.

**`setup.py`** — Reads `requirements.txt`, checks each dependency, and 
auto-installs missing packages via pip.

**`utils.py`** — Shared helpers (`separator()`, `timestamp()`).

## Result

| | Before | After |
|---|---|---|
| Diagnosis time | 10–15 min manual | Under 2 min automated |
| Cloud vs local issue | Indistinguishable | Automatically detected |
| Regional degradation | Not visible | Ranked and flagged |
| Alternative routing | Manual research | Auto-suggested |
| Documentation | Not saved | Timestamped log auto-saved |
| OS support | Single platform | Windows, macOS, Linux |

---

## Sample Output
```
[CLOUD REGION LATENCY]
  Ranking (fastest to slowest):
   1. AWS    us-west-2      (Oregon)               15.2ms  [FAST]
   2. Azure  westus2        (Washington)           76.2ms  [FAST]
   3. AWS    us-east-1      (N. Virginia)          80.9ms  [OK]
   4. AWS    ap-northeast-1 (Tokyo)               112.9ms  [OK]
   5. Azure  northeurope    (Ireland)             125.9ms  [OK]
   6. AWS    eu-west-1      (Ireland)             198.2ms  [OK]
   7. AWS    ap-southeast-2 (Sydney)              214.6ms  [SLOW]
   8. Azure  eastus         (Virginia)            225.6ms  [SLOW]
   9. Azure  japaneast      (Tokyo)                   N/A  [UNREACHABLE]
  10. Azure  australiaeast  (Sydney)                  N/A  [UNREACHABLE]

  Regional issues detected:
  AWS — slow regions: ap-southeast-2 (Sydney)
  Note: other AWS regions are fast — likely a regional issue, not your network.

  Suggested alternatives:
  AWS ap-southeast-2 (Sydney) is SLOW — consider:
    -> us-west-2      (Oregon)              15.2ms  [FAST]
    -> us-east-1      (N. Virginia)         80.9ms  [OK]
  [OK]
----------------------------------------
  OVERALL : ALL CHECKS PASSED
----------------------------------------
```

---

## Requirements

- Python 3.7+
```bash
pip install -r requirements.txt
```

Dependencies are checked and installed automatically on first run.

---

## Setup

**1. Clone the repo**
```bash
git clone https://github.com/RinaRim803/network-troubleshooter.git
cd network-troubleshooter
```

**2. Run**
```bash
python network_check.py
```

---

## Cross-Platform Support

| OS | Gateway detection | Traceroute command | DNS config |
|---|---|---|---|
| Windows | `ipconfig` | `tracert` | `ipconfig /all` |
| macOS | `netstat -nr` | `traceroute` | `scutil --dns` |
| Linux | `ip route` | `traceroute` | `/etc/resolv.conf` |

---

## Skills Demonstrated

- Modular Python design (single-responsibility per module)
- Network troubleshooting logic — L1 through cloud layer
- TCP socket-based latency measurement (avoids HTTP/TLS overhead)
- Statistical noise reduction (3-sample median per region)
- Cloud region performance analysis (AWS + Azure)
- Automatic regional issue detection and alternative routing suggestions
- Cross-platform compatibility (Windows / macOS / Linux)
- Dependency management via requirements.txt + auto-installer
- Structured log generation