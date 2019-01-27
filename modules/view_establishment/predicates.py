"""Contains code related to the View Establishment module Algorithm 2."""

from resolve.enums import Function, Module


class PredicatesAndAction():
    """Models the View Establishment predicates and actions."""

    views = []  # views[*] = {"current": *, "next": *}
    vChange = False
    DF_VIEW = 0
    TEE = None
    RST_PAIR = {"current": TEE, "next": DF_VIEW}  # Default hardwired view Pair
    id = 0
    no_nodes = 0
    no_byz = 0
    view_module = None
    resolver = None

    def __init__(self, module, resolver, n=2, id=0, f=0):
        """Initializes the module."""
        self.views = [{} for i in range(n)]
        self.id = id
        self.view_module = module
        self.no_byz = f
        self.no_nodes = n
        self.resolver = resolver

    # Macros
    def stale_v(self, node_k):
        """Method description.

        Returns true of node k is stale,
        meaning node k is in a phase that is not legit.
        """
        raise NotImplementedError

    def legit_phs_zero(self, vpair):
        """Returns true if it is legit to be in phase 0 with view pair vp."""
        raise NotImplementedError

    def legit_phs_one(self, vpair):
        """Returns true if it is legit to be in phase 1 with view pair vp."""
        raise NotImplementedError

    def type_check(self, vpair):
        """Checks the views in the view pair vp for illegal views (numbers)."""
        raise NotImplementedError

    def valid(self, msg, node_k):
        """Validates the msg from node k and checks if structure is stale."""
        raise NotImplementedError

    def same_v_set(self, node_j, phase=-1):
        """Method description.

        Returns a set of processors that has the view pair as node j
        (and phase if passed)
        and if node j is not stale.
        """
        raise NotImplementedError

    def transit_adopble(self, node_j, phase, mode):
        """Methoid description.

        Checks if 3f+1 processors have reported to remain in
        or transiting to the phase.
        """
        raise NotImplementedError

    def transit_set(self, node_j, phase, mode):
        """Method description.

        If called with mode = "REMAIN"
        - Returns the set of nodes that will support
        to remain in the same view as node j.
        If called with mode = "FOLLOW
        - Returns the set of nodes that will support
        to follow to a new view or to a view change.
        """
        raise NotImplementedError

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
        raise NotImplementedError

    def adopt(self, vpair):
        """Assign the current view pair as vpair."""
        raise NotImplementedError

    def establishable(self, phase, mode):
        """Method description.

        Checks if 4f+1 nodes are willing to move to a view change (phase 0)
        or to a new view (phase 1).
        """
        raise NotImplementedError

    def establish(self):
        """Update the current view in the view pair to the next view."""
        raise NotImplementedError

    def next_view(self):
        """Updates the next view in the view pair to upcoming view."""
        raise NotImplementedError

    def reset_v_change(self):
        """The node is no longer in a view change."""
        raise NotImplementedError

    # Interface functions
    def need_reset(self):
        """True if the replication module requires a reset."""
        return (self.stale_v() and self.resolver.execute(
                module=Module.REPLICATION_MODULE,
                func=Function.REPLICA_FLUSH
                ))

    def reset_all(self):
        """Reset all modules."""
        self.views = [self.RST_PAIR for i in range(self.no_nodes)]
        self.view_module.init_module()
        self.resolver.execute(
            module=Module.REPLICATION_MODULE,
            func=Function.REP_REQUEST_RESET
        )
        return("Reset")

    def view_change(self):
        """A view change is required."""
        self.vChange = True

    def get_view(self, node_j):
        """Returns the most recent reported view of node_j."""
        if (node_j == self.id or
                (self.view_module.phs[self.id] == 0 and
                    self.view_module.witnes_seen())):
            if self.allow_service():
                return self.views[self.id].get("current")
            return self.TEE
        return self.views[node_j].get("current")

    def allow_service(self):
        """Method description.

        Returns true if atleast 3f+1 nodes has the same view as
        current node and current node is not in a view change
        """
        return (len(self.same_v_set(self.id)) > 3 * self.no_byz and
                self.view_module.phs[self.id] == 0 and
                self.views[self.id].get("current") ==
                self.views[self.id].get("next"))

    def automation(self, type, phase, case):
        """Perform the action corresponding to the current situation."""
        raise NotImplementedError

    def auto_max_case(self, phase):
        """Returns the max case for the phase."""
        return 3 if phase == 0 else 3

    def get_info(self, node_k):
        """Returns the most recent reported view of node k."""
        return self.views[node_k]

    def set_info(self, vpair, node_k):
        """Sets the most recent view of node k to the reported view."""
        self.views[node_k] = vpair
