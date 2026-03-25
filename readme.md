# network-troubleshooter

> **"When a user says the internet is slow, I don't guess — I run this."**

A professional-grade Python diagnostic tool designed to transform manual, time-consuming network troubleshooting into a **2-minute automated workflow**. It bridges the gap between local ISP issues and complex cloud region degradations.

---

## 📌 Performance Impact

| Metric | Before (Manual) | After (Automated) |
| :--- | :--- | :--- |
| **Diagnosis Time** | 10–15 min manual per ticket | **Under 2 min automated** |
| **Root Cause Accuracy** | High risk of misdiagnosing cloud issues | **Data-driven detection** |
| **Decision Support** | Manual research for failover | **Auto-suggested alternatives** |
| **Documentation** | Often missing or inconsistent | **Timestamped logs saved automatically** |

---

## 📋 Scenario & Problem Solving

### The Standard Ticket: "The internet is slow"
**The Situation:** A user submits a ticket: *"The internet is slow"* or *"I can't connect to the server."*

**The Problem:** Traditional manual checks (ping, ipconfig, traceroute) are inefficient in cloud-first environments. When a specific AWS or Azure region is degraded, it often looks identical to a local network problem, leading to 15+ minutes of wasted troubleshooting.

**The Solution:**
A modular Python tool that executes a full-stack diagnostic—from local L1 checks to cloud-layer latency ranking—in a single command.

---

## 💡 Real-World Use Cases

### Case 1: Distinguishing Cloud Outages from Local Issues
* **Problem:** Users report slowness in specific global regions. Operators usually "guess" between server, DB, or network issues by manually digging through logs.
* **Automated Solution:** The tool runs multi-region latency measurements and ranks them. It automatically flags if only one region (e.g., `us-east-1`) is spiking while others remain stable.
* **Result:** Provides a report within 2 minutes proving the issue is a specific regional path degradation, not the backend or local network.

### Case 2: Rapid Failover & Alternative Routing
* **Problem:** During a regional outage, On-Call engineers often choose a failover region based on "gut feeling," which may not be the optimal path at that specific moment.
* **Automated Solution:** The tool calculates a real-time ranking of the fastest and most stable regions based on current RTT.
* **Result:** Outputs a **"Top 3 Recommended Alternatives"** list. This reduces the decision-making time from 30+ minutes to mere seconds.

---

## 🛠️ How It Works

The tool is built with a **modular architecture** where each component handles a specific layer of the network stack:

```text
python main.py
        |
  [ setup.py ] --------> Validate & auto-install dependencies (psutil)
        |
  [ checkers.py ] -----> Execute diagnostics in sequence:
        |                • Local: DNS, Gateway, Internet, IP Config, Ports
        |                • Cloud: TCP latency ranking for AWS & Azure
        |
  [ reporter.py ] -----> Assemble results into a formatted report
        |
  [ logs/ ] -----------> Save timestamped .log file for ticket documentation
```

## ⚙️ Technical Architecture & Internal Logic

This project is engineered with a focus on **modular scalability** and **low-overhead diagnostic accuracy**. Below is a detailed breakdown of the internal logic for each core module.

### 1. Orchestration & Environment Safety (`main.py` & `setup.py`)
Before any network checks begin, the system ensures environmental integrity.
* **Auto-Dependency Injection:** `setup.py` reads `requirements.txt` and uses `importlib` to check for missing packages. [cite_start]If a dependency like `psutil` is missing, it auto-installs it via a suppressed `subprocess` call to `pip`. [cite: 1]
* **Pre-Flight Validation:** `main.py` calls `run_setup()` as a gatekeeper. [cite_start]If dependencies cannot be satisfied, the program exits gracefully to prevent runtime tracebacks. [cite: 1]

### 2. Multi-Layer Diagnostic Engine (`checkers.py`)
The diagnostic logic is divided into two primary phases: **Local Infrastructure** and **Cloud Performance**.

#### A. Local Network Stack (L1 - L4)
* [cite_start]**DNS Resolution:** Uses `socket.gethostbyname()` to verify if the local DNS forwarder can resolve public domains (e.g., google.com). [cite: 1]
* [cite_start]**Gateway & Interface Analysis:** * Identifies the default gateway IP based on the host OS (Windows: `ipconfig`, Linux: `ip route`, macOS: `netstat`). [cite: 1]
    * Pings the gateway to distinguish between a "total local outage" and an "ISP/Cloud outage."
* **Service Port Auditing:** Iterates through a dictionary of critical ports (80, 443, 3389, etc.) using `socket.connect_ex()`. [cite_start]This identifies if specific traffic types are being dropped by a local firewall or ISP transparent proxy. [cite: 1]

#### B. Cloud Latency Ranking Logic
* [cite_start]**Median-Based Filtering:** To eliminate "network jitter" or temporary spikes, the tool takes **3 independent TCP samples** for each cloud region and calculates the **median latency**. [cite: 1]
* [cite_start]**TCP Handshake Measurement:** Unlike standard ICMP pings (which are often de-prioritized or blocked by enterprise firewalls), this tool measures the time taken for a full TCP SYN/ACK handshake to specific cloud service endpoints (e.g., DynamoDB for AWS, Blob Storage for Azure). [cite: 1]
* **Classification Algorithm:** Latency is dynamically classified:
    * **FAST:** < 100ms
    * **OK:** 100ms - 200ms
    * **SLOW:** > 200ms
    * [cite_start]**UNREACHABLE:** Connection timeout or refused. [cite: 1]

### 3. Intelligence & Heuristics (`reporter.py`)
The reporter doesn't just show data; it provides **Actionable Intelligence**.
* [cite_start]**Regional Issue Detection:** If the "Home Region" is SLOW but other regions from the same provider are FAST, the system flags a **"Regional Degradation"** alert. [cite: 1]
* [cite_start]**Alternative Suggestion Engine:** When a primary region is flagged as SLOW or UNREACHABLE, the logic parses the ranked list to find the next two fastest "FAST" or "OK" regions to suggest as immediate failover targets. [cite: 1]
* [cite_start]**Automated Logging:** Every report is serialized into a string and written to a timestamped file in the `/logs` directory, ensuring a "paper trail" for every IT ticket handled. [cite: 1]

---

### 🛠️ Core Function Mapping

| Module | Key Function | Logic Description |
| :--- | :--- | :--- |
| **Checkers** | `check_cloud_latency()` | Orchestrates multi-threaded or sequential TCP probes to global endpoints. |
| **Checkers** | `check_traceroute()` | Executes OS-native traceroute to identify the specific hop where latency spikes. |
| **Setup** | `load_requirements()` | Parses version-locked dependencies and maps install names to import names. |
| **Reporter** | `_get_overall()` | A Boolean-gate logic that marks the entire ticket as 'FAIL' if any sub-check returns a failure status. |



## 🚀 Key Features

* **Cloud Region Ranking**: Ranks 10+ global regions (AWS/Azure) using 3-sample median TCP latency to filter noise. 
* **Cross-Platform Engine**: Native support for Windows (ipconfig), macOS (scutil), and Linux (ip route) commands. 
* **Port Availability**: Quickly verifies critical service ports (HTTP, HTTPS, RDP, SMB, DNS, SSH). 
* **Self-Healing Setup**: Automatically manages its own environment using config.json and requirements.txt.

## 💻 Skills Demonstrated

* **Automation**: Python-based workflow orchestration and auto-dependency management.
* **Networking**: Socket programming, TCP/IP, DNS resolution, and routing analysis.
* **Operations**: IT Support ticket lifecycle optimization and incident response (IR) support.
* **Architecture**: Clean, modular code design with clear separation of logic and data.
