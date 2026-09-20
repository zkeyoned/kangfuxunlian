import unittest
from rehab_pose.brief_report import build_brief,brief_text


class BriefTests(unittest.TestCase):
    def test_by_set_and_all_failures_not_only_first_alert(self):
        training={'plan':{'sets':2,'reps_per_set':2,'hold_s':3}}
        reps=[{'training_set':1,'target_comparison':{'amplitude_met':False,'hold_met':False,'return_time_met':False,'extension_time_met':None}},
              {'training_set':2,'target_comparison':{'amplitude_met':True,'hold_met':True,'return_time_met':True,'extension_time_met':True}}]
        events=[{'training_set':2,'code':'TRUNK_BACKWARD'}]
        report=build_brief('1','right',training,reps,events,{1:{'frames':100,'observed_frames':70}},[])
        self.assertEqual(report['completed_reps'],2)
        self.assertEqual(len(report['sets'][0]['problems']),3)
        self.assertEqual(report['sets'][0]['needs_review_reps'],1)
        self.assertEqual(report['sets'][1]['problems'][0]['code'],'TRUNK_BACKWARD')
        self.assertIn('伸膝幅度',brief_text(report))
        self.assertIn('漏检',report['suggestions'][0])

    def test_no_records_is_not_success(self):
        report=build_brief('1','left',{'plan':{'sets':1,'reps_per_set':10,'hold_s':3}},[],[],{},[])
        self.assertIn('不能判断',report['sets'][0]['finding'])
        self.assertFalse(report['video_saved'])
        self.assertEqual(report['sets'][0]['status'],'未开始')
