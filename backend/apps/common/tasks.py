"""Safe broker connectivity task; it handles no patient data and stores no result."""
from config.celery import app
@app.task(ignore_result=True)
def broker_ping(): return "ok"

