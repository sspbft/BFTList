"""Module containing helpers and enums related to Byzantine behaviour."""

# standard
import logging
import os

# globals
logger = logging.getLogger(__name__)

# byzantine behaviors
NONE = "NONE"
UNRESPONSIVE = "UNRESPONSIVE"
DIFFERENT_VIEWS = "DIFFERENT_VIEWS"
FORCING_RESET = "FORCING_RESET"
STOP_ASSIGNING_SEQNUMS = "STOP_ASSIGNING_SEQNUMS"
ASSIGN_DIFFERENT_SEQNUMS = "ASSIGN_DIFFERENT_SEQNUMS"
REUSE_SEQNUMS = "REUSE_SEQNUMS"
SEQNUM_OUT_BOUND = "SEQNUM_OUT_BOUND"
WRONG_CCSP = "WRONG_CCSP"
MODIFY_CLIENT_REQ = "MODIFY_CLIENT_REQ"
UNRESPONSIVE_TO_HALF = "UNRESPONSIVE_TO_HALF"

BYZ_BEHAVIORS = [
    UNRESPONSIVE,
    DIFFERENT_VIEWS,
    FORCING_RESET,
    STOP_ASSIGNING_SEQNUMS,
    ASSIGN_DIFFERENT_SEQNUMS,
    REUSE_SEQNUMS,
    SEQNUM_OUT_BOUND,
    WRONG_CCSP,
    MODIFY_CLIENT_REQ,
    UNRESPONSIVE_TO_HALF
]

# get pre-configured byzantine behavior on load
byz_behavior = os.getenv("BYZANTINE_BEHAVIOR", NONE)


def is_byzantine():
    """Returns true if node is configured to act Byzantine."""
    return byz_behavior in BYZ_BEHAVIORS


def get_byz_behavior():
    """Returns the configured Byzantine behavior for this node."""
    if byz_behavior != NONE and byz_behavior not in BYZ_BEHAVIORS:
        logger.error("Node not configured correctly for Byzantine behavior")
    return byz_behavior


def is_valid_byz_behavior(behavior):
    """Returns True if the supplied behavior is a valid Byzantine behavior."""
    return behavior in BYZ_BEHAVIORS or behavior == NONE


def set_byz_behavior(new_behavior):
    """Sets the Byzantine behavior for this node. Used during runtime."""
    global byz_behavior

    if new_behavior == NONE or is_valid_byz_behavior(new_behavior):
        byz_behavior = new_behavior


def is_unresponsive():
    """Helper method that returns True if this node is UNRESPONSIVE."""
    return byz_behavior == UNRESPONSIVE
