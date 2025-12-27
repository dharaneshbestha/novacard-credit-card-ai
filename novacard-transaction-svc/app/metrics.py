# from prometheus_client import Counter, Histogram

# # Drift detection
# snapshot_drift_detected_total = Counter(
#     "txn_snapshot_drift_detected_total",
#     "Snapshot drift detected (ledger vs snapshot mismatch)",
#     labelnames=["service", "reason"],
# )

# snapshot_rebuild_total = Counter(
#     "txn_snapshot_rebuild_total",
#     "Snapshot rebuild operations performed",
#     labelnames=["service", "reason"],
# )

# snapshot_rebuild_latency_seconds = Histogram(
#     "txn_snapshot_rebuild_latency_seconds",
#     "Time spent rebuilding snapshots",
#     labelnames=["service"],
# )

from __future__ import annotations

from prometheus_client import Counter, Histogram, Gauge

# Service level request metrics
http_requests_total = Counter(
    "txn_http_requests_total",
    "Total HTTP requests",
    ["path", "method", "status"],
)

http_latency_seconds = Histogram(
    "txn_http_latency_seconds",
    "HTTP latency in seconds",
    ["path", "method"],
)

# Snapshot metrics (C7.2.7/7.2.8)
snapshot_rebuild_total = Counter(
    "txn_snapshot_rebuild_total",
    "Snapshot rebuild operations performed",
    ["service", "reason"],
)

snapshot_drift_detected_total = Counter(
    "txn_snapshot_drift_detected_total",
    "Snapshot drift detections",
    ["service", "reason"],
)

# Idempotency metrics
idempotency_total = Counter(
    "txn_idempotency_total",
    "Idempotency outcomes",
    ["result"],
)

# Optional: circuit/health gauges later
service_up = Gauge("txn_service_up", "Service up indicator")