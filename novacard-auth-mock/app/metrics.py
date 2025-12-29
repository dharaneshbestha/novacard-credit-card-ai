from prometheus_client import Counter, Histogram

svc_auth_total = Counter(
    "user_svc_auth_total",
    "Service-auth outcomes",
    ["result", "kid"]
)

svc_auth_latency = Histogram(
    "user_svc_auth_latency_seconds",
    "Service-auth middleware latency",
)