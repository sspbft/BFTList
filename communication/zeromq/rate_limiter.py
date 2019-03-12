"""Simple rate limiter that blocks until message queues are cleared."""

# standard
import asyncio
import os
import logging

# local
from modules.constants import INTEGRATION_RUN_SLEEP, RUN_SLEEP, MAX_QUEUE_SIZE

logger = logging.getLogger(__name__)
resolver = None


async def sleep():
    """Sleeps if any of the sender messages queues are considered full."""
    delay = 0
    if os.getenv("INTEGRATION_TEST"):
        delay = INTEGRATION_RUN_SLEEP
    else:
        delay = float(os.getenv("RUN_SLEEP", RUN_SLEEP))

    while queues_are_full():
        await asyncio.sleep(delay)


def queues_are_full():
    """Returns True if at least on sender message queue is considered full."""
    for s in resolver.senders.values():
        if s.msg_queue.qsize() > MAX_QUEUE_SIZE:
            return True
    return False


def throttle():
    """Helper method that can be used to throttle based on message queues."""
    asyncio.run(sleep())
