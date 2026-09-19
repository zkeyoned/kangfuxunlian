import os,tempfile,unittest,copy,logging
from contextlib import closing
_tmp=tempfile.TemporaryDirectory()
os.environ['REHAB_DATA_DIR']=_tmp.name
import db
from main import app
from fastapi.testclient import TestClient


def payload(client='session-test-001'):
    return {'client_id':client,'exercise_id':'seated','result':{
        'brief_report':{'version':'1.0','exercise':'坐姿伸膝','side':'左腿','completed_reps':1,'target_reps':10,'interrupted_attempts':0,
          'scope':'训练辅助，非医疗诊断','sets':[{'set':1,'status':'记录未完成','completed_reps':1,'target_reps':10,'angle_hold_met_reps':0,'needs_review_reps':1,'problems':[],'finding':'数据需复核'}],'suggestions':['请调整取景']},
        'repetitions':[{'needs_review':True,'knee_peak_deg':None}],
        'feedback_events':[{'code':'TRUNK_FORWARD','timestamp_s':4.5,'training_set':1,'message':'前倾超过设置范围'}],
        'training_session':{'plan':{'hold_s':3},'quality':{'frames':50,'observed_frames':40}}}}


class ReportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        db.init_db();cls.c=TestClient(app)
        cls.ph=cls.login('p.zhang','zhang123');cls.th=cls.login('dr.lin','lin123')
        cls.pid=cls.c.get('/api/v1/auth/me',headers=cls.ph).json()['patient_id']
        cls.c.post('/api/v1/auth/register',json={'username':'reports@example.test','password':'test-only-123','display_name':'报告测试'})
        cls.other=cls.login('reports@example.test','test-only-123')

    @classmethod
    def login(cls,u,p):
        r=cls.c.post('/api/v1/auth/login',json={'username':u,'password':p})
        if r.status_code==403 and r.json().get('code')=='PASSWORD_RESET_REQUIRED':
            cls.c.post('/api/v1/auth/change-password',json={'username':u,'old_password':p,'new_password':p+'2026'})
            r=cls.c.post('/api/v1/auth/login',json={'username':u,'password':p+'2026'})
        return {'Authorization':'Bearer '+r.json()['token']}

    @classmethod
    def tearDownClass(cls):cls.c.close();logging.shutdown()

    def test_roundtrip_idempotence_scope_and_read(self):
        body=payload();r=self.c.post('/api/v1/training-reports',headers=self.ph,json=body)
        self.assertEqual(r.status_code,200,r.text);rid=r.json()['id']
        self.assertEqual(r.json()['delivery']['status'],'available')
        again=self.c.post('/api/v1/training-reports',headers=self.ph,json=body)
        self.assertEqual(again.json()['id'],rid)
        body['result']['training_session']['plan']['hold_s']=5
        self.assertEqual(self.c.post('/api/v1/training-reports',headers=self.ph,json=body).status_code,409)
        path=f'/api/v1/training-reports/{rid}'
        self.assertEqual(self.c.get(path).status_code,401)
        self.assertEqual(self.c.get(path,headers=self.other).status_code,403)
        actual=self.c.get(path,headers=self.th).json()
        self.assertIsNone(actual['result']['repetitions'][0]['knee_peak_deg'])
        self.assertEqual(actual['result']['feedback_events'][0]['timestamp_s'],4.5)
        self.assertIsNone(actual['read_at'])
        self.assertEqual(self.c.post(path+'/read',headers=self.ph).status_code,403)
        self.assertIsNotNone(self.c.post(path+'/read',headers=self.th).json()['read_at'])
        self.assertTrue(any(r['id']==rid for r in self.c.get('/api/v1/training-reports',headers=self.th).json()['reports']))
        with closing(db.connect()) as con,con:
            tid=con.execute('SELECT therapist_id FROM patients WHERE id=?',(self.pid,)).fetchone()[0]
            con.execute('UPDATE patients SET therapist_id=NULL WHERE id=?',(self.pid,))
        self.assertEqual(self.c.get(path,headers=self.th).status_code,403)
        self.assertEqual(self.c.post(path+'/read',headers=self.th).status_code,403)
        self.assertFalse(any(r['id']==rid for r in self.c.get('/api/v1/training-reports',headers=self.th).json()['reports']))
        with closing(db.connect()) as con,con:con.execute('UPDATE patients SET therapist_id=? WHERE id=?',(tid,self.pid))

    def test_unlinked_zero_and_validation(self):
        p=payload('unlinked-zero');b=p['result']['brief_report'];b['completed_reps']=0;b['sets'][0]['completed_reps']=0;b['sets'][0]['needs_review_reps']=0;p['result']['repetitions']=[]
        r=self.c.post('/api/v1/training-reports',headers=self.other,json=p)
        self.assertEqual(r.status_code,200,r.text);self.assertEqual(r.json()['delivery']['status'],'unlinked')
        self.assertEqual(r.json()['result']['brief_report']['completed_reps'],0)
        self.assertEqual(self.c.post('/api/v1/training-reports',headers=self.th,json=p).status_code,403)
        for field,value in [('keypoints',[]),('video','fake')]:
            bad=copy.deepcopy(p);bad['result']['training_session'][field]=value
            self.assertEqual(self.c.post('/api/v1/training-reports',headers=self.other,json=bad).status_code,400)
        bad=copy.deepcopy(p);bad['result']['brief_report']['completed_reps']=9
        self.assertEqual(self.c.post('/api/v1/training-reports',headers=self.other,json=bad).status_code,400)
        # Link later: saved reports become visible without uploading again.
        uid=self.c.get('/api/v1/auth/me',headers=self.th).json()['id']
        req=self.c.post('/api/v1/care/requests',headers=self.other,json={'user_id':uid}).json()['id']
        self.c.post(f'/api/v1/care/requests/{req}/respond',headers=self.th,json={'action':'accept'})
        self.assertEqual(self.c.get(f"/api/v1/training-reports/{r.json()['id']}",headers=self.th).status_code,200)

if __name__=='__main__':unittest.main()
