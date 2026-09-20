const fs=require('fs'),vm=require('vm'),assert=require('assert');
const src=fs.readFileSync('app.js','utf8'),html=fs.readFileSync('index.html','utf8');
const nodes=new Map(),storage=new Map();
let fail=false,calls=[];
const result={brief_report:{version:'1',exercise:'坐姿伸膝',side:'左腿',completed_reps:0,target_reps:10,sets:[{set:1,completed_reps:0,target_reps:10,angle_hold_met_reps:0,finding:'未识别动作',status:'未完成'}],suggestions:[],scope:'训练辅助'},training_session:{plan:{hold_s:3}},repetitions:[],feedback_events:[],_sync:{clientId:'session-1',exerciseId:'seated',userId:7,status:'pending'}};
const row={id:4,client_id:'session-1',exercise_id:'seated',created_at:'2026-09-20 01:00:00',patient_name:'<script>x</script>',brief_report:result.brief_report,result:{...result},delivery:{status:'available',therapist_name:'康复师',read_at:null}};
const c={currentUser:{id:7,role:'patient'},reportsLoading:false,reportsReloadRequested:false,reportPatientFilter:null,uploadTrainingVideo:async()=>{},videoReportButton:()=>"无录像",feedbackReports:{},lastTrainingReport:result,exercises:[{id:'seated'}],
 $:id=>{assert(html.includes(`id="${id.slice(1)}"`),id);if(!nodes.has(id))nodes.set(id,{});return nodes.get(id)},sessionStorage:{getItem:k=>storage.get(k),setItem:(k,v)=>storage.set(k,v)},
 api:async(path,opt)=>{calls.push([path,opt]);if(fail)throw Error('离线');return path==='/training-reports'&&!opt?{reports:[row]}:row},
 showToast(){},renderFeedback(){},showTrainingReport(){},feedbackStorageKey:id=>`feedback:${id}`,buildFeedbackRecord:()=>({brief:result.brief_report,metrics:[]}),escapeHtml:s=>String(s).replaceAll('<','&lt;').replaceAll('>','&gt;')};
vm.createContext(c);vm.runInContext(src.slice(src.indexOf('function pendingReportKey('),src.indexOf('document.addEventListener("click",event=>{',src.indexOf('function pendingReportKey('))),c);
(async()=>{
 fail=true;await c.saveTrainingReport(result);assert.equal(result._sync.status,'failed');assert(c.reportDeliveryText(result).includes('尚未保存'));assert(c.pendingReports(7)['session-1']);
 fail=false;await c.saveTrainingReport(result);assert.equal(result._sync.status,'saved');assert.equal(Object.keys(c.pendingReports(7)).length,0);assert.equal(c.feedbackReports.seated.serverId,4);assert(c.reportDeliveryText(result).includes('尚未查看'));
 const body=calls.find(([p,o])=>o?.method==='POST')[1].body;assert(!('_sync' in body.result));assert.equal(body.client_id,'session-1');assert.equal(body.result.brief_report.completed_reps,0);
 assert(nodes.get('#patient-report-list').innerHTML.includes('&lt;script&gt;'));
 c.currentUser={id:8,role:'therapist'};await c.loadServerReports();assert.equal(nodes.get('#report-unread-count').textContent,1);await c.openSavedReport(4);assert(calls.some(([p])=>p==='/training-reports/4/read'));
 const before=calls.length;await c.saveTrainingReport(result);assert.equal(calls.length,before);
 const unlinked={_sync:{status:'saved',delivery:{status:'unlinked'}}};assert(c.reportDeliveryText(unlinked).includes('尚未关联'));
 console.log('PASS: sync failure/retry, account persistence, real zero result, therapist inbox/read, escaping and owner guard');
})().catch(e=>{console.error(e);process.exit(1)});
