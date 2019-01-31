"""Contains code related to the View Establishment module Algorithm 2."""

from resolve.enums import Function, Module
from modules.enums import ViewEstablishmentEnums


class PredicatesAndAction():
    """Models the View Establishment predicates and actions."""

    CURRENT = "current"
    NEXT = "next"
    FOLLOW = "follow"
    REMAIN = "remain"

    views = []  # views[*] = {"current": *, "next": *}
    vChange = False
    DF_VIEW = 0
    TEE = None
    RST_PAIR = {CURRENT: TEE, NEXT: DF_VIEW}  # Default hardwired view Pair
    id = 0
    number_of_nodes = 0
    number_of_byzantine = 0
    view_module = None
    resolver = None

    # Added variables
    # In automation (*, 0, 0) the found view pair in predicates need to
    # be store until the action (adopting the view pair) has been carried out.
    view_pair_to_adopt = None

    def __init__(self, module, resolver, n=2, id=0, f=0):
        """Initializes the module."""
        self.views = [{self.CURRENT: None, self.NEXT: None} for i in range(n)]
        self.id = id
        self.view_module = module
        self.number_of_byzantine = f
        self.number_of_nodes = n
        self.resolver = resolver

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
        return ((vpair.get(self.CURRENT) == vpair.get(self.NEXT) or
                vpair == self.RST_PAIR) and
                self.type_check(vpair)
                )

    def legit_phs_one(self, vpair):
        """Returns true if it is legit to be in phase 1 with view pair vp."""
        return (vpair.get(self.CURRENT) != vpair.get(self.NEXT) and
                self.type_check(vpair)
                )

    def type_check(self, vpair):
        """Checks the views in the view pair vp for illegal views (numbers)."""
        return (vpair.get(self.NEXT) != self.TEE and
                (vpair.get(self.CURRENT) == self.TEE or
                0 <= vpair.get(self.CURRENT) <= (self.number_of_nodes - 1) or
                0 <= vpair.get(self.NEXT) <= (self.number_of_nodes - 1))
                )

    def valid(self, msg, node_k):
        """Validates the msg from node k and checks if structure is stale."""
        raise NotImplementedError

    def same_v_set(self, node_j, phase=-1):
        """Method description.

        Returns a set of processors that has the view pair as node j
        (and phase if passed)
        and if node j is not stale.
        """
        processor_set = set()
        for processor_id, view_pair in enumerate(self.views):
            if(self.view_module.get_phs(processor_id) == phase and
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
        If called with mode = "FOLLOW
        - Returns the set of nodes that will support
        to follow to a new view or to a view change.
        """
        processor_set = set()
        for processor_id, view_pair in enumerate(self.views):
            if(self.view_module.get_phs(processor_id) != phase and
                self.transition_cases(node_j, view_pair, phase, mode) and not
                    self.stale_v(processor_id)):
                        processor_set.add(processor_id)
        return processor_set

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
        if(mode == self.REMAIN):
            return(
                vpair.get(self.NEXT) == self.views[node_j].get(self.CURRENT)
            )
        elif(mode == self.FOLLOW):
            if(phase == 0):
                return(
                    vpair.get(self.NEXT) ==
                    ((self.views[node_j].get(self.CURRENT) + 1) %
                        self.number_of_nodes)
                )
            elif(phase == 1):
                return(
                    vpair.get(self.CURRENT) ==
                    self.views[node_j].get(self.NEXT)
                )
            else:
                raise ValueError('Not a valid phase: {}'.format(phase))
        else:
            raise ValueError('Not a valid mode: {}'.format(mode))

    def adopt(self, vpair):
        """Assign the current view pair as vpair."""
        self.views[self.id].update({self.NEXT: vpair.get(self.CURRENT)})

    # In the code, sometimes view of self.id is used as input and sometimes
    # not. I choose to remove it because it always uses the current
    # processors view as input to transit_set.
    def establishable(self, phase, mode):
        """Method description.

        Checks if 4f+1 nodes are willing to move to a view change (phase 0)
        or to a new view (phase 1).
        """
        return (len(self.same_v_set(
                    self.views[self.id], self.view_module.get_phs(self.id))) +
                len(self.transit_set(self.id, phase, mode)) >=
                (4 * self.number_of_byzantine + 1)
                )

    def establish(self):
        """Update the current view in the view pair to the next view."""
        self.views[self.id].update(
            {'current': self.views[self.id].get(self.NEXT)})

    def next_view(self):
        """Updates the next view in the view pair to upcoming view."""
        self.views[self.id].update({'next':
                                    (self.views[self.id].get(self.CURRENT) + 1)
                                    % self.number_of_nodes
                                    })

    def reset_v_change(self):
        """The node is no longer in a view change."""
        self.vChange = False

    # Interface functions
    def need_reset(self):
        """True if the replication module requires a reset."""
        return (self.stale_v() and self.resolver.execute(
                module=Module.REPLICATION_MODULE,
                func=Function.REPLICA_FLUSH
                ))

    def reset_all(self):
        """Reset all modules."""
        self.views = [self.RST_PAIR for i in range(self.number_of_nodes)]
        self.view_module.init_module()
        self.resolver.execute(
            module=Module.REPLICATION_MODULE,
            func=Function.REP_REQUEST_RESET
        )
        return(ViewEstablishmentEnums.RESET)

    def view_change(self):
        """A view change is required."""
        self.vChange = True

    def get_view(self, node_j):
        """Returns the most recent reported view of node_j."""
        if (node_j == self.id and
                self.view_module.get_phs(self.id) == 0 and
                self.view_module.witnes_seen()):
            if self.allow_service():
                return self.views[self.id].get(self.CURRENT)
            return self.TEE
        return self.views[node_j].get(self.CURRENT)

    def allow_service(self):
        """Method description.

        Returns true if atleast 3f+1 nodes has the same view as
        current node and current node is not in a view change
        """
        return (len(self.same_v_set(self.id)) >
                3 * self.number_of_byzantine and
                self.view_module.get_phs(self.id) == 0 and
                self.views[self.id].get(self.CURRENT) ==
                self.views[self.id].get(self.NEXT))

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
            raise ValueError('Not a valid phase: {}'.format(phase))

    def automation_phase_0(self, type, case):
        """Perform the action corresponding to the current case of phase 0."""
        # Predicates
        if(type == ViewEstablishmentEnums.PREDICATE):
            # True if a view pair is adoptable but is not the view of
            # processor i
            if(case == 0):
                for processor_id, view_pair in enumerate(self.views):
                    if (self.transit_adopble(processor_id, 0, self.FOLLOW) and
                        self.views[self.id].get(self.CURRENT) !=
                            view_pair.get(self.CURRENT)):
                        self.view_pair_to_adopt = view_pair
                        return True
                return False

            # True if a view change was instructed by Primary Monitoring
            elif(case == 1):
                return (self.vChange and self.establishable(0, self.FOLLOW))

            # Monitoring/Waiting for more processors acknowledgement
            elif(case == 2):
                return (self.transit_adopble(self.id, 0, self.REMAIN) or
                        self.views[self.id] == self.RST_PAIR)

            # True if there is no adoptable view (predicates for other cases
            #  are false)
            elif(case == 3):
                return True

            # Not a valid case
            else:
                raise ValueError('Not a valid case: {}'.format(case))

        # Actions
        elif(type == ViewEstablishmentEnums.ACTION):

            # Adopt the new view
            if(case == 0):
                if(self.view_pair_to_adopt):
                    self.adopt(self.view_pair_to_adopt)
                    self.view_pair_to_adopt = None
                    self.view_module.next_phs()
                    self.reset_v_change()
                    return ViewEstablishmentEnums.NO_RETURN_VALUE
                else:
                    raise ValueError("Not a valid view pair to adopt")

            # Increment view (next view)
            elif(case == 1):
                self.next_view()
                self.view_module.next_phs()
                return ViewEstablishmentEnums.NO_RETURN_VALUE

            # No action and reset the v_change-variable
            elif(case == 2):
                self.reset_v_change()
                return ViewEstablishmentEnums.NO_ACTION

            # Full reset
            elif(case == 3):
                self.reset_v_change()
                return self.reset_all()

            # Not a valid case
            else:
                raise ValueError('Not a valid case: {}'.format(case))

        # Not a valid type (act or pred)
        else:
            raise ValueError('Not a valid type: {}'.format(type))

    def automation_phase_1(self, type, case):
        """Perform the action corresponding to the current case of phase 1."""
        # Predicates
        if(type == ViewEstablishmentEnums.PREDICATE):

            # # True if a view pair is adoptable but is not the view of
            # processor i
            if(case == 0):
                for processor_id, view_pair in enumerate(self.views):
                    if (self.transit_adopble(processor_id, 1, self.FOLLOW) and
                        self.views[self.id].get(self.NEXT) !=
                            view_pair.get(self.CURRENT)):
                        self.view_pair_to_adopt = view_pair
                        return True
                return False

            # True if the view intended to be install is establishable
            elif(case == 1):
                return self.establishable(1, self.FOLLOW)

            # Monitoring/Waiting for more processors acknowledgement
            elif(case == 2):
                return self.transit_adopble(self.id, 1, self.REMAIN)

            # True if there is no adoptable view (predicates for other cases
            # are false)
            elif(case == 3):
                return True

            # Not a valid case
            else:
                raise ValueError('Not a valid case: {}'.format(case))

        # Actions
        elif(type == ViewEstablishmentEnums.ACTION):

            # Adopt the new transit view
            if(case == 0):
                if(self.view_pair_to_adopt):
                    self.adopt(self.view_pair_to_adopt)
                    self.view_pair_to_adopt = None
                    self.reset_v_change()
                    return ViewEstablishmentEnums.NO_RETURN_VALUE
                else:
                    raise ValueError("Not a valid view pair to adopt")

            # Apply changes to view: establish the new view
            elif(case == 1):
                if(self.views[self.id] == self.RST_PAIR):
                    self.resolver.execute(
                        module=Module.REPLICATION_MODULE,
                        func=Function.REPLICA_FLUSH
                    )
                self.establish()
                self.reset_v_change()
                self.view_module.next_phs()
                return ViewEstablishmentEnums.NO_RETURN_VALUE

            # Return no action
            elif(case == 2):
                self.reset_v_change()
                return ViewEstablishmentEnums.NO_ACTION

            # Reset all
            elif(case == 3):
                return self.reset_all()

            # Not a valid case
            else:
                raise ValueError('Not a valid case: {}'.format(case))

        # Not a valid type (act or pred)
        else:
            raise ValueError('Not a valid type: {}'.format(type))

    def auto_max_case(self, phase):
        """Returns the max case for the phase."""
        return 3 if phase == 0 else 3

    def get_info(self, node_k):
        """Returns the most recent reported view of node k."""
        return self.views[node_k]

    def set_info(self, vpair, node_k):
        """Sets the most recent view of node k to the reported view."""
        self.views[node_k] = vpair
