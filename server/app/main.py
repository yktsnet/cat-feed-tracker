import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from apscheduler.schedulers.background import BackgroundScheduler
from app.api import events, webhook
from app.line.notify import send_scheduled_notify, send_alert_if_needed

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)

scheduler = BackgroundScheduler()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 定時通知（UTC）
    scheduler.add_job(send_scheduled_notify, "cron", hour=2,  minute=0, args=["morning"])
    scheduler.add_job(send_scheduled_notify, "cron", hour=7,  minute=0, args=["afternoon"])
    scheduler.add_job(send_scheduled_notify, "cron", hour=12, minute=0, args=["night"])
    # 上限アラートチェック（5分ごと）
    scheduler.add_job(send_alert_if_needed, "interval", minutes=5)
    scheduler.start()
    yield
    scheduler.shutdown()


app = FastAPI(title="cat-feed-tracker", version="0.2.0", lifespan=lifespan)

app.include_router(events.router,  prefix="/api")
app.include_router(webhook.router, prefix="/api")


@app.get("/healthz")
def healthz():
    return {"status": "ok"}
