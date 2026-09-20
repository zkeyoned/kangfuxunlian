const fs=require('fs'),vm=require('vm'),assert=require('assert'),{webcrypto}=require('crypto');
const src=fs.readFileSync('app.js','utf8'),nodes=new Map(),stored=new Map();let requests=[],fail=true;
class Recorder{static isTypeSupported(){return true}constructor(){this.state='inactive';this.mimeType='video/webm'}start(){this.state='recording'}stop(){this.state='inactive';this.ondataavailable({data:new Blob([new Uint8Array([26,69,223,163,...Array(30).fill(0)])],{type:'video/webm'})});this.onstop()}}
const c={Blob,MediaRecorder:Recorder,crypto:webcrypto,performance:{now:()=>1000},currentUser:{id:7,role:'patient'},trainingRecorder:null,pendingVideoFiles:new Map(),videoUploads:new Set(),cameraStream:{},previewFlipped:true,trainingRunning:false,lastTrainingReport:null,
 $:id=>{if(!nodes.has(id))nodes.set(id,{});return nodes.get(id)},showToast(){},escapeHtml:String,
 api:async(path,opt)=>{requests.push(path);return {state:path.endsWith('complete')?'ready':'uploading',chunk_size:1048576,chunk_count:1}},
 fetch:async()=>{if(fail)return {ok:false,status:502,json:async()=>({error:'网络中断'})};return {ok:true}},apiToken:'test',API_BASE:'http://test',AbortSignal};
vm.createContext(c);const start=src.indexOf('function videoKey(');vm.runInContext(src.slice(start,src.indexOf('document.addEventListener("click",async event=>{',start)),c);
c.videoStore=async(action,key,value)=>{if(action==='put')stored.set(key,value);if(action==='delete')stored.delete(key);if(action==='getAll')return [...stored.values()]};
(async()=>{
 c.startTrainingVideo({userId:7,clientId:'session-video',exerciseId:'seated'});await c.finishTrainingVideo();assert.equal(c.pendingVideoFiles.size,1);assert.equal(stored.size,1);
 const row={id:4,client_id:'session-video'};
 await c.uploadTrainingVideo(row);assert.equal(stored.size,1);assert(nodes.get('#report-video-actions').innerHTML.includes('未完成上传'));
 fail=false;await c.uploadTrainingVideo(row);assert.equal(stored.size,0);assert.equal(row.video.state,'ready');assert(c.videoReportButton(row).includes('查看视频'));assert(!c.videoReportButton({id:5}).includes('data-play-training-video'));
 assert(src.includes('data-patient-reports="${p.id}"'));assert(src.includes('?patient_id=${selectedPatient.id}'));
 console.log('PASS: recording final chunk persisted, failed upload retained, retry completes/deletes queue, real-video button and patient routing');
})().catch(e=>{console.error(e);process.exit(1)});
