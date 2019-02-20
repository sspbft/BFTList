import unittest
from unittest.mock import Mock, MagicMock
from resolve.resolver import Resolver
from modules.primary_monitoring.module import PrimaryMonitoringModule
from resolve.enums import Function, Module
from modules.enums import PrimaryMonitoringEnums as enums
from modules.constants import V_STATUS, PRIM, NEED_CHANGE, NEED_CHG_SET


class TestPredicatesAndAction(unittest.TestCase):

    def setUp(self):
        self.resolver = Resolver()

    # Macros
    def test_clean_state(self):
        # Let primary be 0
        self.resolver.execute = MagicMock(return_value = 0)
        primary_mod = PrimaryMonitoringModule(0, self.resolver, 6, 1)
        # Create a non-default vcm
        primary_mod.vcm = [{V_STATUS: enums.V_CHANGE, PRIM: 1, NEED_CHANGE: True, NEED_CHG_SET: {0,2}} for i in range(6)]
        # Check so that vcm is not in default state
        self.assertNotEqual(primary_mod.vcm,
            [{V_STATUS: enums.OK, PRIM: 0, NEED_CHANGE: False, NEED_CHG_SET: set()} for i in range(6)])
        # Clean the vcm and check that all elements are set to the default
        primary_mod.clean_state()
        self.assertEqual(primary_mod.vcm,
            [{V_STATUS: enums.OK, PRIM: 0, NEED_CHANGE: False, NEED_CHG_SET: set()} for i in range(6)])

    def test_sup_change(self):
        # Let primary be 0
        self.resolver.execute = MagicMock(return_value = 0)
        primary_mod = PrimaryMonitoringModule(0, self.resolver, 6, 1)

        # All nodes are needing change
        primary_mod.vcm = [{V_STATUS: enums.OK, PRIM: 0, NEED_CHANGE: True, NEED_CHG_SET: {0,1,2,3,4,5}} for i in range(6)]
        self.assertTrue(primary_mod.sup_change(6))
        # Length of the processor set will not be 7
        self.assertFalse(primary_mod.sup_change(7))

        # The intersection will not be large enough, all have same prim
        # but only 0,1,2 is in NEED_CHG_SET
        primary_mod.vcm = [{V_STATUS: enums.OK,
                           PRIM: 0,
                           NEED_CHANGE: True,
                           NEED_CHG_SET: {0,1,2}} for i in range(3)] + [
                             {V_STATUS: enums.OK,
                           PRIM: 0,
                           NEED_CHANGE: True,
                           NEED_CHG_SET: {}} for i in range(3,6)  
                           ]

        self.assertFalse(primary_mod.sup_change(6))

        # The amount if processor that requires a change are enough and the intersection big enough.
        primary_mod.vcm = [{V_STATUS: enums.OK,
                    PRIM: 0,
                    NEED_CHANGE: True,
                    NEED_CHG_SET: {0,1,2,3}} for i in range(4)] + [
                        {V_STATUS: enums.OK,
                    PRIM: 0,
                    NEED_CHANGE: False,
                    NEED_CHG_SET: {}} for i in range(4,6)  
                    ]
        
        self.assertTrue(primary_mod.sup_change(4))

    # Interface functions
    def test_no_view_change(self):
        # Let primary be 0
        self.resolver.execute = MagicMock(return_value = 0)
        primary_mod = PrimaryMonitoringModule(0, self.resolver, 6, 1)

        # Default value is OK 
        self.assertTrue(primary_mod.no_view_change())

        # Change V_STATUS to not OK
        primary_mod.vcm[primary_mod.id] = {V_STATUS: enums.NO_SERVICE, PRIM: 0, NEED_CHANGE: False, NEED_CHG_SET: {}} 
        self.assertFalse(primary_mod.no_view_change())

    # Added functions
    def test_get_df_vcm(self):        
        # Let primary be 1
        self.resolver.execute = MagicMock(return_value = 1)
        primary_mod = PrimaryMonitoringModule(0, self.resolver, 6, 1)

        self.assertEqual(primary_mod.get_default_vcm(0),
            {V_STATUS: enums.OK, PRIM: 1, NEED_CHANGE: False, NEED_CHG_SET: set()})
        