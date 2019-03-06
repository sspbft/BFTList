# standard
import asyncio
import os
import logging

# local
from modules.constants import INTEGRATION_RUN_SLEEP, RUN_SLEEP, MAX_QUEUE_SIZE

logger = logging.getLogger(__name__)

resolver = None

async def sleep():
    delay = 0
    if os.getenv("INTEGRATION_TEST"):
        delay = INTEGRATION_RUN_SLEEP
    else:
        delay = float(os.getenv("RUN_SLEEP", RUN_SLEEP))

    while queues_are_full():
        await asyncio.sleep(delay)

def queues_are_full():
    for s in resolver.senders.values():
        if s.msg_queue.qsize() > MAX_QUEUE_SIZE:
            return True
    return False

def throttle():
    asyncio.run(sleep())