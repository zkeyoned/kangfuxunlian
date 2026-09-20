from pathlib import Path
import hashlib
import json
import urllib.request
import zipfile
import shutil

MODEL_URL="https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_full/float16/1/pose_landmarker_full.task"


def download_model(path):
    """Explicit first-run download. No model binary is redistributed in this project."""
    path=Path(path)
    if path.exists():
        return path
    path.parent.mkdir(parents=True,exist_ok=True)
    temporary=path.with_suffix(".download")
    try:
        with urllib.request.urlopen(MODEL_URL,timeout=90) as src, temporary.open("wb") as dst:
            while chunk:=src.read(1024*1024):
                dst.write(chunk)
        if temporary.stat().st_size<1000000:
            raise RuntimeError("Downloaded model unexpectedly small")
        temporary.replace(path)
        path.with_suffix(".source.json").write_text(json.dumps({"url":MODEL_URL,
            "sha256":hashlib.sha256(path.read_bytes()).hexdigest()},indent=2),encoding="utf-8")
    finally:
        temporary.unlink(missing_ok=True)
    return path


class PoseModel:
    def __init__(self,path):
        import mediapipe as mp
        self.mp=mp
        self.last_ms=-1
        self.detector=mp.tasks.vision.PoseLandmarker.create_from_options(
            mp.tasks.vision.PoseLandmarkerOptions(
                base_options=mp.tasks.BaseOptions(model_asset_path=str(path)),
                running_mode=mp.tasks.vision.RunningMode.VIDEO,
                num_poses=2))

    def detect(self,rgb,timestamp_s):
        import numpy as np
        ms=max(self.last_ms+1,round(timestamp_s*1000))
        self.last_ms=ms
        result=self.detector.detect_for_video(
            self.mp.Image(image_format=self.mp.ImageFormat.SRGB,data=np.ascontiguousarray(rgb)),ms)
        if len(result.pose_landmarks)!=1:
            return [], "no_person" if not result.pose_landmarks else "multiple_people"
        return [{"x":p.x,"y":p.y,"visibility":float(p.visibility or 0),
                 "presence":float(p.presence or 0)} for p in result.pose_landmarks[0]],"single_person"

    def close(self):
        self.detector.close()


# Official RTMLib Body presets: tiny detector + medium body-7 pose model.
RTM_ASSETS = {
    "detector.onnx": "https://download.openmmlab.com/mmpose/v1/projects/rtmposev1/onnx_sdk/yolox_tiny_8xb8-300e_humanart-6f3252f9.zip",
    "detector_m.onnx": "https://download.openmmlab.com/mmpose/v1/projects/rtmposev1/onnx_sdk/yolox_m_8xb8-300e_humanart-c2c7a14a.zip",
    "pose.onnx": "https://download.openmmlab.com/mmpose/v1/projects/rtmposev1/onnx_sdk/rtmpose-m_simcc-body7_pt-body7_420e-256x192-e48f03d0_20230504.zip",
}


def required_rtm_assets(roi_mode):
    return ['pose.onnx']+(['detector_m.onnx'] if roi_mode=='locked' else ['detector.onnx'] if roi_mode=='detected' else [])


def download_rtmpose(directory,roi_mode=None):
    directory=Path(directory)
    directory.mkdir(parents=True,exist_ok=True)
    for name,url in RTM_ASSETS.items():
        if roi_mode is not None and name not in required_rtm_assets(roi_mode):continue
        target=directory/name
        if target.exists():
            continue
        archive=directory/(name+".download.zip")
        partial=directory/(name+".partial")
        print(f"Downloading RTMPose asset: {name}",flush=True)
        try:
            with urllib.request.urlopen(url,timeout=90) as response, archive.open("wb") as out:
                shutil.copyfileobj(response,out)
            with zipfile.ZipFile(archive) as bundle:
                entries=[i for i in bundle.infolist() if i.filename.endswith(".onnx")]
                if len(entries)!=1:
                    raise ValueError("Expected exactly one ONNX model in official archive")
                # Stream a single member to our fixed path: never extract archive paths.
                with bundle.open(entries[0]) as src, partial.open("wb") as out:
                    shutil.copyfileobj(src,out)
            partial.replace(target)
            target.with_suffix(".source.json").write_text(json.dumps({"url":url,
                "sha256":hashlib.sha256(target.read_bytes()).hexdigest()},indent=2),encoding="utf-8")
        finally:
            archive.unlink(missing_ok=True)
            partial.unlink(missing_ok=True)
    return directory


def coco_to_landmarks(keypoints,scores,width,height):
    """Map COCO17 to sparse MediaPipe33 slots; unused points have zero confidence.

    RTMPose SimCC scores are not calibrated visibility probabilities.
    """
    mapping={0:0,1:2,2:5,3:7,4:8,5:11,6:12,7:13,8:14,9:15,10:16,
             11:23,12:24,13:25,14:26,15:27,16:28}
    points=[{"x":0.,"y":0.,"visibility":0.,"presence":0.} for _ in range(33)]
    for src,dst in mapping.items():
        points[dst]={"x":float(keypoints[src][0])/width,"y":float(keypoints[src][1])/height,
                     "visibility":float(scores[src]),"presence":float(scores[src])}
    return points


class RTMPoseModel:
    def __init__(self,directory,roi_mode="detected"):
        from rtmlib import YOLOX, RTMPose
        import onnxruntime as ort
        directory=Path(directory)
        if roi_mode not in ("detected","full-frame","locked"):
            raise ValueError("Unknown ROI mode")
        self.roi_mode=roi_mode
        for name in required_rtm_assets(roi_mode):
            if not (directory/name).exists():
                raise FileNotFoundError("RTMPose models missing: use --backend rtmpose --download-model")
        detector_name='detector_m.onnx' if roi_mode=='locked' else 'detector.onnx'
        detector_size=(640,640) if roi_mode=='locked' else (416,416)
        self.detector=YOLOX(str(directory/detector_name),model_input_size=detector_size,
                            backend="onnxruntime",device="cpu") if roi_mode in ("detected","locked") else None
        if roi_mode=="locked":
            from .subject import SubjectLock
            self.subject=SubjectLock()
        self.pose=RTMPose(str(directory/"pose.onnx"),model_input_size=(192,256),
                          backend="onnxruntime",device="cpu",to_openpose=False)
        # Avoid two inference sessions each occupying all CPU cores.
        opts=ort.SessionOptions()
        opts.intra_op_num_threads=4
        opts.inter_op_num_threads=1
        for obj in (self.detector,self.pose):
            if obj is None:
                continue
            obj.session=ort.InferenceSession(obj.onnx_model,sess_options=opts,providers=["CPUExecutionProvider"])

    def detect(self,rgb,timestamp_s):
        import numpy as np
        bgr=np.ascontiguousarray(rgb[:,:,::-1])
        if self.roi_mode=="full-frame":
            boxes=[[0,0,rgb.shape[1],rgb.shape[0]]]
            status="assumed_single_person_roi"
        else:
            boxes=self.detector(bgr)
            if self.roi_mode=="locked":
                from .subject import appearance
                boxes=[] if boxes is None else boxes
                extract_appearance=getattr(self,'appearance_extractor',appearance)
                idx,status=self.subject.update(boxes,[extract_appearance(bgr,b) for b in boxes],timestamp_s)
                if idx is None:return [],status
                boxes=[boxes[idx]]
            else:
                status="single_person"
            if boxes is None or len(boxes)==0:
                return [],"no_person"
            if len(boxes)>1:
                return [],"multiple_people"
        keypoints,scores=self.pose(bgr,bboxes=boxes)
        return coco_to_landmarks(keypoints[0],scores[0],rgb.shape[1],rgb.shape[0]),status

    def close(self):
        self.detector=None
        self.pose=None
