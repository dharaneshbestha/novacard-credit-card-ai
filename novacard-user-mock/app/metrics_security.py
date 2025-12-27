from prometheus_client import Counter

user_security_events_total = Counter(
    "user_security_events_total",
    "Security events in user service",
    ["event", "result", "kid"],
)