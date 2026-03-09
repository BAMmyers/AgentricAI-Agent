"""
Prometheus metrics definitions and middleware.
"""
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from fastapi import Request, Response
import time

# Counters
requests_total = Counter(
    'agentricai_requests_total',
    'Total requests',
    ['endpoint', 'method', 'status']
)

agent_invocations = Counter(
    'agentricai_agent_invocations_total',
    'Total agent invocations',
    ['agent_id', 'status']
)

# Histograms
request_duration = Histogram(
    'agentricai_request_duration_seconds',
    'Request duration',
    ['endpoint'],
    buckets=(0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0)
)

agent_latency = Histogram(
    'agentricai_agent_latency_seconds',
    'Agent response latency',
    ['agent_id']
)

# Gauges
active_conversations = Gauge(
    'agentricai_active_conversations',
    'Active conversations'
)

memory_db_size = Gauge(
    'agentricai_memory_db_size_bytes',
    'Memory database size'
)

# Middleware function
async def metrics_middleware(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    duration = time.time() - start
    request_duration.labels(endpoint=request.url.path).observe(duration)

    requests_total.labels(
        endpoint=request.url.path,
        method=request.method,
        status=response.status_code
    ).inc()
    return response

# Export endpoint function
async def metrics_endpoint():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
