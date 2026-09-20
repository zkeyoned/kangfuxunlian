import json
from typing import Literal
from fastapi import Depends,HTTPException
from pydantic import BaseModel,ConfigDict,Field,model_validator
import db

class Selection(BaseModel):
    model_config=ConfigDict(extra='forbid')
    condition:Literal['knee_osteoarthritis']|None
    exercise_ids:list[Literal['seated','supine','squat','stand']]=Field(max_length=4)
    @model_validator(mode='after')
    def consistent(self):
        if bool(self.condition)!=bool(self.exercise_ids):raise ValueError('请选择膝骨关节炎和至少一个动作；清空时两项同时清空')
        if len(set(self.exercise_ids))!=len(self.exercise_ids):raise ValueError('动作不能重复')
        return self

def install_routes(app,get_con,current_user):
    def patient(u):
        if u['role']!='patient' or not u.get('patient_id'):raise HTTPException(403,'仅患者可设置本人训练方向')
        return u['patient_id']
    @app.get('/api/v1/me/training-selection')
    def read(u=Depends(current_user),con=Depends(get_con)):
        row=con.execute('SELECT * FROM patient_training_selection WHERE patient_id=?',(patient(u),)).fetchone()
        return {'selection':{'condition':row['condition'],'exercise_ids':json.loads(row['exercise_ids_json']),'updated_at':row['updated_at']} if row else None}
    @app.put('/api/v1/me/training-selection')
    def save(body:Selection,u=Depends(current_user),con=Depends(get_con)):
        pid=patient(u)
        with con:
            con.execute('INSERT INTO patient_training_selection VALUES(?,?,?,?) ON CONFLICT(patient_id) DO UPDATE SET condition=excluded.condition,exercise_ids_json=excluded.exercise_ids_json,updated_at=excluded.updated_at',(pid,body.condition,json.dumps(body.exercise_ids),db.now()))
            con.execute('INSERT INTO audit_logs(user_id,action,target) VALUES(?,?,?)',(u['id'],'training_selection.save',f'patient:{pid}'))
        return read(u,con)
