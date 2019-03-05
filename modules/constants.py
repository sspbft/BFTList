"""Constant string values for the modules"""
import sys

# View Establishment module
CURRENT = "current"
NEXT = "next"
VIEWS = "views"
PHASE = "phase"
WITNESSES = "witnesses"

# Replication module
CLIENT_REQ = "client_request"
REP_STATE = "rep_state"
R_LOG = "r_log"
PEND_REQS = "pend_reqs"
REQ_Q = "req_q"
LAST_REQ = "last_req"
CON_FLAG = "con_flag"
VIEW_CHANGE = "view_change"
REQUEST = "request"
X_SET = "x_set"
SEQUENCE_NO = "sequence_no"
STATUS = "status"
REPLY = "reply"
VIEW = "view"
PRIM = "prim"
CLIENT = "client"
REPLY = "reply"

RUN_SLEEP = 0.05
MAXINT = sys.maxsize  # Sequence number limit
SIGMA = 10  # Threshold for assigning sequence numbers

# Primary Monitoring
V_STATUS = "v_status"
NEED_CHANGE = "need_change"
NEED_CHG_SET = "need_chg_set"
THRESHOLD = 30  # Threshold for liveness, beat-variable
