import os
from celery import Celery

REDIS_URL = os.getenv("REDIS_URL", os.getenv("REDIS_URL", "redis://localhost:6379/0"))
celery_app = Celery("swarm", broker=REDIS_URL, backend=REDIS_URL)


# Example task registration
@celery_app.task(name="swarm.create_bundle")
def create_bundle_task(project_id: str, customer_email: str = None):
    from backend.replicator import SwarmReplicator

    r = SwarmReplicator.create_company_bundle(project_id, customer_email=customer_email)
    return r
