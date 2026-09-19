import unittest
from rehab_pose.contract import rep_to_contract


class ContractTests(unittest.TestCase):
    def test_v01_rep_maps_to_stable_contract(self):
        rep={'index':2,'start_s':1.,'end_s':5.125,'knee_peak_deg':168.,
             'target_comparison':{'amplitude_met':False,'extension_time_met':False,
                                  'return_time_met':True}}
        events=[{'timestamp_s':3,'code':'TRUNK_FORWARD'},
                {'timestamp_s':8,'code':'THIGH_MOVEMENT'}]
        self.assertEqual(rep_to_contract(rep,events),
                         {'rep_index':2,'peak_angle':168.,'duration_ms':4125,
                          'valid':False,'flags':['amplitude_low','too_fast','trunk_lean']})

    def test_valid_follows_contract_not_hold_target(self):
        rep={'index':1,'start_s':0.,'end_s':9.,'max_included_deg':172.,
             'target_comparison':{'amplitude_met':True,'hold_met':False,
                                  'extension_time_met':True,'return_time_met':True}}
        self.assertTrue(rep_to_contract(rep)['valid'])


if __name__=='__main__':unittest.main()

