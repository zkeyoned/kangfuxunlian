import copy, unittest
from contextlib import closing
from test_training_reports import ReportTests, db

class PlanTests(ReportTests):
    def test_plan_publish_draft_scope_and_validation(self):
        path=f'/api/v1/patients/{self.pid}/visual-prescription'
        body={'status':'draft','title':'测试方案','side':'right','phase':'测试','days_per_week':5,'notes':'控制返回速度',
              'items':[{'exercise_id':'seated','sets':3,'reps':12,'target_deg':175,'hold_s':3,'return_s':2,'rest_s':30}]}
        self.assertEqual(self.c.post(path,headers=self.ph,json=body).status_code,403)
        r=self.c.post(path,headers=self.th,json=body);self.assertEqual(r.status_code,200,r.text)
        self.assertIsNone(self.c.get('/api/v1/me/visual-prescription',headers=self.ph).json()['prescription'])
        body['status']='published';first=self.c.post(path,headers=self.th,json=body).json()
        visible=self.c.get('/api/v1/me/visual-prescription',headers=self.ph).json()['prescription']
        self.assertEqual(visible['items'][0]['target_deg'],175);self.assertEqual(visible['notes'],body['notes'])
        body['status']='draft';body['items'][0]['hold_s']=6
        self.c.post(path,headers=self.th,json=body)
        self.assertEqual(self.c.get('/api/v1/me/visual-prescription',headers=self.ph).json()['prescription']['id'],first['id'])
        body['status']='published';second=self.c.post(path,headers=self.th,json=body).json()
        self.assertNotEqual(first['id'],second['id'])
        self.assertIsNone(self.c.get(path,headers=self.th).json()['draft'])
        self.assertIsNone(self.c.get('/api/v1/me/visual-prescription',headers=self.other).json()['prescription'])
        bad=copy.deepcopy(body);bad['items'][0]['target_deg']=999
        self.assertEqual(self.c.post(path,headers=self.th,json=bad).status_code,422)
        bad=copy.deepcopy(body);bad['items'].append(bad['items'][0])
        self.assertEqual(self.c.post(path,headers=self.th,json=bad).status_code,422)
        with closing(db.connect()) as con,con:
            tid=con.execute('SELECT therapist_id FROM patients WHERE id=?',(self.pid,)).fetchone()[0]
            con.execute('UPDATE patients SET therapist_id=NULL WHERE id=?',(self.pid,))
        self.assertIsNone(self.c.get('/api/v1/me/visual-prescription',headers=self.ph).json()['prescription'])
        self.assertEqual(self.c.get(path,headers=self.th).status_code,403)
        with closing(db.connect()) as con,con:con.execute('UPDATE patients SET therapist_id=? WHERE id=?',(tid,self.pid))




    def test_slr_surface_rule_version_roundtrip(self):
        body={'status':'published','title':'动作2候选','side':'left','phase':'测试','days_per_week':1,
              'items':[{'exercise_id':'supine','rule_version':'slr_v0.1_surface','sets':1,'reps':3,'target_deg':30,'hold_s':5,'return_s':1,'rest_s':30}]}
        r=self.c.post(f'/api/v1/patients/{self.pid}/visual-prescription',headers=self.th,json=body)
        self.assertEqual(r.status_code,200,r.text)
        actual=self.c.get('/api/v1/me/visual-prescription',headers=self.ph).json()['prescription']
        self.assertEqual(actual['items'][0]['rule_version'],'slr_v0.1_surface')
        self.assertEqual(actual['items'][0]['hold_s'],5)


    def test_sts_rule_version_roundtrip(self):
        body={'status':'published','title':'坐站候选','side':'left','phase':'测试','days_per_week':1,
              'items':[{'exercise_id':'stand','rule_version':'sts_v0.1_dual_baseline','sets':1,'reps':3,'target_deg':165,'hold_s':1,'return_s':1,'rest_s':30}]}
        r=self.c.post(f'/api/v1/patients/{self.pid}/visual-prescription',headers=self.th,json=body)
        self.assertEqual(r.status_code,200,r.text)
        actual=self.c.get('/api/v1/me/visual-prescription',headers=self.ph).json()['prescription']
        self.assertEqual(actual['items'][0]['rule_version'],'sts_v0.1_dual_baseline')
        self.assertEqual(actual['items'][0]['hold_s'],1)

    def test_squat_joint_rule_version_roundtrip(self):
        body={'status':'published','title':'微蹲候选','side':'left','phase':'测试','days_per_week':1,
              'items':[{'exercise_id':'squat','rule_version':'squat_v0.1_joint','sets':1,'reps':3,'target_deg':30,'hold_s':1,'return_s':1,'rest_s':30}]}
        r=self.c.post(f'/api/v1/patients/{self.pid}/visual-prescription',headers=self.th,json=body)
        self.assertEqual(r.status_code,200,r.text)
        actual=self.c.get('/api/v1/me/visual-prescription',headers=self.ph).json()['prescription']
        self.assertEqual(actual['items'][0]['rule_version'],'squat_v0.1_joint')
        self.assertEqual(actual['items'][0]['target_deg'],30)
        self.assertEqual(actual['items'][0]['hold_s'],1)

if __name__=='__main__':unittest.main(defaultTest='PlanTests')
