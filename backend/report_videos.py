import hashlib, math
from typing import Literal
from fastapi import Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field
import db

CHUNK=1048576
class VideoInput(BaseModel):
    mime: Literal['video/webm','video/mp4']
    size:int=Field(ge=12,le=256*CHUNK)
    sha256:str=Field(pattern=r'^[a-f0-9]{64}$')
    duration_s:float=Field(ge=0,le=86400,allow_inf_nan=False)
    preview_flipped:bool=False

def video_meta(con,rid):
    row=db.one(con.execute('SELECT * FROM report_videos WHERE report_id=?',(rid,)))
    if row:row['chunk_size']=CHUNK
    return row

def install_routes(app,get_con,current_user,patient_in_scope):
    def access(con,user,rid,write=False):
        r=db.one(con.execute('SELECT patient_id FROM training_reports WHERE id=?',(rid,)))
        if not r:raise HTTPException(404,'报告不存在')
        patient_in_scope(con,user,r['patient_id'])
        if write and user['role']!='patient':raise HTTPException(403,'仅患者本人可上传录像')
        return video_meta(con,rid)

    @app.post('/api/v1/training-reports/{rid}/video')
    def start(rid:int,body:VideoInput,user=Depends(current_user),con=Depends(get_con)):
        with con:
            con.execute('BEGIN IMMEDIATE');old=access(con,user,rid,True)
            if old:
                if any(old[k]!=getattr(body,k) for k in ('mime','size','sha256','duration_s','preview_flipped')):raise HTTPException(409,'本报告已关联其他录像，不会覆盖')
                return old
            con.execute('INSERT INTO report_videos(report_id,mime,size,sha256,duration_s,preview_flipped,chunk_count,created_at) VALUES(?,?,?,?,?,?,?,?)',
              (rid,body.mime,body.size,body.sha256,body.duration_s,body.preview_flipped,math.ceil(body.size/CHUNK),db.now()))
        return video_meta(con,rid)

    @app.put('/api/v1/training-reports/{rid}/video/chunks/{index}')
    async def upload(rid:int,index:int,request:Request,user=Depends(current_user),con=Depends(get_con)):
        v=access(con,user,rid,True)
        if not v:raise HTTPException(409,'请先初始化录像')
        if not 0<=index<v['chunk_count']:raise HTTPException(400,'分块索引无效')
        expected=min(CHUNK,v['size']-index*CHUNK);data=bytearray()
        async for part in request.stream():
            data.extend(part)
            if len(data)>expected:raise HTTPException(413,'录像块过大')
        if len(data)!=expected:raise HTTPException(400,'录像块长度不完整')
        with con:
            con.execute('BEGIN IMMEDIATE');access(con,user,rid,True)
            old=con.execute('SELECT data FROM report_video_chunks WHERE report_id=? AND chunk_index=?',(rid,index)).fetchone()
            if old:
                if old[0]!=bytes(data):raise HTTPException(409,'同一块内容不同')
            else:con.execute('INSERT INTO report_video_chunks VALUES(?,?,?)',(rid,index,bytes(data)))
        return {'ok':True,'index':index}

    @app.post('/api/v1/training-reports/{rid}/video/complete')
    def complete(rid:int,user=Depends(current_user),con=Depends(get_con)):
        with con:
            con.execute('BEGIN IMMEDIATE');v=access(con,user,rid,True)
            if not v:raise HTTPException(404,'无录像')
            digest=hashlib.sha256();count=0;size=0;header=b''
            for row in con.execute('SELECT data FROM report_video_chunks WHERE report_id=? ORDER BY chunk_index',(rid,)):
                block=row[0]
                if not count:header=block[:12]
                digest.update(block);count+=1;size+=len(block)
            if count!=v['chunk_count'] or size!=v['size'] or digest.hexdigest()!=v['sha256']:raise HTTPException(409,'录像尚未完整上传或校验失败，请重试')
            if not (header.startswith(b'\x1a\x45\xdf\xa3') if v['mime']=='video/webm' else header[4:8]==b'ftyp'):raise HTTPException(400,'不是支持的录像容器')
            con.execute("UPDATE report_videos SET state='ready' WHERE report_id=?",(rid,))
        return video_meta(con,rid)

    @app.get('/api/v1/training-reports/{rid}/video')
    def info(rid:int,user=Depends(current_user),con=Depends(get_con)):
        return {'video':access(con,user,rid)}

    @app.get('/api/v1/training-reports/{rid}/video/chunks/{index}')
    def chunk(rid:int,index:int,user=Depends(current_user),con=Depends(get_con)):
        v=access(con,user,rid)
        if not v or v['state']!='ready':raise HTTPException(404,'录像尚未保存完成')
        r=con.execute('SELECT data FROM report_video_chunks WHERE report_id=? AND chunk_index=?',(rid,index)).fetchone()
        if not r:raise HTTPException(404,'录像块不存在')
        return Response(r[0],media_type='application/octet-stream',headers={'Cache-Control':'no-store','X-Content-Type-Options':'nosniff'})
