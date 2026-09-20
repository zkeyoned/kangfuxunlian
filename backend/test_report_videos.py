import hashlib,unittest
from contextlib import closing
from test_training_reports import ReportTests,payload
import db
from report_videos import CHUNK

class VideoTests(ReportTests):
    def test_video_chunk_roundtrip_and_permissions(self):
        report=self.c.post('/api/v1/training-reports',headers=self.ph,json=payload('video-test-001')).json()
        rid=report['id'];base=f'/api/v1/training-reports/{rid}/video'
        # Container-shaped binary checks transport integrity, not decoder quality.
        data=b'\x1a\x45\xdf\xa3'+bytes(CHUNK+35)
        body={'mime':'video/webm','size':len(data),'sha256':hashlib.sha256(data).hexdigest(),'duration_s':8.2,'preview_flipped':True}
        self.assertEqual(self.c.post(base,headers=self.th,json=body).status_code,403)
        self.assertEqual(self.c.post(base,headers=self.other,json=body).status_code,403)
        self.assertEqual(self.c.post(base,headers=self.ph,json=body).json()['chunk_count'],2)
        self.assertEqual(self.c.post(base+'/complete',headers=self.ph).status_code,409)
        self.assertEqual(self.c.put(base+'/chunks/0',headers=self.ph,content=b'short').status_code,400)
        for i in range(2):
            r=self.c.put(base+f'/chunks/{i}',headers=self.ph,content=data[i*CHUNK:(i+1)*CHUNK]);self.assertEqual(r.status_code,200,r.text)
        self.assertEqual(self.c.get(base+'/chunks/0',headers=self.th).status_code,404)
        self.assertEqual(self.c.post(base+'/complete',headers=self.ph).json()['state'],'ready')
        self.assertEqual(self.c.post(base,headers=self.ph,json=body).json()['state'],'ready')
        self.assertEqual(self.c.put(base+'/chunks/0',headers=self.ph,content=data[:CHUNK]).status_code,200)
        self.assertEqual(self.c.put(base+'/chunks/0',headers=self.ph,content=bytes(CHUNK)).status_code,409)
        recovered=b''.join(self.c.get(base+f'/chunks/{i}',headers=self.th).content for i in range(2))
        self.assertEqual(recovered,data)
        self.assertEqual(self.c.get(base+'/chunks/0').status_code,401)
        self.assertEqual(self.c.get(base+'/chunks/0',headers=self.other).status_code,403)
        rows=self.c.get(f'/api/v1/training-reports?patient_id={self.pid}',headers=self.th).json()['reports']
        self.assertTrue(all(r['patient_id']==self.pid for r in rows));self.assertEqual(next(r for r in rows if r['id']==rid)['video']['state'],'ready')
        self.assertEqual(self.c.get(f'/api/v1/training-reports?patient_id={self.pid}',headers=self.other).status_code,403)
        with closing(db.connect()) as con,con:
            tid=con.execute('SELECT therapist_id FROM patients WHERE id=?',(self.pid,)).fetchone()[0];con.execute('UPDATE patients SET therapist_id=NULL WHERE id=?',(self.pid,))
        self.assertEqual(self.c.get(base+'/chunks/0',headers=self.th).status_code,403)
        with closing(db.connect()) as con,con:con.execute('UPDATE patients SET therapist_id=? WHERE id=?',(tid,self.pid))

if __name__=='__main__':unittest.main(defaultTest='VideoTests')
