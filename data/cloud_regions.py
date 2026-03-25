# Cloud provider region endpoints for TCP latency measurement.
#
# Each entry maps a human-readable region label to its host and port.
# TCP socket connection is used instead of HTTP to avoid TLS handshake overhead.
#
# Endpoint selection criteria:
# - Publicly accessible without authentication
# - Stable, long-term endpoints unlikely to be removed
# - Per-region subdomains for accurate geographic measurement
#
# To add a region  : add an entry under the appropriate provider.
# To add a provider: add a new top-level key with the same dict structure.
# GCP is excluded  : no stable per-region public endpoints available.

CLOUD_REGIONS = {
    "AWS": {
        "us-west-2      (Oregon)":      {"host": "dynamodb.us-west-2.amazonaws.com",      "port": 443},
        "us-east-1      (N. Virginia)": {"host": "dynamodb.us-east-1.amazonaws.com",      "port": 443},
        "ap-northeast-1 (Tokyo)":       {"host": "dynamodb.ap-northeast-1.amazonaws.com", "port": 443},
        "ap-southeast-2 (Sydney)":      {"host": "dynamodb.ap-southeast-2.amazonaws.com", "port": 443},
        "eu-west-1      (Ireland)":     {"host": "dynamodb.eu-west-1.amazonaws.com",      "port": 443},
    },
    "Azure": {
        "westus2        (Washington)":  {"host": "westus2.blob.core.windows.net",         "port": 443},
        "eastus         (Virginia)":    {"host": "eastus.blob.core.windows.net",          "port": 443},
        "japaneast      (Tokyo)":       {"host": "japaneast.blob.core.windows.net",       "port": 443},
        "australiaeast  (Sydney)":      {"host": "australiaeast.blob.core.windows.net",   "port": 443},
        "northeurope    (Ireland)":     {"host": "northeurope.blob.core.windows.net",     "port": 443},
    },
}

# Latency thresholds (ms) for status classification
# Tuned for Vancouver, BC — adjust if running from a different region
LATENCY_THRESHOLDS = {
    "FAST": 80,    # < 80ms  : same continent, nearby region
    "OK":   200,   # < 200ms : cross-continent
    "SLOW": 200,   # >= 200ms: degraded
}
