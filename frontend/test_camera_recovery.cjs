const fs=require('fs'),vm=require('vm'),assert=require('assert');
const src=fs.readFileSync('app.js','utf8'),nodes=new Map(),handlers={};let stopped=0,cleared=0,request;
const context={clearRect(){cleared++}};
const c={VISION_MODE:"local",selectBrowserSubject:async(x,y)=>{request={body:{x,y}}},surfaceSelection:null,cameraRequestGeneration:2,trainingRunning:true,trainingTimer:1,visionSessionId:'old',trainingOwner:{},lastVisionResult:{subject:{status:'select_subject'}},previewFlipped:true,cameraStream:{getTracks:()=>[{stop(){stopped++}}]},clearTimeout(){},finishTrainingVideo:()=>Promise.resolve(),
 $:id=>{if(!nodes.has(id))nodes.set(id,{style:{},setAttribute(){},classList:{remove(){}},getContext:()=>context,addEventListener:(name,fn)=>handlers[id+name]=fn});return nodes.get(id)},
 visionApi:async(path,body)=>{request={path,body}},showToast(){}};
vm.createContext(c);vm.runInContext(src.slice(src.indexOf('function expireVisionSession('),src.indexOf('$("#flip-preview").addEventListener')),c);
const start=src.indexOf('// Selection uses');vm.runInContext(src.slice(start,src.indexOf('$("#reselect-subject")',start)),c);
(async()=>{
 const canvas={width:960,height:540,getBoundingClientRect:()=>({left:0,top:0,width:960,height:640})};
 await handlers['#pose-overlayclick']({currentTarget:canvas,clientX:100,clientY:150});assert.equal(request.body.x,860);assert.equal(request.body.y,100);
 c.previewFlipped=false;await handlers['#pose-overlayclick']({currentTarget:canvas,clientX:100,clientY:150});assert.equal(request.body.x,100);
 c.VISION_MODE="browser";await handlers['#pose-overlayclick']({currentTarget:canvas,clientX:100,clientY:150});assert.equal(request.body.x,100/960);assert.equal(request.body.y,100/540);
 c.expireVisionSession();assert.equal(c.trainingRunning,false);assert.equal(c.visionSessionId,null);assert.equal(stopped,1);assert.equal(c.cameraRequestGeneration,3);assert.equal(nodes.get('#start-training').textContent,'重新开始识别');
 assert(src.includes('error.status===404){expireVisionSession();return}'));
 console.log('PASS: mirrored/unmirrored letterbox click coordinates and expired-session stop/restart state');
})().catch(e=>{console.error(e);process.exit(1)});

