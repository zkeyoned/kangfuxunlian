const assert=require('assert'),fs=require('fs'),vm=require('vm');
const FrameQueue=require('./frame-queue.js');
const source=fs.readFileSync('app.js','utf8');
const pixels={},timers=[],nodes=new Map();let sent,displayed,stopped=false;
const c={window:{},lastVisionResult:null,FrameQueue, cameraRequestGeneration:1,visionSessionId:'session',trainingRunning:true,
 VISION_BASE:'/vision/api/live',captureStart:0,performance:{now:()=>1000},
 visionHeaders:h=>({...h,Authorization:'Bearer test'}),AbortSignal,
 fetch:async(url,options)=>{sent=JSON.parse(options.body).frames;assert.equal(options.headers.Authorization,'Bearer test');return {ok:true,json:async()=>({frame_id:sent[0].frame_id,timestamp_s:sent[0].timestamp_s,value:170})}},
 Image:class{set src(v){this.naturalWidth=640;this.naturalHeight=480;pixels.decoded=v;this.onload()}},
 captureCanvas:{getContext:()=>({drawImage:()=>{pixels.painted=true}})},
 document:{createElement:()=>({getContext:()=>({drawImage(){}}),toDataURL:()=> 'data:image/jpeg;base64,fixture'})},
 $:selector=>selector==='#training-video'?{readyState:2,videoWidth:640,videoHeight:480}:(nodes.has(selector)?nodes.get(selector):(nodes.set(selector,{querySelectorAll:()=>[],getContext:()=>({clearRect(){pixels.cleared=true}})}),nodes.get(selector))),
 updateLiveResult:r=>{assert(pixels.painted,'paint corresponding image before metrics');displayed=r},
 setTimeout:(fn,ms)=>{timers.push({fn,ms});return timers.length},clearTimeout(){},showToast(){},stopLiveTraining(){stopped=true}
};
vm.createContext(c);vm.runInContext(source.slice(source.indexOf('// Remote RTMPose:')),c);
(async()=>{
 c.startRemoteFrames();assert(vm.runInContext('remoteFrames.options.live',c));await vm.runInContext('remoteFrames.drain()',c);
 assert.equal(displayed.frame_id,sent[0].frame_id);assert.equal(displayed.timestamp_s,sent[0].timestamp_s);
 assert.equal(pixels.decoded,'data:image/jpeg;base64,fixture');assert(!stopped);
 // Even if a request never answers, the watchdog releases frozen preview.
 c.performance.now=()=>2700;timers.find(t=>t.ms===250).fn();assert(pixels.cleared);assert.equal(nodes.get('.camera-state').textContent,'实时预览 · 识别结果延迟');
 c.performance.now=()=>1000;
 // A stale response must clear the old overlay and never update metrics.
 displayed=null;c.fetch=async(url,options)=>{const batch=JSON.parse(options.body).frames;c.performance.now=()=>4000;return{ok:true,json:async()=>({...batch[0]})}};
 c.startRemoteFrames();await vm.runInContext('remoteFrames.drain()',c);assert.equal(displayed,null);
 c.fetch=async()=>({ok:true,json:async()=>({frame_id:999,timestamp_s:1})});
 c.startRemoteFrames();await vm.runInContext('remoteFrames.drain()',c);
 assert(vm.runInContext('Boolean(remoteFrames.failed)',c),'mismatched image must reject result');
 console.log('PASS authenticated remote frames, matched image before metrics, mismatched frame rejected');
})().catch(e=>{console.error(e);process.exit(1)});
