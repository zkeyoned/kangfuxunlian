"""患者与康复师双向邀请。明确接受前不授予患者档案访问权。"""
from fastapi import Depends, HTTPException
from pydantic import BaseModel, Field
import db


class SearchIn(BaseModel):
    account: str = Field(min_length=1, max_length=254)


class InviteIn(BaseModel):
    user_id: int


class DecisionIn(BaseModel):
    action: str


def install_routes(app, get_con, current_user):
    def member(user=Depends(current_user)):
        if user['role'] not in ('patient', 'therapist'):
            raise HTTPException(403, '仅患者和康复师可使用关联功能')
        return user

    def audit(con, uid, action, target):
        con.execute('INSERT INTO audit_logs(user_id,action,target) VALUES(?,?,?)', (uid, action, target))

    @app.post('/api/v1/care/search')
    def search(body: SearchIn, user=Depends(member), con=Depends(get_con)):
        account = body.account.strip()
        if '@' in account:
            account = account.lower()
        opposite = 'therapist' if user['role'] == 'patient' else 'patient'
        found = db.one(con.execute('SELECT id,display_name,role FROM users WHERE username=? AND role=? AND is_active=1', (account, opposite)))
        # No list or fuzzy search. Return no clinical data or other contacts.
        return {'users': [found] if found else []}

    @app.get('/api/v1/care/connections')
    def connections(user=Depends(member), con=Depends(get_con)):
        field = 'p.user_id' if user['role'] == 'patient' else 'p.therapist_id'
        rows = db.rows(con.execute(
            'SELECT p.id AS patient_id,u.id AS patient_user_id,u.display_name AS patient_name,'
            't.id AS therapist_user_id,t.display_name AS therapist_name FROM patients p '
            'JOIN users u ON u.id=p.user_id JOIN users t ON t.id=p.therapist_id '
            f'WHERE {field}=?', (user['id'],)))
        requests = db.rows(con.execute(
            'SELECT r.*,s.display_name AS sender_name,v.display_name AS recipient_name '
            'FROM care_requests r JOIN users s ON s.id=r.sender_id JOIN users v ON v.id=r.recipient_id '
            "WHERE (sender_id=? OR recipient_id=?) AND status='pending' ORDER BY r.id DESC", (user['id'],user['id'])))
        return {'connections': rows, 'requests': requests}

    @app.post('/api/v1/care/requests', status_code=201)
    def invite(body: InviteIn, user=Depends(member), con=Depends(get_con)):
        with con:
            con.execute('BEGIN IMMEDIATE')
            target = db.one(con.execute('SELECT * FROM users WHERE id=? AND is_active=1', (body.user_id,)))
            if not target or {target['role'], user['role']} != {'patient','therapist'}:
                raise HTTPException(400, '请选择另一身份的有效账号')
            puid = user['id'] if user['role']=='patient' else target['id']
            tid = target['id'] if target['role']=='therapist' else user['id']
            p = db.one(con.execute('SELECT * FROM patients WHERE user_id=?', (puid,)))
            if not p:
                raise HTTPException(400, '患者档案不存在')
            if p['therapist_id'] is not None:
                raise HTTPException(409, '患者已有主责康复师，请先解除原关联')
            existing = db.one(con.execute("SELECT id FROM care_requests WHERE patient_id=? AND therapist_id=? AND status='pending'",(p['id'],tid)))
            if existing:
                raise HTTPException(409, '双方已有待处理申请，请在申请列表接受或等待对方处理')
            rid = con.execute('INSERT INTO care_requests(sender_id,recipient_id,patient_id,therapist_id) VALUES(?,?,?,?)',
                              (user['id'],target['id'],p['id'],tid)).lastrowid
            audit(con,user['id'],'care.request',f'care_request:{rid}')
        return {'id':rid,'status':'pending'}

    @app.post('/api/v1/care/requests/{rid}/respond')
    def respond(rid: int, body: DecisionIn, user=Depends(member), con=Depends(get_con)):
        if body.action not in ('accept','reject','cancel'):
            raise HTTPException(400,'不支持的操作')
        with con:
            con.execute('BEGIN IMMEDIATE')
            row=db.one(con.execute('SELECT * FROM care_requests WHERE id=?',(rid,)))
            if not row or user['id'] not in (row['sender_id'],row['recipient_id']):
                raise HTTPException(404,'申请不存在')
            allowed=row['sender_id'] if body.action=='cancel' else row['recipient_id']
            if user['id']!=allowed:
                raise HTTPException(403,'只能处理发给自己的申请，或撤回自己发出的申请')
            if row['status']!='pending':
                raise HTTPException(409,'申请已经处理，请刷新列表')
            status={'accept':'accepted','reject':'rejected','cancel':'cancelled'}[body.action]
            if body.action=='accept':
                if con.execute('SELECT COUNT(*) FROM users WHERE id IN (?,?) AND is_active=1',(row['sender_id'],row['recipient_id'])).fetchone()[0]!=2:
                    raise HTTPException(409,'其中一个账号已停用')
                p=db.one(con.execute('SELECT therapist_id FROM patients WHERE id=?',(row['patient_id'],)))
                if p['therapist_id'] is not None:
                    raise HTTPException(409,'患者已有主责康复师，请刷新列表')
                con.execute('UPDATE patients SET therapist_id=? WHERE id=?',(row['therapist_id'],row['patient_id']))
                con.execute("UPDATE care_requests SET status='cancelled',updated_at=? WHERE patient_id=? AND status='pending' AND id<>?",(db.now(),row['patient_id'],rid))
            con.execute('UPDATE care_requests SET status=?,updated_at=? WHERE id=?',(status,db.now(),rid))
            audit(con,user['id'],'care.'+body.action,f'care_request:{rid}')
        return {'ok':True,'status':status}

    @app.delete('/api/v1/care/connections/{pid}')
    def unlink(pid: int, user=Depends(member), con=Depends(get_con)):
        with con:
            con.execute('BEGIN IMMEDIATE')
            p=db.one(con.execute('SELECT * FROM patients WHERE id=?',(pid,)))
            if not p or not p['therapist_id'] or user['id'] not in (p['user_id'],p['therapist_id']):
                raise HTTPException(404,'关联不存在')
            con.execute("UPDATE plans SET status='paused' WHERE patient_id=? AND status='active'",(pid,))
            con.execute('UPDATE patients SET therapist_id=NULL WHERE id=?',(pid,))
            audit(con,user['id'],'care.unlink',f'patient:{pid}')
        return {'ok':True}
