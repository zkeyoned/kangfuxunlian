"""Bounded JPEG batches. Validate all frames before advancing any analyzer."""
import base64
import math
import numpy as np

def decode_batch(body, cv2):
    if cv2 is None: raise ValueError('服务器尚未安装RTMPose图像依赖')
    frames = body.get('frames') if isinstance(body, dict) else None
    if not isinstance(frames, list) or not 1 <= len(frames) <= 8:
        raise ValueError('一次需要1至8帧')
    decoded, last, ids = [], -1., set()
    for item in frames:
        if not isinstance(item, dict): raise ValueError('无效帧')
        t, fid = item.get('timestamp_s'), item.get('frame_id')
        if isinstance(t, bool) or not isinstance(t, (int,float)) or not math.isfinite(t) or t <= last or t < 0:
            raise ValueError('采集时间必须有限且严格递增')
        if isinstance(fid, bool) or not isinstance(fid, int) or fid < 0 or fid in ids:
            raise ValueError('帧编号无效或重复')
        encoded = item.get('image')
        if not isinstance(encoded,str) or len(encoded)>400000: raise ValueError('图像过大')
        raw = base64.b64decode(encoded, validate=True)
        # Inspect JPEG SOF dimensions before OpenCV allocates decoded pixels.
        if raw[:2] != b'\xff\xd8': raise ValueError('必须是JPEG图像')
        i, size = 2, None
        while i+4 <= len(raw):
            if raw[i]!=255: break
            while i<len(raw) and raw[i]==255: i+=1
            if i>=len(raw): break
            marker=raw[i];i+=1
            if marker in (0xd8,0xd9) or 0xd0<=marker<=0xd7: continue
            if i+2>len(raw): break
            length=int.from_bytes(raw[i:i+2],'big')
            if length<2 or i+length>len(raw): break
            if marker in (0xc0,0xc1,0xc2) and length>=8:
                size=(int.from_bytes(raw[i+3:i+5],'big'),int.from_bytes(raw[i+5:i+7],'big'));break
            i+=length
        if not size or not all(0<v<=960 for v in size): raise ValueError('JPEG尺寸须不超过960×960')
        frame=cv2.imdecode(np.frombuffer(raw,dtype=np.uint8),cv2.IMREAD_COLOR)
        if frame is None or frame.shape[:2]!=size: raise ValueError('JPEG解码失败')
        decoded.append((frame,t,fid));last=t;ids.add(fid)
    return decoded

def process_batch(session, decoded):
    previous=session.analyzer.engine.last_t
    if previous is not None and decoded[0][1]<=previous: raise ValueError('画面时间戳必须递增')
    reps, events = [], []
    for frame,t,fid in decoded:
        result=session.process(frame,t)
        reps.extend(result.get('new_reps') or [])
        events.extend(result.get('feedback_events') or [])
    return {**result,'frame_id':fid,'batch_frames':len(decoded),'new_reps':reps,'feedback_events':events}
