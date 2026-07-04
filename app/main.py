import uuid
import structlog
from fastapi import FastAPI, Request
from tortoise.contrib.fastapi import register_tortoise
from app.infrastructure.persistence.config import TORTOISE_CONFIG
from app.interfaces.api.endpoints import router

structlog.configure(
    processors=[
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ]
)

app = FastAPI(title="finCard API")

@app.middleware("http")
async def add_correlation_id(request: Request, call_next):
    correlation_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(correlation_id=correlation_id)
    response = await call_next(request)
    response.headers["X-Correlation-ID"] = correlation_id
    return response

app.include_router(router)

register_tortoise(
    app,
    config=TORTOISE_CONFIG,
    generate_schemas=True,
    add_exception_handlers=True,
)

@app.on_event("startup")
async def startup_db_fix():
    from tortoise import connections
    conn = connections.get("default")
    try:
        # Check if user_id exists in transactions
        res = await conn.execute_query_dict("SELECT column_name FROM information_schema.columns WHERE table_name='transactions' AND column_name='user_id'")
        if not res:
            print("Fixing schema: Adding user_id to transactions")
            await conn.execute_script('ALTER TABLE "transactions" ADD COLUMN "user_id" UUID;')
    except Exception as e:
        print(f"Startup DB fix error: {e}")
