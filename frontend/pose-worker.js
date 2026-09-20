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
    // 认到第二个人就够判断"画面里不止一个人"，规则层据此暂停计数。
    numPoses: 2,
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
      const first = poses[0] || [];
      // 规则层要求恰好 33 个点，缺就整帧作废，不要送半截数据。
      const landmarks = first.length === 33 ? first.map((p) => ({
        x: p.x,
        y: p.y,
        // JS 版 NormalizedLandmark 没有 presence；规则层用 min(visibility, presence)
        // 做阈值，这里补齐成同一个值，保持与服务端一致的判定语义。
        visibility: typeof p.visibility === "number" ? p.visibility : 0,
        presence: typeof p.visibility === "number" ? p.visibility : 0,
      })) : null;
      self.postMessage({
        type: "result",
        id: msg.id,
        landmarks,
        pose_status: landmarks ? toPoseStatus(poses.length) : "no_person",
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
