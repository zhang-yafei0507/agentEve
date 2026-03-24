import uuid, time


def generate_trace_id() -> str:
    return f"trace-{uuid.uuid4().hex[:12]}-{int(time.time())}"
