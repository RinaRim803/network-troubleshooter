import socket
import statistics
import time

from data.cloud_regions import CLOUD_REGIONS, LATENCY_THRESHOLDS


# ─────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────

def _measure_latency(host: str, port: int = 443) -> float | None:
    """
    Measure TCP connection latency to a host:port.
    Takes 3 samples and returns the median to reduce noise.
    TCP socket is used instead of HTTP to avoid TLS handshake overhead.
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
    Suggest up to 3 faster alternative regions from the same provider.
    Excludes SLOW and UNREACHABLE regions from suggestions.
    """
    alternatives = [
        r for r in results
        if r["provider"] == provider
        and r["region"] != current_region
        and r["latency_ms"] is not None
        and r["classification"] in ("FAST", "OK")
    ]
    return sorted(alternatives, key=lambda r: r["latency_ms"])[:3]


# ─────────────────────────────────────────
# Step 8 — Cloud region latency
# ─────────────────────────────────────────

def check_cloud_latency() -> dict:
    """
    Measure TCP latency to each cloud provider region endpoint.

    For each region:
    - Sends 3 TCP connection attempts, takes the median
    - Classifies as FAST / OK / SLOW / UNREACHABLE

    Then:
    - Ranks all regions by latency (fastest first)
    - Detects regional issues: same provider has both FAST and SLOW regions
      → likely a cloud-side problem, not a local network issue
    - Suggests alternative regions for any SLOW region
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

    # Sort by latency — unreachable regions go to the end
    ranked = sorted(
        all_results,
        key=lambda r: r["latency_ms"] if r["latency_ms"] is not None else float("inf"),
    )

    # Detect regional issues per provider
    # A regional issue = same provider has both FAST and SLOW/UNREACHABLE regions
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

    # Suggest alternative regions for each SLOW region
    suggestions = []
    for provider in CLOUD_REGIONS:
        provider_results = [r for r in all_results if r["provider"] == provider]
        for slow in [r for r in provider_results if r["classification"] == "SLOW"]:
            alternatives = _suggest_alternatives(all_results, slow["region"], provider)
            if alternatives:
                suggestions.append({
                    "provider":     provider,
                    "slow_region":  slow["region"],
                    "alternatives": alternatives,
                })

    # Overall OK if at least one region is reachable
    reachable = [r for r in all_results if r["latency_ms"] is not None]
    return {
        "ranked":          ranked,
        "regional_issues": regional_issues,
        "suggestions":     suggestions,
        "status":          "OK" if reachable else "FAIL",
    }
