"""Module containing helpers and enums related to Byzantine behaviour."""

# standard
import logging
import os

# globals
logger = logging.getLogger(__name__)

# byzantine behaviors
UNRESPONSIVE = "UNRESPONSIVE"
DIFFERENT_VIEWS = "DIFFERENT_VIEWS"
FORCING_RESET = "FORCING_RESET"
STOP_ASSIGNING_SEQNUMS = "STOP_ASSIGNING_SEQNUMS"
ASSIGN_DIFFERENT_SEQNUMS = "ASSIGN_DIFFERENT_SEQNUMS"
REUSE_SEQNUMS = "REUSE_SEQNUMS"
SEQNUM_OUT_BOUND = "SEQNUM_OUT_BOUND"
MODIFY_CLIENT_REQ = "MODIFY_CLIENT_REQ"

BYZ_BEHAVIORS = [
    UNRESPONSIVE,
    DIFFERENT_VIEWS,
    FORCING_RESET,
    STOP_ASSIGNING_SEQNUMS,
    ASSIGN_DIFFERENT_SEQNUMS,
    REUSE_SEQNUMS,
    SEQNUM_OUT_BOUND,
    MODIFY_CLIENT_REQ
]


def is_byzantine():
    """Returns true if node is configured to act Byzantine."""
    if os.getenv("BYZANTINE") and os.getenv("BYZANTINE_BEHAVIOR"):
        return True
    return False


def get_byz_behavior():
    """Returns the configured Byzantine behavior for this node."""
    behavior = os.getenv("BYZANTINE_BEHAVIOR")
    if is_byzantine() and (behavior is None or behavior not in BYZ_BEHAVIORS):
        logger.error("Node not configured correctly for Byzantine behavior")
    return behavior
