/* 浏览器端姿态识别 worker。
 *
 * 只做一件事：把一帧画面变成 33 个关键点。动作判定、计次、评分仍然全部由
 * 服务端的规则层负责（algorithm/rehab-pose-demo/rehab_pose/），这里不做任何判断。
 *
 * 放在 worker 里是因为 detectForVideo 是同步阻塞调用，跑在主线程会让画面卡住。
 *
 * 用的模型文件与服务端 backend="mediapipe" 完全相同（pose_landmarker_full.task，
 * sha256 5134a3aa…），所以关键点口径与服务端一致。
 */
// 这里用的是经典 worker + importScripts，不是 module worker。
// 原因：MediaPipe 内部要用 importScripts 去加载 wasm 胶水层，而 module worker
// 里没有这个函数，会直接报 "ModuleFactory not set"。官方为此单独发了 IIFE 版本
// vision_bundle.js（挂全局 Vision），这里用的就是它。
//
// 路径一律用绝对 URL：MediaPipe 按 bundle 自身所在目录解析相对路径，
// 传 "./vendor/..." 会被拼成 /vendor/mediapipe/vendor/mediapipe/... 而 404。
const ASSET_ROOT = new URL("./vendor/mediapipe/", self.location.href).href;
importScripts(ASSET_ROOT + "vision_bundle.js");
const { FilesetResolver, PoseLandmarker } = Vision;

let landmarker = null;
let lastTimestampMs = 0;

async function init() {
  const fileset = await FilesetResolver.forVisionTasks(ASSET_ROOT + "wasm");
  landmarker = await PoseLandmarker.createFromOptions(fileset, {
    baseOptions: {
      modelAssetPath: ASSET_ROOT + "pose_landmarker_full.task",
      // 浏览器端 GPU delegate 没有官方兼容性承诺，先一律用 CPU 保稳。
      delegate: "CPU",
    },
    runningMode: "VIDEO",
    // 最多四个候选，身份由浏览器锁定器确定，不取输出顺序。
    numPoses: 4,
  });
}

function toPoseStatus(count) {
  if (count === 0) return "no_person";
  if (count > 1) return "multiple_people";
  return "single_person";
}

self.onmessage = async (event) => {
  const msg = event.data || {};

  if (msg.type === "init") {
    try {
      await init();
      self.postMessage({ type: "ready" });
    } catch (error) {
      self.postMessage({ type: "error", message: String(error && error.message || error) });
    }
    return;
  }

  if (msg.type === "frame") {
    const bitmap = msg.bitmap;
    if (!landmarker) {
      if (bitmap) bitmap.close();
      self.postMessage({ type: "result", id: msg.id, error: "识别模型尚未就绪" });
      return;
    }
    try {
      // MediaPipe 要求时间戳严格递增，和服务端 model.py 的处理方式保持一致。
      const stamp = Math.max(lastTimestampMs + 1, Math.round(msg.timestamp_s * 1000));
      lastTimestampMs = stamp;
      const output = landmarker.detectForVideo(bitmap, stamp);
      const poses = output.landmarks || [];
      const canvas=new OffscreenCanvas(160,120),ctx=canvas.getContext("2d",{willReadFrequently:true});
      ctx.drawImage(bitmap,0,0,160,120);
      const pixels=ctx.getImageData(0,0,160,120).data;
      const candidates=poses.filter(p=>p.length===33).map(pose=>{
        const landmarks=pose.map(p=>({x:p.x,y:p.y,visibility:p.visibility||0,presence:p.visibility||0}));
        const hist=new Array(64).fill(0);let count=0;
        // Sample an inset shoulder/hip quadrilateral, avoiding background at its edges.
        const [ls,rs,lh,rh]=[11,12,23,24].map(i=>pose[i]);
        for(let v=.2;v<=.8;v+=.1)for(let u=.2;u<=.8;u+=.1){
          const x=(1-v)*((1-u)*ls.x+u*rs.x)+v*((1-u)*lh.x+u*rh.x);
          const y=(1-v)*((1-u)*ls.y+u*rs.y)+v*((1-u)*lh.y+u*rh.y);
          if(x<0||y<0||x>=1||y>=1)continue;
          const i=(Math.floor(y*120)*160+Math.floor(x*160))*4;
          hist[(pixels[i]>>6)*16+(pixels[i+1]>>6)*4+(pixels[i+2]>>6)]++;count++;
        }
        return {landmarks,appearance:count?hist.map(x=>x/count):null};
      });
      self.postMessage({
        type: "result",
        id: msg.id,
        candidates,
        width: msg.width,
        height: msg.height,
        timestamp_s: msg.timestamp_s,
      });
    } catch (error) {
      self.postMessage({ type: "result", id: msg.id, error: String(error && error.message || error) });
    } finally {
      if (bitmap) bitmap.close();
    }
  }
};
