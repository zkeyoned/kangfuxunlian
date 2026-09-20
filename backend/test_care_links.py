"""在临时库验证邀请、双方权限、撤销和跨机构访问。"""
import os
import tempfile
import unittest
import logging
from contextlib import closing

_temp=tempfile.TemporaryDirectory()
os.environ['REHAB_DATA_DIR']=_temp.name
import db
from main import app
from fastapi.testclient import TestClient


class CareTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        db.init_db()
        cls.c=TestClient(app)
        cls.th=cls.login('dr.lin','lin123')
        with closing(db.connect()) as con, con:
            inst=con.execute("SELECT institution_id FROM users WHERE username='dr.lin'").fetchone()[0]
            con.execute('INSERT INTO users(institution_id,role,username,password_hash,display_name) VALUES(?,?,?,?,?)',
                        (inst,'therapist','other.therapist',db.hash_password('test-only-123'),'测试康复师'))
        cls.other=cls.login('other.therapist','test-only-123')

    @classmethod
    def login(cls,name,password):
        r=cls.c.post('/api/v1/auth/login',json={'username':name,'password':password})
        if r.status_code==403 and r.json().get('code')=='PASSWORD_RESET_REQUIRED':
            cls.c.post('/api/v1/auth/change-password',json={'username':name,'old_password':password,'new_password':password+'2026'})
            r=cls.c.post('/api/v1/auth/login',json={'username':name,'password':password+'2026'})
        assert r.status_code==200,r.text
        return {'Authorization':'Bearer '+r.json()['token']}

    @classmethod
    def tearDownClass(cls):
        cls.c.close()
        logging.shutdown()

    def patient(self,name):
        r=self.c.post('/api/v1/auth/register',json={'username':name+'@example.test','password':'test-only-123','display_name':'测试患者'})
        self.assertEqual(r.status_code,201,r.text)
        h=self.login(name+'@example.test','test-only-123')
        return h,self.c.get('/api/v1/auth/me',headers=h).json()

    def test_patient_initiates_and_unlinks(self):
        h,p=self.patient('patientfirst')
        uid=self.c.post('/api/v1/care/search',headers=h,json={'account':'dr.lin'}).json()['users'][0]['id']
        pid=p['patient_id']
        self.assertEqual(self.c.get(f'/api/v1/patients/{pid}',headers=self.th).status_code,403)
        r=self.c.post('/api/v1/care/requests',headers=h,json={'user_id':uid})
        self.assertEqual(r.status_code,201,r.text);rid=r.json()['id']
        self.assertEqual(self.c.post('/api/v1/care/requests',headers=self.th,json={'user_id':p['id']}).status_code,409)
        self.assertEqual(self.c.post(f'/api/v1/care/requests/{rid}/respond',headers=h,json={'action':'accept'}).status_code,403)
        self.assertEqual(self.c.post(f'/api/v1/care/requests/{rid}/respond',headers=self.other,json={'action':'accept'}).status_code,404)
        self.assertEqual(self.c.post(f'/api/v1/care/requests/{rid}/respond',headers=self.th,json={'action':'accept'}).status_code,200)
        self.assertEqual(self.c.get(f'/api/v1/patients/{pid}',headers=self.th).status_code,200)
        self.assertEqual(self.c.get(f'/api/v1/patients/{pid}',headers=self.other).status_code,403)
        self.assertIn(pid,[x['id'] for x in self.c.get('/api/v1/patients',headers=self.th).json()])
        self.assertEqual(self.c.get('/api/v1/patients',headers=self.other).json(),[])
        self.assertEqual(self.c.get('/api/v1/stats',headers=self.other).json()['patients'],0)
        self.assertEqual(self.c.get('/api/v1/alerts',headers=self.other).json(),[])
        self.assertEqual(self.c.get('/api/v1/care/connections',headers=h).json()['connections'][0]['therapist_user_id'],uid)
        with closing(db.connect()) as con, con:
            con.execute("INSERT INTO plans(patient_id,therapist_id,title,start_date) VALUES(?,?,?,?)",(pid,uid,'测试计划','2026-01-01'))
        self.assertEqual(self.c.delete(f'/api/v1/care/connections/{pid}',headers=self.other).status_code,404)
        self.assertEqual(self.c.delete(f'/api/v1/care/connections/{pid}',headers=h).status_code,200)
        for endpoint in (f'/patients/{pid}',f'/patients/{pid}/sessions',f'/patients/{pid}/export.csv'):
            self.assertEqual(self.c.get('/api/v1'+endpoint,headers=self.th).status_code,403)
        with closing(db.connect()) as con, con:
            self.assertEqual(con.execute('SELECT status FROM plans WHERE patient_id=?',(pid,)).fetchone()[0],'paused')

    def test_therapist_initiates_reject_cancel_accept(self):
        h,p=self.patient('therapistfirst')
        found=self.c.post('/api/v1/care/search',headers=self.th,json={'account':'THERAPISTFIRST@EXAMPLE.TEST'}).json()['users']
        self.assertEqual(found,[{'id':p['id'],'display_name':'测试患者','role':'patient'}])
        self.assertEqual(self.c.post('/api/v1/care/search',headers=self.th,json={'account':'therapistfirst'}).json()['users'],[])
        for action in ('reject','cancel','accept'):
            r=self.c.post('/api/v1/care/requests',headers=self.th,json={'user_id':p['id']});self.assertEqual(r.status_code,201)
            rid=r.json()['id']
            self.assertEqual(self.c.post(f'/api/v1/care/requests/{rid}/respond',headers=self.th if action=='cancel' else h,json={'action':action}).status_code,200)
        self.assertEqual(len(self.c.get('/api/v1/care/connections',headers=h).json()['connections']),1)
        self.assertEqual(self.c.post('/api/v1/care/requests',headers=self.other,json={'user_id':p['id']}).status_code,409)

    def test_phone_and_auth_required(self):
        r=self.c.post('/api/v1/auth/register',json={'username':'13900000000','password':'test-only-123','display_name':'虚构号码测试'})
        self.assertEqual(r.status_code,201)
        self.assertEqual(len(self.c.post('/api/v1/care/search',headers=self.th,json={'account':'13900000000'}).json()['users']),1)
        self.assertEqual(self.c.post('/api/v1/care/search',json={'account':'13900000000'}).status_code,401)


if __name__=='__main__':unittest.main()
