"""Explicit local demo setup. Never reset existing accounts or patient data."""
from contextlib import closing
import db

DEMO_PATIENTS=[('p.zhaomin','zhao123','赵敏'),('p.linyuqing','linyu123','林雨晴'),('p.zhouqiming','zhou123','周启明')]

def provision(con):
    with con:
        con.execute('BEGIN IMMEDIATE')
        therapist=con.execute("SELECT * FROM users WHERE username='dr.lin' AND role='therapist' AND is_active=1").fetchone()
        if not therapist:raise ValueError('缺少原有演示康复师 dr.lin，不自动创建或更改真实康复师')
        rows=[]
        for username,password,name in DEMO_PATIENTS:
            old=con.execute('SELECT * FROM users WHERE username=?',(username,)).fetchone()
            if old:
                patient=con.execute('SELECT * FROM patients WHERE user_id=?',(old['id'],)).fetchone()
                if old['display_name']!=name or old['role']!='patient' or not patient or patient['notes']!='虚构演示账号，由演示初始化工具创建':
                    raise ValueError(f'{username} 已存在且不是本工具创建的演示账号，停止而不覆盖')
                rows.append((username,'已存在，保留密码和关联'));continue
            uid=con.execute('INSERT INTO users(institution_id,role,username,password_hash,display_name) VALUES(?,?,?,?,?)',(therapist['institution_id'],'patient',username,db.hash_password(password),name)).lastrowid
            con.execute('INSERT INTO patients(user_id,institution_id,therapist_id,phase,notes) VALUES(?,?,?,?,?)',(uid,therapist['institution_id'],therapist['id'],'演示档案，待康复师设置','虚构演示账号，由演示初始化工具创建'))
            con.execute('INSERT INTO audit_logs(action,target) VALUES(?,?)',('demo.patient.create',f'user:{uid}'))
            rows.append((username,'已创建'))
        return rows

if __name__=='__main__':
    db.init_db()
    with closing(db.connect()) as con:
        for username,status in provision(con):print(username,status)
