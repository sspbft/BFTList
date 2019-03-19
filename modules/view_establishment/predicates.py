"""Contains code related to the View Establishment module Algorithm 2."""

# standard
from copy import deepcopy
import logging

# local
from resolve.enums import Function, Module
from modules.enums import ViewEstablishmentEnums as enums
from modules.constants import CURRENT, NEXT

# globals
logger = logging.getLogger(__name__)


class PredicatesAndAction():
    """Models the View Establishment predicates and actions."""

    # Added variables
    # In automation (*, *, 0) the found view pair in predicates need to
    # be store until the action (adopting the view pair) has been carried out.
    view_pair_to_adopt = -1

    def __init__(self, module, id, resolver, n, f):
        """Initializes the module."""
        self.views = [{CURRENT: enums.TEE, NEXT: enums.DF_VIEW}
                      for i in range(n)]
        self.id = id
        self.view_module = module
        self.number_of_byzantine = f
        self.number_of_nodes = n
        self.resolver = resolver
        self.vChange = False
        self.RST_PAIR = {CURRENT: enums.TEE, NEXT: enums.DF_VIEW}

    # Macros
    def stale_v(self, node_k):
        """Method description.

        Returns true of node k is stale,
        meaning node k is in a phase that is not legit.
        """
        return (self.view_module.get_phs(node_k) == 0 and not
                self.legit_phs_zero(self.views[node_k]) or
                (self.view_module.get_phs(node_k) == 1 and not
                    self.legit_phs_one(self.views[node_k]))
                )

    def legit_phs_zero(self, vpair):
        """Returns true if it is legit to be in phase 0 with view pair vp."""
        return ((vpair.get(CURRENT) == vpair.get(NEXT) or
                vpair == self.RST_PAIR) and
                self.type_check(vpair)
                )

    def legit_phs_one(self, vpair):
        """Returns true if it is legit to be in phase 1 with view pair vp."""
        return (vpair.get(CURRENT) != vpair.get(NEXT) and
                self.type_check(vpair)
                )

    def type_check(self, vpair):
        """Checks the views in the view pair vp for illegal views (numbers)."""
        return (vpair.get(NEXT) != enums.TEE and
                (vpair.get(NEXT) == enums.DF_VIEW or
                0 <= vpair.get(NEXT) <= (self.number_of_nodes - 1)) and
                (vpair.get(CURRENT) == enums.TEE or
                vpair.get(CURRENT) == enums.DF_VIEW or
                0 <= vpair.get(CURRENT) <= (self.number_of_nodes - 1))
                )

    def valid(self, msg):
        """Validates the msg from node k and checks if structure is stale.

        The message format is: msg[0] = phs, msg[1] = witnesses, msg[2] =
        view_pair
        """
        return ((msg[0] == 0 and self.legit_phs_zero(msg[2])) or
                (msg[0] == 1 and self.legit_phs_one(msg[2]))
                )

    def same_v_set(self, node_j, phase):
        """Method description.

        Returns a set of processors that has the view pair as node j
        (and phase if passed)
        and if node j is not stale.
        """
        processor_set = set()
        for processor_id, view_pair in enumerate(self.views):
            # check if either have current as TEE and same next, if so they are
            # considered to be in the same view set
            if phase == 1:
                if (view_pair[CURRENT] == enums.TEE or
                   self.views[node_j][CURRENT] == enums.TEE):
                    if view_pair[NEXT] == self.views[node_j][NEXT]:
                        processor_set.add(processor_id)

            if phase is None:
                if (view_pair == self.views[node_j] and not
                        self.stale_v(processor_id)):
                    processor_set.add(processor_id)
            else:
                if (self.view_module.get_phs(processor_id) == phase and
                        view_pair == self.views[node_j] and not
                        self.stale_v(processor_id)):
                    processor_set.add(processor_id)
        return processor_set

    def transit_adopble(self, node_j, phase, mode):
        """Method description.

        Checks if 3f+1 processors have reported to remain in
        or transiting to the phase.
        """
        return(len(
            self.same_v_set(node_j, self.view_module.get_phs(node_j))
            .union(self.transit_set(node_j, phase, mode))) >=
            (3 * self.number_of_byzantine + 1)
        )

    def transit_set(self, node_j, phase, mode):
        """Method description.

        If called with mode = "REMAIN"
        - Returns the set of nodes that will support
        to remain in the same view as node j.
        If called with mode = "enums.FOLLOW
        - Returns the set of nodes that will support
        to enums.FOLLOW to a new view or to a view change.
        """
        processor_set_transit = set()
        for processor_id, view_pair in enumerate(self.views):
            if(self.view_module.get_phs(processor_id) != phase and
                self.transition_cases(node_j, view_pair, phase, mode) and not
                    self.stale_v(processor_id)):
                        processor_set_transit.add(processor_id)
        return processor_set_transit

    def transition_cases(self, node_j, vpair, phase, mode):
        """Method description.

        Examines three cases.
        mode = "REMAIN"
        - Returns true if the current view of node j is the same as vpair.next.
        mode = "FOLLOW, phase = 0
        - Returns true if vpair.next is the consecutive view of the current
        view of node j.
        mode = "FOLLOW, phase = 1
        - Returns true if vpair.current is the same as the next view of node j
        """
        if(mode == enums.REMAIN):
            return(
                vpair.get(NEXT) == self.views[node_j][CURRENT]
            )
        elif(mode == enums.FOLLOW):
            if(phase == 0):
                if self.views[node_j][CURRENT] != enums.TEE:
                    return(
                        vpair.get(NEXT) ==
                        ((self.views[node_j][CURRENT] + 1) %
                            self.number_of_nodes)
                    )
                return (vpair.get(NEXT) == enums.DF_VIEW)
            elif(phase == 1):
                return(
                    vpair.get(CURRENT) ==
                    self.views[node_j][NEXT]
                )
            else:
                logger.error(f"Not a valid phase: {phase}")
        else:
            logger.error(f"Not a valid mode: {mode}")

    def adopt(self, vpair):
        """Adopt the view pair."""
        self.views[self.id][NEXT] = deepcopy(vpair[NEXT])

    def establishable(self, phase, mode):
        """Method description.

        Checks if 4f+1 nodes are willing to move to a view change (phase 0)
        or to a new view (phase 1).
        """
        return (len(self.same_v_set(
                self.id, self.view_module.get_phs(self.id))) +
                len(self.transit_set(self.id, phase, mode)) >=
                (4 * self.number_of_byzantine + 1))

    def establish(self):
        """Update the current view in the view pair to the next view."""
        self.views[self.id][CURRENT] = deepcopy(self.views[
                                                self.id][NEXT])

    def next_view(self):
        """Updates the next view in the view pair to upcoming view."""
        if self.views[self.id][CURRENT] == enums.TEE:
            self.views[self.id][NEXT] = enums.DF_VIEW
        else:
            self.views[self.id][NEXT] = ((
                self.views[self.id].get(CURRENT) + 1)
                % self.number_of_nodes)

    def reset_v_change(self):
        """The node is no longer in a view change."""
        self.vChange = False

    # Interface functions
    def need_reset(self):
        """True if the replication module requires a reset."""
        return (self.stale_v(self.id) or self.resolver.execute(
                module=Module.REPLICATION_MODULE,
                func=Function.NEED_FLUSH
                ))

    def reset_all(self):
        """Reset all modules."""
        self.views = [deepcopy(self.RST_PAIR) for i in range(
                                                self.number_of_nodes)]
        self.view_module.init_module()
        self.resolver.execute(
            module=Module.REPLICATION_MODULE,
            func=Function.REP_REQUEST_RESET
        )
        logger.info("reset_all() called")
        return(enums.RESET)

    def view_change(self):
        """A view change is required."""
        logger.info("vChange is set to True by PrimMon")
        self.vChange = True

    def get_current_view(self, node_j):
        """Returns the most recent reported *current* view of node_j."""
        if (node_j == self.id and
                self.view_module.get_phs(self.id) == 0 and
                self.view_module.witnes_seen()):
            if self.allow_service():
                return self.views[self.id].get(CURRENT)
            return enums.TEE
        return self.views[node_j].get(CURRENT)

    def allow_service(self):
        """Method description.

        Returns true if atleast 3f+1 nodes has the same view as
        current node and current node is not in a view change
        """
        return (len(self.same_v_set(self.id,
                    self.view_module.get_phs(self.id))) >
                3 * self.number_of_byzantine and
                self.view_module.get_phs(self.id) == 0 and
                self.views[self.id].get(CURRENT) ==
                self.views[self.id].get(NEXT))

    def automation(self, type, phase, case):
        """Perform the action corresponding to the current situation."""
        # Phase 0, waiting for a next view
        if (phase == 0):
            return self.automation_phase_0(type, case)

        # Phase 1, in a view change
        elif(phase == 1):
            return self.automation_phase_1(type, case)

        # Not a valid phase
        else:
            logger.error(f"Not a valid phase: {phase}")

    def automation_phase_0(self, type, case):
        """Perform the action corresponding to the current case of phase 0."""
        # Predicates
        if(type == enums.PREDICATE):
            # True if a view pair is adoptable but is not the view of
            # processor i
            if(case == 0):
                for processor_id, view_pair in enumerate(self.views):
                    if processor_id != self.id:
                        # Assert that the processor doesn't end up in
                        # phase 1 with CURRENT = NEXT
                        if (self.views[self.id][CURRENT] != view_pair[NEXT] and
                           (self.views[self.id][NEXT] != view_pair[NEXT] or
                                # If own view is RST_PAIR and the other is not,
                                # the view_pair might be adoptable
                                # Own view should not remain in rst_pair
                           self.views[self.id] == self.RST_PAIR)):
                            # Assert that the view_pair is transit adoptable
                            if self.transit_adopble(
                               processor_id, 0, enums.FOLLOW):
                                logger.info(f"ADOPTING: {view_pair} with views: {self.views}")
                                self.view_pair_to_adopt = deepcopy(view_pair)
                                return True
                return False

            # True if a view change was instructed by Primary Monitoring
            elif(case == 1):
                return(
                    (self.vChange and self.establishable(0, enums.FOLLOW)) or
                    (self.views[self.id] == self.RST_PAIR and
                     self.establishable(0, enums.FOLLOW))
                )

            # Monitoring/Waiting for more processors acknowledgement
            elif(case == 2):
                return (self.transit_adopble(self.id, 0, enums.REMAIN) or
                        self.views[self.id] == self.RST_PAIR)

            # True if there is no adoptable view (predicates for other cases
            #  are false)
            elif(case == 3):
                return True

            # Not a valid case
            else:
                logger.error(f"Not a valid case: {case}")

        # Actions
        elif(type == enums.ACTION):

            # Adopt the new view
            if(case == 0):
                if(self.view_pair_to_adopt):
                    self.adopt(self.view_pair_to_adopt)
                    self.view_pair_to_adopt = -1
                    self.view_module.next_phs()
                    self.reset_v_change()
                    return enums.NO_RETURN_VALUE
                else:
                    logger.error(f"Not a valid view pair to adopt: \
                        {self.view_pair_to_adopt}")

            # Two subcases
            elif(case == 1):
                # Case 1a (increment view and move to next face
                if(self.vChange):
                    self.next_view()
                    self.view_module.next_phs()
                    self.reset_v_change()
                    return enums.NO_RETURN_VALUE
                # Case 1b (do NOT increment view, stay in RST_PAIR but move to
                #  next phase)
                elif(self.views[self.id] == self.RST_PAIR):
                    self.view_module.next_phs()
                    return enums.NO_RETURN_VALUE

            # No action and reset the v_change-variable
            elif(case == 2):
                self.reset_v_change()
                return enums.NO_ACTION

            # Full reset
            elif(case == 3):
                self.reset_v_change()
                return self.reset_all()

            # Not a valid case
            else:
                logger.error(f"Not a valid case: {case}")

        # Not a valid type (act or pred)
        else:
            logger.error(f"Not a valid type: {type}")

    def automation_phase_1(self, type, case):
        """Perform the action corresponding to the current case of phase 1."""
        # Predicates
        if(type == enums.PREDICATE):
            # True if a view pair is adoptable but is not the view of
            # processor i
            if(case == 0):
                for processor_id, view_pair in enumerate(self.views):
                    if processor_id != self.id:
                        # Assert that the processor doesn't end up in
                        # phase 1 with CURRENT = NEXT
                        if (self.views[self.id][CURRENT] != view_pair[NEXT] and
                           self.views[self.id][NEXT] != view_pair[NEXT]):
                            # Assert that the view_pair is transit adoptable
                            if self.transit_adopble(
                               processor_id, 1, enums.FOLLOW):
                                self.view_pair_to_adopt = deepcopy(
                                    view_pair)
                                return True
                return False

            # True if the view intended to be install is establishable
            elif(case == 1):
                return self.establishable(1, enums.FOLLOW)

            # Monitoring/Waiting for more processors acknowledgement
            elif(case == 2):
                return self.transit_adopble(self.id, 1, enums.REMAIN)

            # True if there is no adoptable view (predicates for other cases
            # are false)
            elif(case == 3):
                return True

            # Not a valid case
            else:
                logger.error(f"Not a valid case: {case}")

        # Actions
        elif(type == enums.ACTION):

            # Adopt the new transit view
            if(case == 0):
                if(self.view_pair_to_adopt):
                    self.adopt(self.view_pair_to_adopt)
                    self.view_pair_to_adopt = -1
                    self.reset_v_change()
                    return enums.NO_RETURN_VALUE
                else:
                    logger.error("Not a valid view pair to adopt:" +
                                 f" {self.view_pair_to_adopt}")

            # Apply changes to view: establish the new view
            elif(case == 1):
                # if(self.views[self.id] == self.RST_PAIR):
                #     self.resolver.execute(
                #         module=Module.REPLICATION_MODULE,
                #         func=Function.REPLICA_FLUSH
                #     )
                self.establish()
                self.reset_v_change()
                self.view_module.next_phs()
                return enums.NO_RETURN_VALUE

            # Return no action
            elif(case == 2):
                self.reset_v_change()
                return enums.NO_ACTION

            # Reset all
            elif(case == 3):
                self.reset_v_change()
                return self.reset_all()

            # Not a valid case
            else:
                logger.error(f"Not a valid case: {case}")

        # Not a valid type (act or pred)
        else:
            logger.error(f"Not a valid type: {type}")

    def auto_max_case(self, phase):
        """Returns the max case for the phase."""
        return 3 if phase == 0 else 3

    def get_info(self, node_k):
        """Returns the most recent reported view of node k."""
        return self.views[node_k]

    def set_info(self, vpair, node_k):
        """Sets the most recent view of node k to the reported view."""
        self.views[node_k] = vpair
