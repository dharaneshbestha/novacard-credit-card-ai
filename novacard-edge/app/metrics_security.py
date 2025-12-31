from prometheus_client import Counter

edge_security_events_total = Counter(
    "edge_security_events_total",
    "Security events in edge service",
    ["event", "result"],
)
