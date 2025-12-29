from prometheus_client import Counter, Gauge, Histogram

# Requests forwarded to downstream services
downstream_requests_total = Counter(
    "edge_downstream_requests_total",
    "Total downstream requests",
    ["service", "method", "result"],  # result: success|5xx|timeout|unreachable|circuit_open|other_error
)

downstream_latency_seconds = Histogram(
    "edge_downstream_latency_seconds",
    "Downstream request latency in seconds",
    ["service", "method"],
)

circuit_state = Gauge(
    "edge_circuit_state",
    "Circuit breaker state (0=closed, 1=open, 2=half_open)",
    ["service"],
)

def set_circuit_state(service: str, state: str):
    mapping = {"CLOSED": 0, "OPEN": 1, "HALF_OPEN": 2}
    circuit_state.labels(service=service).set(mapping.get(state, -1))