"""Local video/explicit webcam analysis. Frame timing uses presentation timestamps."""
import argparse
from dataclasses import asdict
from datetime import datetime, timezone
from fractions import Fraction
from pathlib import Path
import hashlib
import json
import time
from collections import Counter

from . import __version__
from .core import Config, Analyzer, metrics
from .model import PoseModel, RTMPoseModel, download_model, download_rtmpose, required_rtm_assets
from .tracking import PoseTracker, TrackingConfig
from .measures import MotionMeasures,MeasureConfig
from .exercises import ExerciseAnalyzer,NAMES

ROOT=Path(__file__).resolve().parents[1]


def video_frames(path):
    import av
    with av.open(str(path)) as container:
        stream=container.streams.video[0]
        first=None
        previous=-1.
        for frame in container.decode(stream):
            if frame.pts is None or frame.time_base is None:
                raise ValueError("Video has no presentation timestamps; re-encode it before analysis")
            t=float(frame.pts*frame.time_base)
            if first is None:
                first=t
            t-=first
            if t<=previous:
                raise ValueError("Non-increasing video timestamps; re-encode video")
            previous=t
            yield t,frame.to_ndarray(format="bgr24")


def camera_frames(index,resolution='720p',capture_info=None):
    import cv2
    sizes={'480p':(640,480),'720p':(1280,720),'1080p':(1920,1080)}
    if resolution not in sizes:raise ValueError('Unsupported camera resolution')
    cap=cv2.VideoCapture(index)
    if not cap.isOpened():
        cap.release()
        raise RuntimeError("Cannot open camera. Check Windows camera permissions and other apps.")
    try:
        width,height=sizes[resolution]
        accepted={
            'mjpg':bool(cap.set(cv2.CAP_PROP_FOURCC,cv2.VideoWriter_fourcc(*'MJPG'))),
            'width':bool(cap.set(cv2.CAP_PROP_FRAME_WIDTH,width)),
            'height':bool(cap.set(cv2.CAP_PROP_FRAME_HEIGHT,height)),
            'fps':bool(cap.set(cv2.CAP_PROP_FPS,30))}
        if capture_info is not None:
            capture_info.update(requested_width=width,requested_height=height,requested_fps=30,
                                property_requests_accepted=accepted)
        start=time.monotonic();previous_size=None
        while True:
            ok,frame=cap.read()
            if not ok:
                raise RuntimeError("Camera frame read failed")
            actual_h,actual_w=frame.shape[:2]
            if previous_size!=(actual_w,actual_h):
                matched=(actual_w,actual_h)==(width,height)
                if capture_info is not None:
                    capture_info.update(actual_width=actual_w,actual_height=actual_h,requested_size_matched=matched)
                print(f'摄像头请求 {width}×{height}；实际画面 {actual_w}×{actual_h}'+
                      ('。' if matched else '（设备未按请求输出，请以实际尺寸为准）。'),flush=True)
                previous_size=(actual_w,actual_h)
            yield time.monotonic()-start,frame
    finally:
        cap.release()


class AnnotatedWriter:
    """MPEG4 video with original variable timing, without original audio."""
    def __init__(self,path,width,height):
        import av
        self.av=av
        self.container=av.open(str(path),"w")
        self.stream=self.container.add_stream("mpeg4",rate=30)
        self.stream.width=width//2*2
        self.stream.height=height//2*2
        # Explicit quality budget: previous unspecified bitrate heavily compressed motion.
        self.target_bitrate=max(2_000_000,self.stream.width*self.stream.height*6)
        self.stream.bit_rate=self.target_bitrate
        self.stream.pix_fmt="yuv420p"
        self.stream.time_base=Fraction(1,10000)
        self.stream.codec_context.time_base=Fraction(1,10000)
        self.last_pts=-1

    def write(self,bgr,t):
        import cv2
        if bgr.shape[1]!=self.stream.width or bgr.shape[0]!=self.stream.height:
            bgr=cv2.resize(bgr,(self.stream.width,self.stream.height))
        frame=self.av.VideoFrame.from_ndarray(bgr,format="bgr24")
        frame.time_base=Fraction(1,10000)
        frame.pts=max(self.last_pts+1,round(t*10000))
        self.last_pts=frame.pts
        for packet in self.stream.encode(frame):
            self.container.mux(packet)

    def close(self):
        try:
            for packet in self.stream.encode():
                self.container.mux(packet)
        finally:
            self.container.close()


def overlay(frame,m,state,side,min_confidence=.6,backend="mediapipe",quality_flags=(),prediction=None,measure=None):
    import cv2
    pts=m["keypoints"]
    line_color=(255,180,30) if backend.startswith("rtmpose") else (70,230,100)
    point_color=(255,90,220) if backend.startswith("rtmpose") else (0,220,255)
    for name,p in pts.items():
        if p["confidence"]>=min_confidence and p["x"] is not None and p["y"] is not None:
            point=(round(p["x"]),round(p["y"]))
            cv2.circle(frame,point,6,point_color,-1)
            cv2.putText(frame,name,point,cv2.FONT_HERSHEY_SIMPLEX,.45,point_color,1)
    for a,b in (("shoulder","hip"),("hip","knee"),("knee","ankle")):
        if a in pts and b in pts and min(pts[a]["confidence"],pts[b]["confidence"])>=min_confidence:
            cv2.line(frame,(round(pts[a]["x"]),round(pts[a]["y"])),
                     (round(pts[b]["x"]),round(pts[b]["y"])),line_color,3)
    if prediction:
        predicted=prediction["keypoints"]
        for a,b in (("hip","knee"),("knee","ankle")):
            p,q=predicted[a],predicted[b]
            import math
            length=math.hypot(q["x"]-p["x"],q["y"]-p["y"])
            for offset in range(0,max(1,int(length)),16):
                u=offset/max(length,1); v=min(1,(offset+8)/max(length,1))
                start=tuple(round(p[k]+u*(q[k]-p[k])) for k in ("x","y"))
                end=tuple(round(p[k]+v*(q[k]-p[k])) for k in ("x","y"))
                cv2.line(frame,start,end,(0,190,255),2)
    value=state["smoothed_included_deg"]
    lines=["RESEARCH DEMO - NOT CLINICALLY VALIDATED",f"{state.get('exercise','KNEE_EXTENSION')} | {side}",
           f"Knee included angle: {value:.1f} deg" if value is not None else "Angle: UNKNOWN",
           f"Phase: {state['phase']} | Reps: {state['completed_reps']}",
           f"Detection: {state['detection_status']} | Q / Esc: stop",
           "Check: "+(", ".join(quality_flags) if quality_flags else "tracking OK")]
    if prediction:
        lines.append("ORANGE DASHES: prediction only; angle / hold paused")
    if measure:
        cal=measure['calibration'];v=measure['measurement_metrics']
        lines.append(f"Reference: {cal['status']} {cal['progress']*100:.0f}% | B reset")
        def fmt(x):return '--' if x is None else f'{x:.1f}'
        lines.append('Trunk +forward/-back: '+fmt(v['trunk_signed_deg'])+' | Delta: '+fmt(v['trunk_delta_deg']))
        lines.append('Knee speed deg/s: '+fmt(v['knee_velocity_deg_s'])+' | Thigh delta: '+fmt(v['thigh_delta_deg']))
        if measure.get('display_feedback'):lines.append('Notice: '+', '.join(measure['display_feedback']))
    for i,line in enumerate(lines):
        y=25+i*25
        cv2.putText(frame,line,(10,y),cv2.FONT_HERSHEY_SIMPLEX,.5,(0,0,0),3)
        cv2.putText(frame,line,(10,y),cv2.FONT_HERSHEY_SIMPLEX,.5,(255,255,255),1)
    return frame


def analyze(source,output,side="left",config_path=None,model_path=None,preview=False,
            save_video=True,max_seconds=None,backend="mediapipe",tracking=True,rtm_roi="detected",facing="left",exercise="1",camera_resolution='720p',training_plan=None):
    import cv2
    config_path=Path(config_path or ROOT/"config/knee_extension.json")
    document=json.loads(config_path.read_text(encoding="utf-8-sig"))
    if exercise not in NAMES:raise ValueError('Unsupported exercise')
    if rtm_roi=='locked' and (backend!='rtmpose' or not preview):
        raise ValueError('Subject lock requires RTMPose and interactive preview for confirmation')
    if backend not in ("mediapipe","rtmpose"):
        raise ValueError("Unknown backend")
    params=dict(document["parameters"])
    params.update(document.get("backend_parameters",{}).get(backend,{}))
    if tracking:
        params["smoothing_tau_s"]=0 # coordinate filtering already smooths angles; avoid double lag
    config=Config(**params)
    tracking_config=TrackingConfig(**document.get("tracking",{}))
    tracker=PoseTracker(side,config.min_confidence,tracking_config)
    model_path=Path(model_path or (ROOT/"models/rtmpose" if backend=="rtmpose" else ROOT/"models/pose_landmarker_full.task"))
    paths=[model_path/name for name in required_rtm_assets(rtm_roi)] if backend=="rtmpose" else [model_path]
    if not all(p.is_file() for p in paths):
        raise FileNotFoundError(f"Model missing. Run: python -m rehab_pose.run --backend {backend} --download-model")
    hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    output=Path(output)
    output.mkdir(parents=True,exist_ok=False)
    from .exercise_rules import ExerciseFeedback,ExerciseRulesConfig,UNSUPPORTED
    rules_config=ExerciseRulesConfig(**document.get('exercise_rules',{}))
    analyzer=ExerciseAnalyzer(exercise,config,document.get('exercise_profiles',{}).get(exercise),rules_config)
    extra_feedback=ExerciseFeedback(exercise,rules_config)
    from .session import TrainingSession
    session=TrainingSession(training_plan) if training_plan else None
    if session:
        expected=training_plan.hold_s
        if exercise=='1' and expected not in (2,2.5,3,5):raise ValueError('动作1当前支持保持2、2.5、3或5秒，标准默认3秒')
        if exercise=='2' and expected!=5:raise ValueError('动作2当前保持5秒')
        if exercise in ('6','8') and expected!=0:raise ValueError('动作6/8不设置顶点保持')
        analyzer.engine.config.min_hold_s=expected
    measure_config=MeasureConfig(**document.get('measurement',{}))
    measures=MotionMeasures(facing,measure_config,config.min_confidence,exercise)
    target_generation=0;previous_shape=None;calibration_history=[];feedback_history=[];shown_feedback={}
    from .leg_selection import LegSelection
    # The start-page side is sufficient. Never silently block an entire session
    # behind a keyboard confirmation step.
    leg=LegSelection(side,False)
    guidance_last=None
    pending_leg_click=[]
    model=None
    writer=None
    source_writer=None
    capture_info={'source':'camera' if isinstance(source,int) else 'video'}
    frames=camera_frames(source,camera_resolution,capture_info) if isinstance(source,int) else video_frames(source)
    status="completed"
    count=0
    reliable_count=0
    error=None
    flag_counts=Counter()
    raw_reliable_count=0
    prediction_count=0
    inference_seconds=0.
    try:
        model=RTMPoseModel(model_path,rtm_roi) if backend=="rtmpose" else PoseModel(model_path)
        if preview:
            cv2.namedWindow('Knee extension demo')
            def click(event,x,y,flags,param):
                if event==cv2.EVENT_LBUTTONDOWN:
                    if rtm_roi=='locked' and model.subject.status!='locked':model.subject.click(x,y)
                    elif not leg.confirmed:pending_leg_click.append((x,y))
            cv2.setMouseCallback('Knee extension demo',click)
        with (output/"frames.jsonl").open("w",encoding="utf-8") as records:
            for t,frame in frames:
                if session:
                    old_status=session.status;session.tick(t)
                    toggle=output/'PAUSE_TOGGLE'
                    if toggle.exists():
                        toggle.unlink();session.toggle_pause(t)
                    if old_status!=session.status:
                        analyzer.abort(t,'session_transition');measures.reset();shown_feedback.clear()
                if (output/"STOP").exists():
                    status="stopped_by_user"
                    break
                if max_seconds is not None and t>max_seconds:
                    status="time_limit"
                    break
                h,w=frame.shape[:2]
                inference_start=time.perf_counter()
                landmarks,reason=model.detect(cv2.cvtColor(frame,cv2.COLOR_BGR2RGB),t)
                inference_seconds+=time.perf_counter()-inference_start
                subject=model.subject.snapshot() if rtm_roi=='locked' else {'status':'not_locked','generation':0,'identity_verified':False}
                if previous_shape is not None and previous_shape!=(w,h):
                    measures.reset();analyzer.abort(t,'frame_size_changed');shown_feedback.clear()
                    leg.reset()
                previous_shape=(w,h)
                if subject['generation']!=target_generation or (rtm_roi=='locked' and subject['status']!='locked'):
                    tracker=PoseTracker(side,config.min_confidence,tracking_config)
                    measures.reset();analyzer.abort(t,'subject_confirmation_required');shown_feedback.clear()
                    target_generation=subject['generation']
                    leg.reset()
                if pending_leg_click:
                    x,y=pending_leg_click.pop();pending_leg_click.clear()
                    if leg.click(x,y,landmarks,w,h,config.min_confidence):
                        side=leg.side;tracker=PoseTracker(side,config.min_confidence,tracking_config)
                        measures.reset();analyzer.abort(t,'leg_clicked');shown_feedback.clear()
                        print('已选中'+side+'彩线，请检查后按回车确认。',flush=True)
                    else:print('两腿重叠或点击位置不明确，请稍微分开腿后点击膝或踝附近。',flush=True)
                if tracking:
                    m,quality=tracker.update(t,landmarks,w,h)
                else:
                    m=metrics(landmarks,w,h,side,config.min_confidence)
                    quality={"quality_flags":[],"raw_metrics":m}
                flag_counts.update(quality["quality_flags"])
                raw_reliable_count+=int(quality["raw_metrics"]["visible"])
                prediction_count+=int(quality.get("bridge_pending",False))
                if 'possible_side_switch' in quality['quality_flags']:
                    leg.reset();measures.reset();analyzer.abort(t,'leg_reconfirmation_required')
                if not leg.confirmed:
                    m=dict(m,visible=False,value=None)
                if exercise=='1' and m['visible'] and measures.baseline:
                    import math
                    hip=m['keypoints']['hip'];knee=m['keypoints']['knee']
                    thigh=math.degrees(math.atan2(hip['y']-knee['y'],measures.direction*(knee['x']-hip['x'])))
                    if abs(thigh)>50:
                        measures.reset();analyzer.abort(t,'left_seated_pose');shown_feedback.clear()
                blocked=session is not None and session.status!='training'
                measure=measures.update(t,dict(m,visible=False) if blocked else m,w,h,analyzer.state)
                measure['feedback_events'].extend(extra_feedback.update(t,measure,analyzer.state))
                guidance = 'confirm_training_leg' if not leg.confirmed else measure['calibration']['status']
                guide_text={'confirm_training_leg':'先轻抬训练腿，核对两条彩线；按L选LEFT、K选RIGHT，再按回车确认。然后放下小腿。',
                            'waiting_for_points':'评估暂停：关节不可靠，请露出训练侧髋膝踝。',
                            'check_start_pose_and_direction':'尚未标定：请坐好并放下小腿，检查选择的腿和脚伸出方向。',
                            'hold_start_pose':'尚未开始评估：保持坐姿不动，等待约2秒稳定标定。',
                            'ready':'标定完成，可以开始训练。'}
                measure['guidance']={'status':guidance,'message':guide_text.get(guidance,guidance)}
                if exercise!='1' and guidance in ('hold_start_pose','check_start_pose_and_direction'):
                    instruction={'2':'仰卧，训练腿放平伸直，另一腿屈膝；从侧面拍摄。','6':'扶稳支撑物，站直并保持侧面取景。','8':'坐好，双脚放稳，保持侧面取景。'}[exercise]
                    measure['guidance']['message']='等待起始标定：'+instruction+'请稳定保持约2秒。'
                if blocked:
                    guidance=session.status
                    measure['guidance']={'status':guidance,'message':{'resting':'组间休息：不计数，不累计保持时间。','paused':'已暂停，恢复后重新标定。','completed':'训练计划已完成。'}[guidance]}
                if guidance=='hold_start_pose':
                    measure['guidance']['remaining_s']=max(0,measure_config.calibration_s*(1-measure['calibration']['progress']))
                if guidance=='check_start_pose_and_direction' and exercise=='1':
                    vals=measure['measurement_metrics']
                    measure['guidance']['message']+=f" 当前膝夹角{vals['knee_included_deg']:.1f}°（起始范围55～130°），大腿方向{vals['thigh_elevation_deg']:.1f}°（需接近水平±35°）。"
                if guidance!=guidance_last:
                    print(measure['guidance']['message'],flush=True);guidance_last=guidance
                baseline=measure['calibration']['baseline']
                if baseline and (not calibration_history or baseline['captured_at_s']!=calibration_history[-1]['captured_at_s']):
                    calibration_history.append(dict(baseline,target_generation=target_generation))
                before_reps=len(analyzer.reps)
                state=analyzer.update(t,dict(m,visible=False) if blocked else m,measure,quality.get("bridge_pending",False) and not blocked)
                if len(analyzer.reps)>before_reps:
                    rep=analyzer.reps[-1];rep['target_generation']=target_generation
                    if session:session.record_rep(t,rep)
                    for key,code,message in [('amplitude_met','AMPLITUDE_BELOW_TARGET','本次尚未伸到目标角度，请在舒适范围内缓慢伸直'),
                                             ('hold_met','HOLD_TOO_SHORT','本次连续保持时间不足'),
                                             ('extension_time_met','EXTENSION_TOO_FAST','本次伸出过快，请缓慢伸膝'),
                                             ('return_time_met','RETURN_TOO_FAST','本次放回过快，请缓慢放下')]:
                        if rep['target_comparison'][key] is False:
                            measure['feedback_events'].append(dict(code=code,message=message,level='notice',timestamp_s=t,rep_index=rep['index']))
                            break
                for event in measure['feedback_events']:
                    feedback_history.append(event);shown_feedback[event['code']]=t+2.
                if not m['visible']:shown_feedback.clear()
                measure['display_feedback']=[code for code,end in shown_feedback.items() if end>=t]
                record={"schema_version":"1.4","algorithm_version":__version__,"backend":backend,
                        "rtm_roi":rtm_roi if backend=="rtmpose" else None,
                        "side":side,"subject":subject,
                        'leg_confirmation':{'confirmed':leg.confirmed,'model_side':leg.side,'generation':leg.generation,'required':leg.required},
                        "frame_size":{"width":w,"height":h},"pose_status":reason,**m,**state,**quality,**measure}
                if session:record['training_progress']=session.snapshot(t)
                records.write(json.dumps(record,allow_nan=False)+"\n")
                count+=1
                reliable_count+=int(m["visible"])
                if save_video:
                    if source_writer is None:source_writer=AnnotatedWriter(output/'source.mp4',w,h)
                    source_writer.write(frame,t)
                display_backend=backend+(" [fixed single person]" if backend=="rtmpose" and rtm_roi=="full-frame" else "")
                overlay(frame,m,state,side,config.min_confidence,display_backend,quality["quality_flags"],quality.get("display_prediction"),measure)
                if not leg.confirmed:leg.draw(frame,landmarks,config.min_confidence)
                elif measure['calibration']['status']!='ready':
                    instruction={'1':'sit, lower leg','2':'lie down, straight training leg','6':'stand upright with support','8':'sit on chair'}[exercise]
                    cv2.putText(frame,'NOT EVALUATING: '+instruction+', hold still',(15,h-45),0,.6,(0,255,255),2)
                    remaining=measure['guidance'].get('remaining_s')
                    if remaining is not None:cv2.putText(frame,f'Hold still: {remaining:.1f}s remaining',(15,h-15),0,.65,(0,255,255),2)
                if rtm_roi=='locked':model.subject.draw(frame)
                if session:
                    progress=session.snapshot(t)
                    cv2.putText(frame,f"Set {session.group}/{training_plan.sets}  Reps {session.count}/{training_plan.reps_per_set}  {session.status}  Rest {progress['rest_remaining_s']:.0f}s | P pause",(15,h-75),0,.6,(0,255,255),2)
                if save_video:
                    if writer is None:
                        writer=AnnotatedWriter(output/"annotated.mp4",w,h)
                    writer.write(frame,t)
                if preview:
                    cv2.imshow("Knee extension demo",frame)
                    key=cv2.waitKey(1)&255
                    if key in (27,ord("q")):
                        status="stopped_by_user"
                        break
                    if key==ord('p') and session:
                        session.toggle_pause(t);analyzer.abort(t,'user_pause_resume');measures.reset();shown_feedback.clear()
                    if key==ord('b'):
                        measures.reset();analyzer.abort(t,'manual_recalibration');shown_feedback.clear()
                    if key==ord('l'):
                        if session and session.total:
                            print('本次计划已开始计数；换训练侧请结束后重新开始。',flush=True)
                            continue
                        side='left'
                        leg.choose(side);tracker=PoseTracker(side,config.min_confidence,tracking_config)
                        measures.reset();analyzer.abort(t,'leg_changed');shown_feedback.clear()
                    if key==ord('k'):
                        if session and session.total:
                            print('本次计划已开始计数；换训练侧请结束后重新开始。',flush=True)
                            continue
                        side='right';leg.choose(side);tracker=PoseTracker(side,config.min_confidence,tracking_config)
                        measures.reset();analyzer.abort(t,'leg_changed');shown_feedback.clear()
                    if key in (10,13) and not leg.confirmed:
                        if leg.confirm(landmarks,w,h,config.min_confidence):
                            measures.reset();analyzer.abort(t,'leg_confirmed')
                            print('训练腿已确认。现在放下小腿，坐稳完成标定。',flush=True)
                    if rtm_roi=='locked':
                        if key==ord('c'):model.subject.confirm()
                        if key==ord('r'):model.subject.reset()
                    if cv2.getWindowProperty("Knee extension demo",cv2.WND_PROP_VISIBLE)<1:
                        status="stopped_by_user"
                        break
                if count%100==0:
                    print(f"Frames: {count}, reps: {len(analyzer.reps)}",flush=True)
                if session and session.status=='completed':
                    status='plan_completed';break
        if count==0:
            raise ValueError("No video frames decoded")
    except KeyboardInterrupt:
        status="stopped_by_user"
    except Exception as exc:
        status="failed"
        error=str(exc)
        raise
    finally:
        frames.close()
        analyzer.finish()
        try:
            try:
                if writer:writer.close()
            finally:
                if source_writer:source_writer.close()
        finally:
            if model:
                model.close()
            if preview:
                cv2.destroyAllWindows()
            summary={"schema_version":"1.4","algorithm_version":__version__,"backend":backend,
                     "rtm_roi":rtm_roi if backend=="rtmpose" else None,
                     "created_utc":datetime.now(timezone.utc).isoformat(),
                     "exercise":NAMES[exercise],"experimental_exercise":exercise!='1',"side":side,"facing":facing,"status":status,"error":error,
                     "note":"TECHNICAL TEST ONLY; not clinically validated; no muscle activation measurement",
                     "angle_definition":"ipsilateral hip-knee-ankle pixel angle 0..180; extension increases angle",
                     "timing_source":"monotonic_clock" if isinstance(source,int) else "video_presentation_timestamps",
                     "configuration":document,"effective_parameters":asdict(analyzer.engine.config),
                     "measurement_parameters":asdict(measure_config),'calibrations':calibration_history,'feedback_events':feedback_history,
                     'target_confirmations':target_generation,
                     'capture':capture_info,
                     'recording_target_bitrate':writer.target_bitrate if writer else None,
                     "tracking_enabled":tracking,"tracking_parameters":asdict(tracking_config),
                     "model_hashes":hashes,"quality_flag_counts":dict(flag_counts),
                     "raw_reliable_frames":raw_reliable_count,
                     "mean_inference_ms":inference_seconds/count*1000 if count else None,
                     "frames":count,"reliable_frames":reliable_count,
                     "prediction_only_frames":prediction_count,
                     "reps_needing_review":sum(bool(r.get("needs_review")) for r in analyzer.reps),
                      "completed_reps":len(analyzer.reps),
                      "target_completed_reps":sum(bool(r.get('target_completed')) for r in analyzer.reps),
                      "action_standard_version":"seated-knee-extension-v0.1" if exercise=='1' else None,
                      "repetitions":analyzer.reps,
                     "interrupted_attempts":analyzer.interrupted,"raw_video_copied":False}
            summary['unannotated_video_saved']=source_writer is not None
            summary['unannotated_video_note']='source.mp4 is encoded camera/input frames before overlays, not lossless sensor data'
            summary['exercise_rules']=asdict(rules_config)
            summary['unsupported_checks']=UNSUPPORTED.get(exercise,['肌肉发力'])
            from .contract import rep_to_contract
            summary['contract_reps']=[rep_to_contract(r,feedback_history) for r in analyzer.reps]
            if session:
                session.finish(session.last_t or 0,status)
                summary['training_session']=session.result(session.last_t or 0)
            (output/"summary.json").write_text(json.dumps(summary,indent=2,ensure_ascii=False,allow_nan=False),encoding="utf-8")
            if (output/'frames.jsonl').exists():
                from .assessment import write_report
                write_report(output, summary)
    print(f"Done: {output.resolve()}",flush=True)
    return summary


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    group=parser.add_mutually_exclusive_group()
    group.add_argument("--video",type=Path)
    group.add_argument("--camera",type=int)
    parser.add_argument("--side",choices=["left","right"],default="left")
    parser.add_argument('--facing',choices=['left','right'],default='left',help='On-screen direction toward toes in start pose')
    parser.add_argument('--exercise',choices=list(NAMES),default='1')
    parser.add_argument('--camera-resolution',choices=['480p','720p','1080p'],default='720p')
    parser.add_argument('--sets',type=int,help='Enable a single-side training plan')
    parser.add_argument('--reps-per-set',type=int,default=10)
    parser.add_argument('--hold-seconds',type=float,default=None)
    parser.add_argument("--config",type=Path,default=ROOT/"config/knee_extension.json")
    parser.add_argument("--model",type=Path,help="MediaPipe file or RTMPose model directory")
    parser.add_argument("--backend",choices=["mediapipe","rtmpose"],default="mediapipe")
    parser.add_argument("--rtm-roi",choices=["detected","full-frame","locked"],default="detected",
                        help="full-frame assumes exactly one person, bypasses person detection")
    parser.add_argument("--no-tracking",action="store_true",help="Comparison only: disable quality gate and coordinate filtering")
    parser.add_argument("--output",type=Path)
    parser.add_argument("--preview",action="store_true")
    parser.add_argument("--no-save-video",action="store_true")
    parser.add_argument("--max-seconds",type=float)
    parser.add_argument("--download-model",action="store_true")
    args=parser.parse_args()
    if args.download_model:
        if args.backend=="rtmpose":
            print(download_rtmpose(args.model or ROOT/"models/rtmpose"))
        else:
            print(download_model(args.model or ROOT/"models/pose_landmarker_full.task"))
        return
    if args.video is None and args.camera is None:
        parser.error("Choose --video PATH or --camera 0, or --download-model")
    if args.max_seconds is not None and args.max_seconds<=0:
        parser.error("--max-seconds must be positive")
    if args.camera is not None and not args.preview and args.max_seconds is None:
        parser.error("Camera requires --preview or --max-seconds to allow stopping")
    output=args.output or ROOT/"results"/datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    from .session import TrainingPlan
    hold=args.hold_seconds if args.hold_seconds is not None else {'1':3.,'2':5.,'6':0.,'8':0.}[args.exercise]
    try:plan=TrainingPlan(args.sets,args.reps_per_set,hold) if args.sets is not None else None
    except ValueError as exc:parser.error(str(exc))
    analyze(args.camera if args.camera is not None else args.video,output,args.side,args.config,args.model,
            args.preview,not args.no_save_video,args.max_seconds,args.backend,not args.no_tracking,args.rtm_roi,args.facing,args.exercise,args.camera_resolution,plan)


if __name__=="__main__":
    main()
