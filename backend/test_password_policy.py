import os,tempfile,unittest
from contextlib import closing
_tmp=tempfile.TemporaryDirectory();os.environ['REHAB_DATA_DIR']=_tmp.name
import db
from main import app
from fastapi.testclient import TestClient

class PasswordTests(unittest.TestCase):
    def test_policy_and_authenticated_change(self):
        db.init_db();c=TestClient(app)
        for pw in ['abcdefghi','123456789','abc1234','abcdefghijklm123','abc1234567890123']:
            r=c.post('/api/v1/auth/register',json={'username':'policy@example.test','display_name':'测试','password':pw})
            self.assertEqual(r.status_code,422,(pw,r.text))
        self.assertEqual(c.post('/api/v1/auth/register',json={'username':'policy@example.test','display_name':'测试','password':'Abcd1234'}).status_code,201)
        r=c.post('/api/v1/auth/login',json={'username':'dr.lin','password':'lin123'})
        self.assertEqual(r.status_code,403);self.assertEqual(r.json()['code'],'PASSWORD_RESET_REQUIRED');self.assertNotIn('token',r.json())
        self.assertEqual(c.post('/api/v1/auth/login',json={'username':'dr.lin','password':'wrong'}).status_code,401)
        with closing(db.connect()) as con:
            uid=con.execute("SELECT id FROM users WHERE username='dr.lin'").fetchone()[0]
            old_token=db.issue_token(con,uid)
        data={'username':'dr.lin','old_password':'wrong','new_password':'Newpass123'}
        self.assertEqual(c.post('/api/v1/auth/change-password',json=data).status_code,401)
        data['old_password']='lin123';data['new_password']='12345678'
        self.assertEqual(c.post('/api/v1/auth/change-password',json=data).status_code,422)
        data['new_password']='Newpass123'
        self.assertEqual(c.post('/api/v1/auth/change-password',json=data).status_code,200)
        self.assertEqual(c.get('/api/v1/auth/me',headers={'Authorization':'Bearer '+old_token}).status_code,401)
        self.assertEqual(c.post('/api/v1/auth/login',json={'username':'dr.lin','password':'lin123'}).status_code,401)
        r=c.post('/api/v1/auth/login',json={'username':'dr.lin','password':'Newpass123'});self.assertEqual(r.status_code,200)
        self.assertEqual(c.post('/api/v1/patients',headers={'Authorization':'Bearer '+r.json()['token']},json={'username':'invalid','password':'abc','display_name':'测试'}).status_code,422)
        c.close()

if __name__=='__main__':unittest.main()
