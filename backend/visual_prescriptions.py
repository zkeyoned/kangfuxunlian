import json
from typing import Literal
from fastapi import Depends, HTTPException
from pydantic import BaseModel, Field, ConfigDict, model_validator
import db
from plan_parameters import validate_targets

class Item(BaseModel):
    model_config=ConfigDict(extra='forbid')
    exercise_id:Literal['seated','supine','squat','stand']
    rule_version:Literal['slr_v0.1_surface','sts_v0.1_dual_baseline']|None=None
    sets:int=Field(ge=1,le=20,strict=True)
    reps:int=Field(ge=1,le=100,strict=True)
    target_deg:float
    hold_s:float
    return_s:float
    rest_s:float
    @model_validator(mode='after')
    def targets(self):
        validate_targets(self.exercise_id,{k:getattr(self,k) for k in ('target_deg','hold_s','return_s','rest_s')})
        return self

class Prescription(BaseModel):
    model_config=ConfigDict(extra='forbid')
    status:Literal['draft','published']
    title:str=Field(min_length=1,max_length=100)
    side:Literal['left','right']
    phase:str=Field(max_length=100)
    days_per_week:int=Field(ge=1,le=7,strict=True)
    daily_sessions:int=Field(default=1,ge=1,le=10,strict=True)
    duration_weeks:int=Field(default=2,ge=1,le=52,strict=True)
    pain_pause_score:int=Field(default=5,ge=0,le=10,strict=True)
    notes:str=Field(default='',max_length=2000)
    items:list[Item]=Field(min_length=1,max_length=4)
    @model_validator(mode='after')
    def unique(self):
        if len({i.exercise_id for i in self.items})!=len(self.items):raise ValueError('动作不能重复')
        return self

def pack(row):
    return {**json.loads(row['body_json']),'id':row['id'],'created_at':row['created_at']} if row else None

def install_routes(app,get_con,current_user,patient_in_scope):
    def therapist(con,u,pid):
        if u['role']!='therapist':raise HTTPException(403,'仅关联康复师可编辑方案')
        patient_in_scope(con,u,pid)

    @app.get('/api/v1/patients/{pid}/visual-prescription')
    def read(pid:int,u=Depends(current_user),con=Depends(get_con)):
        therapist(con,u,pid)
        return {s:pack(con.execute('SELECT * FROM visual_prescriptions WHERE patient_id=? AND therapist_id=? AND status=? ORDER BY id DESC LIMIT 1',(pid,u['id'],s)).fetchone()) for s in ('draft','published')}

    @app.post('/api/v1/patients/{pid}/visual-prescription')
    def save(pid:int,body:Prescription,u=Depends(current_user),con=Depends(get_con)):
        with con:
            con.execute('BEGIN IMMEDIATE');therapist(con,u,pid)
            cur=con.execute('INSERT INTO visual_prescriptions(patient_id,therapist_id,status,body_json,created_at) VALUES(?,?,?,?,?)',(pid,u['id'],body.status,body.model_dump_json(),db.now()))
            con.execute('INSERT INTO audit_logs(user_id,action,target) VALUES(?,?,?)',(u['id'],'visual_plan.'+body.status,'visual_prescription:'+str(cur.lastrowid)))
            if body.status=='published':con.execute("DELETE FROM visual_prescriptions WHERE patient_id=? AND therapist_id=? AND status='draft'",(pid,u['id']))
        return pack(con.execute('SELECT * FROM visual_prescriptions WHERE id=?',(cur.lastrowid,)).fetchone())

    @app.get('/api/v1/me/visual-prescription')
    def mine(u=Depends(current_user),con=Depends(get_con)):
        if u['role']!='patient':raise HTTPException(403,'仅患者可读取本人方案')
        row=con.execute("SELECT v.* FROM visual_prescriptions v JOIN patients p ON p.id=v.patient_id AND p.therapist_id=v.therapist_id WHERE p.user_id=? AND v.status='published' ORDER BY v.id DESC LIMIT 1",(u['id'],)).fetchone()
        return {'prescription':pack(row)}
