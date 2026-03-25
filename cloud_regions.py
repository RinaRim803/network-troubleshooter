# Cloud provider region endpoints for latency measurement.
# Each entry maps a human-readable region label to its public endpoint URL.
#
# Endpoint selection criteria:
# - Publicly accessible without authentication
# - Lightweight response (HEAD request friendly)
# - Stable and unlikely to be removed
#
# To add a new region: add an entry under the appropriate provider.
# To add a new provider: add a new top-level key.
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
LATENCY_THRESHOLDS = {
    "FAST": 80,    # < 80ms   (같은 대륙, 가까운 리전)
    "OK":   200,   # 80~200ms (다른 대륙)
    "SLOW": 200,   # > 200ms
}