"""Module containing helpers and enums related to Byzantine behaviour."""

import logging
import os

logger = logging.getLogger(__name__)
UNRESPONSIVE = "UNRESPONSIVE"
DIFFERENT_VIEWS = "DIFFERENT_VIEWS"
FORCING_RESET = "FORCING_RESET"
BYZ_BEHAVIORS = [UNRESPONSIVE, DIFFERENT_VIEWS, FORCING_RESET]


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
