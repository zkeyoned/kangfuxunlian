import os,tempfile,unittest
_tmp=tempfile.TemporaryDirectory();os.environ['REHAB_DATA_DIR']=_tmp.name
import db
from main import app
from fastapi.testclient import TestClient

class SelectionTests(unittest.TestCase):
    def test_empty_isolation_validation_and_clear(self):
        db.init_db();c=TestClient(app);headers=[]
        for name in ['first','second']:
            body={'username':name+'@example.test','password':'Test12345','display_name':name}
            self.assertEqual(c.post('/api/v1/auth/register',json=body).status_code,201)
            headers.append({'Authorization':'Bearer '+c.post('/api/v1/auth/login',json=body).json()['token']})
        path='/api/v1/me/training-selection';a,b=headers
        self.assertIsNone(c.get(path,headers=a).json()['selection'])
        self.assertIsNone(c.get('/api/v1/me/visual-prescription',headers=a).json()['prescription'])
        body={'condition':'knee_osteoarthritis','exercise_ids':['seated','supine']}
        self.assertEqual(c.put(path,json=body,headers=a).status_code,200)
        self.assertEqual(c.get(path,headers=a).json()['selection']['exercise_ids'],['seated','supine'])
        self.assertIsNone(c.get(path,headers=b).json()['selection'])
        self.assertEqual(c.get(path).status_code,401)
        for bad in [dict(body,patient_id=1),dict(body,condition='other'),dict(body,exercise_ids=['seated','seated']),dict(body,exercise_ids=[])]:
            self.assertEqual(c.put(path,headers=a,json=bad).status_code,422)
        self.assertEqual(c.put(path,headers=a,json={'condition':None,'exercise_ids':[]}).status_code,200)
        self.assertEqual(c.get(path,headers=a).json()['selection']['exercise_ids'],[])
        self.assertIsNone(c.get('/api/v1/me/visual-prescription',headers=a).json()['prescription'])
        c.close()

if __name__=='__main__':unittest.main()
