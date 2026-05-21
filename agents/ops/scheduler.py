"""Background scheduler for continuous self-healing (production)."""

import logging
import os
import time

from agents.ops.self_heal import run_heal_cycle

logger = logging.getLogger("ops.scheduler")

INTERVAL_SEC = int(os.getenv("OPS_HEAL_INTERVAL_SEC", "300"))


def main():
    logging.basicConfig(level=logging.INFO)
    logger.info("Starting ops heal scheduler every %ss", INTERVAL_SEC)
    while True:
        try:
            run_heal_cycle()
        except Exception:
            logger.exception("Heal cycle error")
        time.sleep(INTERVAL_SEC)


if __name__ == "__main__":
    main()
