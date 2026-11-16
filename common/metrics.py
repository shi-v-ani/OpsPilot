from prometheus_client import Counter, Histogram

REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["service", "method", "path", "status"],
)

REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency",
    ["service", "method", "path"],
)

OUTBOUND_REQUESTS = Counter(
    "outbound_requests_total",
    "Outbound HTTP calls from this service",
    ["service", "target", "status"],
)
