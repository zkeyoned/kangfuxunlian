const fs=require('fs'),vm=require('vm'),assert=require('assert');
const src=fs.readFileSync('app.js','utf8'),html=fs.readFileSync('index.html','utf8');
const nodes=new Map();
const $=id=>{assert(html.includes(`id="${id.slice(1)}"`),`missing ${id}`);if(!nodes.has(id))nodes.set(id,{open:false,showModal(){this.open=true}});return nodes.get(id)};
const start=src.indexOf('function showTrainingReport('),end=src.indexOf('$("#close-training-report")',start);
const escape=src.split(/\r?\n/).find(x=>x.startsWith('function escapeHtml('));
const c={$ ,showToast(){},currentUser:{role:'patient'},buildFeedbackRecord:()=>({metrics:[]}),reportDeliveryText:()=>"已保存"};vm.createContext(c);vm.runInContext(escape+'\n'+src.slice(start,end),c);
c.showTrainingReport({brief_report:{exercise:'坐姿伸膝',side:'右腿',completed_reps:1,target_reps:10,sets:[{set:1,status:'记录未完成',completed_reps:1,target_reps:10,angle_hold_met_reps:0,needs_review_reps:1,finding:'<img onerror=alert(1)>'}],suggestions:['缓慢放回'],scope:'训练辅助',delivery:'未发送'}});
assert($('#training-report-dialog').open);assert($('#report-sets').innerHTML.includes('&lt;img'));assert(!$('#report-sets').innerHTML.includes('<img'));assert($('#report-overview').textContent.includes('1 / 计划 10'));
console.log('Report rendering, element wiring and escaping passed');

c.fmt=(n,d=1)=>Number.isFinite(n)?n.toFixed(d):"--";
c.showTrainingReport({rule_version:"squat_v0.1_joint",training_session:{rule_version:"squat_v0.1_joint"},repetitions:[{index:1,goal_met:false,knee_flexion_peak_deg:50,target_hold_s:1.2,rise_s:2,hip_drop_peak:.035,depth_exceeded:true}],brief_report:{exercise:"扶椅微蹲",side:"左腿",completed_reps:1,target_reps:3,attempted_reps:1,goal_reps:0,incomplete_attempts:0,unable_to_evaluate:0,sets:[],suggestions:[],scope:"训练辅助"}});
assert($('#report-sets').innerHTML.includes('次微蹲'));
assert(!$('#report-sets').innerHTML.includes('次坐站'));
assert($('#report-sets').innerHTML.includes('50.0'));
assert($('#report-sets').innerHTML.includes('0.035'));
assert($('#report-sets').innerHTML.includes('本次保留记录'));
console.log('PASS squat real-metric report rendering and independent goal state');
