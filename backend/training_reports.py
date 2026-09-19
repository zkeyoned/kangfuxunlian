"""Persist actual visual summaries without applying the legacy scoring scheme."""
import json
from typing import Literal
from fastapi import Depends, HTTPException, Query
from pydantic import BaseModel, Field
import db


class ReportInput(BaseModel):
    client_id: str = Field(min_length=8, max_length=100, pattern=r'^[A-Za-z0-9_-]+$')
    exercise_id: Literal['seated','supine','squat','stand']
    result: dict


def validate_result(result):
    allowed={'brief_report','repetitions','feedback_events','training_session'}
    if set(result)-allowed:
        raise HTTPException(400,'报告只能包含简报和动作指标')
    try:
        encoded=json.dumps(result,ensure_ascii=False,allow_nan=False,sort_keys=True,separators=(',',':'))
    except (ValueError,TypeError,RecursionError):
        raise HTTPException(400,'报告含无效数值或结构')
    if len(encoded.encode('utf8'))>2_000_000:
        raise HTTPException(413,'报告过大')
    def check(node,depth=0):
        if depth>15:raise HTTPException(400,'报告结构过深')
        if isinstance(node,dict):
            if set(node)&{'keypoints','landmarks','video','image','frames_jsonl'} or ('frames' in node and type(node['frames']) is not int):
                raise HTTPException(400,'不接收录像或原始关键点')
            for value in node.values():check(value,depth+1)
        elif isinstance(node,list):
            for value in node:check(value,depth+1)
    check(result)
    b=result.get('brief_report',{})
    def number(v):return type(v) is int and 0<=v<=100000
    if not isinstance(b,dict) or not isinstance(b.get('version'),str):raise HTTPException(400,'缺少有效简报')
    if not all(isinstance(b.get(k),str) for k in ('exercise','side','scope')):raise HTTPException(400,'简报文字字段不完整')
    if not all(number(b.get(k)) for k in ('completed_reps','target_reps','interrupted_attempts')):raise HTTPException(400,'简报次数无效')
    groups=b.get('sets')
    if not isinstance(groups,list) or not 1<=len(groups)<=20:raise HTTPException(400,'简报组数无效')
    for g in groups:
        if not isinstance(g,dict) or not all(number(g.get(k)) for k in ('set','completed_reps','target_reps','angle_hold_met_reps','needs_review_reps')):
            raise HTTPException(400,'组级次数无效')
        if not all(isinstance(g.get(k),str) for k in ('status','finding')) or not isinstance(g.get('problems'),list):raise HTTPException(400,'组级结构无效')
    if sum(g['completed_reps'] for g in groups)!=b['completed_reps'] or sum(g['target_reps'] for g in groups)!=b['target_reps']:
        raise HTTPException(400,'汇总次数与分组不一致')
    if not isinstance(b.get('suggestions'),list) or not all(isinstance(s,str) for s in b['suggestions']):raise HTTPException(400,'建议格式无效')
    for k in ('repetitions','feedback_events'):
        if not isinstance(result.get(k),list) or not all(isinstance(r,dict) for r in result[k]):raise HTTPException(400,'动作记录格式无效')
    if len(result['repetitions'])!=b['completed_reps']:raise HTTPException(400,'动作记录数量不一致')
    if not isinstance(result.get('training_session'),dict):raise HTTPException(400,'缺少训练计划快照')
    return encoded


def install_routes(app,get_con,current_user,patient_in_scope):
    def pack(con,row,full=False):
        p=db.one(con.execute('SELECT p.therapist_id,u.display_name FROM patients p JOIN users u ON u.id=p.user_id WHERE p.id=?',(row['patient_id'],)))
        t=db.one(con.execute('SELECT display_name FROM users WHERE id=? AND is_active=1',(p['therapist_id'],)))
        result=json.loads(row['result_json'])
        read=row['read_at'] if row['read_by']==p['therapist_id'] else None
        delivery={'status':'available' if t else 'unlinked','therapist_name':t['display_name'] if t else None,'read_at':read}
        out={k:row[k] for k in ('id','client_id','patient_id','exercise_id','created_at')}
        out.update(patient_name=p['display_name'],brief_report=result['brief_report'],delivery=delivery,read_at=read)
        if full:out['result']=result
        return out

    def accessible(con,user,rid):
        row=db.one(con.execute('SELECT * FROM training_reports WHERE id=?',(rid,)))
        if not row:raise HTTPException(404,'报告不存在')
        patient_in_scope(con,user,row['patient_id'])
        return row

    @app.post('/api/v1/training-reports')
    def save(body:ReportInput,user=Depends(current_user),con=Depends(get_con)):
        if user['role']!='patient' or not user.get('patient_id'):raise HTTPException(403,'仅患者可保存自己的训练报告')
        encoded=validate_result(body.result)
        with con:
            con.execute('BEGIN IMMEDIATE')
            old=db.one(con.execute('SELECT * FROM training_reports WHERE patient_id=? AND client_id=?',(user['patient_id'],body.client_id)))
            if old:
                if old['result_json']!=encoded or old['exercise_id']!=body.exercise_id:raise HTTPException(409,'本次训练已保存，内容不同，未覆盖原记录')
                return pack(con,old,True)
            rid=con.execute('INSERT INTO training_reports(patient_id,client_id,exercise_id,result_json,created_at) VALUES(?,?,?,?,?)',
                (user['patient_id'],body.client_id,body.exercise_id,encoded,db.now())).lastrowid
            con.execute('INSERT INTO audit_logs(user_id,action,target,detail_json) VALUES(?,?,?,?)',(user['id'],'training_report.save',f'training_report:{rid}','{}'))
            return pack(con,db.one(con.execute('SELECT * FROM training_reports WHERE id=?',(rid,))),True)

    @app.get('/api/v1/training-reports')
    def listing(limit:int=Query(50,ge=1,le=100),user=Depends(current_user),con=Depends(get_con)):
        if user['role']=='patient':scope,value='p.user_id',user['id']
        elif user['role']=='therapist':scope,value='p.therapist_id',user['id']
        elif user['role']=='admin':scope,value='p.institution_id',user['institution_id']
        else:raise HTTPException(403,'无权读取报告')
        rows=[dict(r) for r in con.execute(f'SELECT r.* FROM training_reports r JOIN patients p ON p.id=r.patient_id WHERE {scope}=? ORDER BY r.id DESC LIMIT ?',(value,limit))]
        return {'reports':[pack(con,row) for row in rows]}

    @app.get('/api/v1/training-reports/{rid}')
    def detail(rid:int,user=Depends(current_user),con=Depends(get_con)):
        return pack(con,accessible(con,user,rid),True)

    @app.post('/api/v1/training-reports/{rid}/read')
    def read(rid:int,user=Depends(current_user),con=Depends(get_con)):
        row=accessible(con,user,rid)
        if user['role']!='therapist':raise HTTPException(403,'仅康复师可以标记查看')
        with con:
            con.execute('UPDATE training_reports SET read_by=?,read_at=? WHERE id=?',(user['id'],db.now(),rid))
        return pack(con,db.one(con.execute('SELECT * FROM training_reports WHERE id=?',(rid,))))
