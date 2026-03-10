"""
OpenTelemetry tracing initialization for AgentricAI.
"""
from opentelemetry import trace
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor


def init_tracing(app=None, service_name: str = "agentricai"):
    jaeger_exporter = JaegerExporter(
        agent_host_name="localhost",
        agent_port=6831,
    )

    trace.set_tracer_provider(TracerProvider())
    trace.get_tracer_provider().add_span_processor(
        BatchSpanProcessor(jaeger_exporter)
    )
    
    if app is not None:
        FastAPIInstrumentor.instrument_app(app)
    RequestsInstrumentor().instrument()


def get_tracer(name: str = __name__):
    return trace.get_tracer(name)
