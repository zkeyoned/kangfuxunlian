const assert=require('assert'),fs=require('fs'),vm=require('vm');
const src=fs.readFileSync('app.js','utf8');
let resets=0,selected=0;
const c={browserSelectionBusy:false,browserLockEpoch:0,LANDMARK_QUEUE:[1,2],cameraRequestGeneration:1,visionSessionId:'test',uploadBusy:true,
 setTimeout(fn){c.uploadBusy=false;fn()},visionApi:async()=>{assert(!c.uploadBusy);resets++},
 browserLock:{select(){selected++;return true},reset(){}},performance:{now:()=>3000},captureStart:0,showToast(){}};
vm.createContext(c);vm.runInContext(src.slice(src.indexOf('async function selectBrowserSubject(')),c);
(async()=>{
 await c.selectBrowserSubject(.3,.4);
 assert.equal(resets,1);assert.equal(selected,1);assert.equal(c.LANDMARK_QUEUE.length,0);assert.equal(c.browserLockEpoch,1);assert(!c.browserSelectionBusy);
 c.visionApi=async()=>{throw Error('offline')};
 await assert.rejects(()=>c.selectBrowserSubject(.2,.3));assert.equal(selected,1,'failed baseline reset must not change identity');assert(!c.browserSelectionBusy);
 console.log('PASS subject reselection drains upload, clears queue, invalidates in-flight detections, and preserves identity on reset failure');
})().catch(e=>{console.error(e);process.exit(1)});
