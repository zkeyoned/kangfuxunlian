const fs=require('fs'),vm=require('vm'),assert=require('assert');
async function run(path){
 const src=fs.readFileSync(path,'utf8');let fetches=0,updates=0,resizes=0,release;
 const canvas={_w:960,_h:540,get width(){return this._w},set width(v){resizes++;this._w=v},get height(){return this._h},set height(v){resizes++;this._h=v},getContext:()=>({drawImage(){},clearRect(){}})};
 const state={},c={window:{},performance:{now:()=>100},trainingRunning:true,frameBusy:false,cameraRequestGeneration:1,visionSessionId:'test',captureStart:0,captureCanvas:canvas,VISION_BASE:'/vision',AbortSignal:{timeout:()=>null},visionHeaders:h=>h,FrameEncoder:class{encode(){return new Promise(r=>release=r)}},$:s=>s==='#training-video'?{readyState:2,videoWidth:960,videoHeight:540}:s==='#pose-overlay'?canvas:state,fetch:async()=>{fetches++;return{ok:true,json:async()=>({backend:'rtmpose',processing_ms:20})}},updateLiveResult(){updates++},setTimeout(){},stopLiveTraining(){},expireVisionSession(){}};
 vm.createContext(c);vm.runInContext(src.slice(src.indexOf('let localEncoder=null;'),src.indexOf('\nlet surfaceSelection=')),c);
 const first=c.sendCameraFrame();await c.sendCameraFrame();release('jpeg');await first;assert.equal(fetches,1);assert.equal(updates,1);assert.equal(resizes,0);assert.equal(c.window.__posePerformance.length,1);
 const stopped=c.sendCameraFrame();c.cameraRequestGeneration++;release('jpeg');await stopped;assert.equal(fetches,1);assert.equal(updates,1);
 console.log('PASS local capture: one request, no redundant resize, timing, stopped-session discard: '+path);
}
(async()=>{await run('app.js');if(process.argv[2])await run(process.argv[2])})().catch(e=>{console.error(e);process.exit(1)});
