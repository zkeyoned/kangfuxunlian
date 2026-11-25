const exercises = [
  {
    id: "seated", name: "坐姿伸膝", short: "坐姿伸膝", image: "assets/seated-knee-extension-v2.jpg", dose: "2 组 × 10 次", done: false,
    flow: "坐稳 → 缓慢伸直患侧膝关节 → 保持 → 缓慢放下",
    focus: ["完成次数", "最大伸膝角度", "顶点保持", "抬起与下放速度"],
    hero: ["还差 7° 完全伸直", "第 8 次动作在顶点停留不足，下一次伸直后多保持 1.6 秒。"],
    note: "先把腿完全伸直，再开始计时。下放时心里默数两秒，避免突然落下。",
    metrics: [
      ["完成次数", "10 次", "目标 10 次", "已完成", "good"],
      ["最大伸膝角度", "168°", "目标 ≥ 175°", "还差 7°", "warn"],
      ["顶点保持时间", "1.4 秒", "目标 3 秒", "需增加 1.6 秒", "warn"],
      ["平均下放时间", "0.9 秒", "目标 1.5 至 2.5 秒", "下放过快", "warn"]
    ],
    live: [["膝伸展", "168", "°"], ["顶点保持", "1.4", "秒"], ["本组次数", "8", "/ 10"], ["下放时间", "0.9", "秒"]],
    cues: [["伸展", "再伸直一点", "膝关节还差约 7° 达到目标"], ["保持", "保持住，继续 1.6 秒", "计时从达到目标角度后开始"], ["回落", "慢一点放下", "控制下放约 2 秒，不要突然落下"]],
    rules: [["次数",10,"次"],["伸膝角度",175,"° 以上"],["顶点保持",1,"秒"],["下放时间",2,"秒"]]
  },
  {
    id: "supine", name: "卧姿直腿抬高", short: "仰卧抬腿", image: "assets/supine-leg-raise-v2.jpg", dose: "2 组 × 8 次", done: false,
    flow: "仰卧固定相机 → 膝关节保持伸直 → 抬腿 → 保持 → 控制下放",
    focus: ["抬腿次数", "髋关节抬升角度", "膝关节伸直", "顶点保持", "下放速度"],
    hero: ["抬腿角度达标，膝盖需再伸直", "第 6 次膝关节弯曲 8°，请先收紧大腿再抬起。"],
    note: "建议从身体侧面拍摄，避免被子或宽松衣物遮挡髋、膝关键点。",
    metrics: [["抬腿次数","8 次","目标 8 次","已完成","good"],["髋关节抬升角度","28°","目标 25° 至 35°","范围内","good"],["膝关节屈曲","8°","目标 ≤ 5°","需再伸直","warn"],["顶点保持时间","2.1 秒","目标 3 秒","不足 0.9 秒","warn"],["平均下放时间","1.1 秒","目标 ≥ 1.5 秒","下放偏快","warn"]],
    live: [["髋抬升", "28", "°"], ["膝屈曲", "8", "°"], ["顶点保持", "2.1", "秒"], ["本组次数", "6", "/ 8"]],
    cues: [["抬起","膝盖再伸直一点","检测到膝屈曲约 8°"],["保持","稳定保持 0.9 秒","抬腿角度已经达标"],["回落","控制住，不要落太快","保持膝盖伸直并缓慢回落"]],
    rules: [["次数",8,"次"],["髋抬升角度",30,"°"],["膝屈曲上限",5,"°"],["顶点保持",3,"秒"],["下放时间",2,"秒"]]
  },
  {
    id: "squat", name: "扶椅子膝盖微蹲", short: "扶椅微蹲", image: "assets/chair-mini-squat-v2.jpg", dose: "2 组 × 10 次", done: false,
    flow: "扶稳椅背 → 屈髋屈膝下蹲 → 膝盖对准脚尖 → 回到站立",
    focus: ["完成次数", "屈膝深度", "膝与脚尖对线", "躯干角度", "左右对称", "动作速度"],
    hero: ["深度合适，右膝有内扣趋势", "第 7 次右膝向内偏移约 6°，下蹲时让膝盖朝第二脚趾方向。"],
    note: "扶稳椅子，膝盖朝脚尖方向移动。膝屈曲不要超过 90°，按能力逐渐增加深度。",
    metrics: [["完成次数","10 次","目标 ≥ 10 次","已完成","good"],["最大屈膝角度","42°","目标 35° 至 60°","范围内","good"],["膝内扣偏移","6°","目标 ≤ 3°","右膝向外调整","warn"],["躯干前倾","12°","目标 ≤ 20°","控制良好","good"],["左右负重偏移","8%","目标 ≤ 5%","稍偏左侧","warn"]],
    live: [["屈膝深度", "42", "°"], ["右膝偏移", "6", "°"], ["躯干前倾", "12", "°"], ["本组次数", "7", "/ 10"]],
    cues: [["下蹲","右膝向外调整","让膝盖对准第二脚趾"],["底点","深度合适，保持稳定","当前屈膝 42°，未超过限制"],["站起","两侧均匀用力","重心稍微偏向左侧"]],
    rules: [["次数",10,"次"],["屈膝深度",45,"°"],["屈膝上限",90,"°"],["膝内扣上限",3,"°"],["左右偏移上限",5,"%"]]
  },
  {
    id: "stand", name: "坐站训练", short: "坐站训练", image: "assets/sit-to-stand-v2.jpg", dose: "2 组 × 8 次", done: false,
    flow: "坐姿 → 身体前倾 → 离开椅子 → 完全站立 → 缓慢坐下",
    focus: ["完成次数", "是否完全站直", "坐站用时", "躯干前倾", "左右偏移", "手臂借力"],
    hero: ["站立完整，起身时身体偏向左侧", "第 5 次重心左移 4 cm，双脚均匀踩地后再起身。"],
    note: "双脚与肩同宽，身体前倾后发力站起。尽量不借助手臂，坐下时保持控制。",
    metrics: [["完成次数","8 次","目标 8 次","已完成","good"],["完全站直","7 / 8 次","目标每次站直","1 次不足","warn"],["平均坐站用时","2.7 秒","目标 2.5 至 4 秒","范围内","good"],["躯干最大前倾","31°","目标 25° 至 40°","范围内","good"],["左右偏移","4 cm","目标 ≤ 2 cm","向左偏移","warn"],["手臂借力","1 次","目标 0 次","减少借力","warn"]],
    live: [["站起用时", "2.7", "秒"], ["躯干前倾", "31", "°"], ["左右偏移", "4", "cm"], ["本组次数", "5", "/ 8"]],
    cues: [["前倾","很好，保持双脚均匀受力","躯干前倾角度合适"],["站起","重心向右调整一点","检测到身体向左偏移 4 cm"],["站立","把身体完全站直","髋关节还差约 6° 完全伸展"]],
    rules: [["次数",8,"次"],["坐站用时",3,"秒"],["前倾角度",35,"°"],["左右偏移上限",2,"cm"],["手臂借力",0,"次"]]
  }
];

exercises.find(e=>e.id==="supine").note="仰卧，非训练腿屈膝支撑，训练腿舒适伸直。先标定床沿朝脚方向，再放平保持2秒。缓慢抬到目标范围，膝盖保持伸直后连续保持5秒，再缓慢放下；抬起、放下各约2–3秒。不能舒适完成时暂停，不强行伸直。";
exercises.find(e=>e.id==="supine").flow="侧面拍摄并标定床面 → 仰卧、另一腿屈膝 → 训练腿伸直抬起 → 联合保持 → 缓慢放下";
exercises.find(e=>e.id==="stand").note="双脚踩稳，上身稍向前，慢慢站起来；站稳后把臀部往后送，慢慢坐回。起立前倾是正常过程。按所选辅助方式完成，不为计次强行站直。先坐稳标定，再舒适站稳标定并人工确认，最后坐回开始。";
Object.assign(exercises.find(e=>e.id==="squat"),{flow:"双手扶稳 → 缓慢屈膝下蹲 → 短暂停留 → 慢慢站回",note:"固定水平侧面拍摄，让肩、髋、膝、踝可见。双手扶稳椅背或固定台面，双脚约髋宽；先舒适站稳2秒。慢慢下蹲至设定目标附近，允许正常前倾，不追求蹲得更深。短暂停留后慢慢站回。"});
let patientTrainingSource="empty",selfTrainingSelection=null,selfSelectionSignature=null;
let visualPlan=null,visualPlanUser=null,activePrescriptionSnapshot=null,planLoadGeneration=0;
function defaultTargets(id){return {target_deg:{seated:170,supine:30,squat:30,stand:165}[id],hold_s:{seated:1,supine:5,squat:1,stand:1}[id],return_s:1,rest_s:30}}
function availableExercises(){return exercises.filter(ex=>patientTrainingSource!=="empty"&&ex.planSelected)}
function targetDescription(ex){const t=ex.targets||defaultTargets(ex.id);if(ex.id==="squat")return `膝屈曲目标 ${t.target_deg}°，进入±5°、维持±8°，髋部需同时下降；${t.hold_s===0?"不停顿模式":`连续保持${t.hold_s}秒`}；缓慢蹲下与站回；先确认支撑、舒适站立标定2秒`;if(ex.id==="stand")return `膝夹角≥${t.target_deg}°、髋上升≥90%、距站姿躯干基线≤10°联合确认；连续站稳${t.hold_s}秒，坐回后计完整次数；须坐姿/站姿双标定`;if(ex.id==="supine")return `床面抬腿目标 ${t.target_deg}°；进入±5°且膝屈曲≤10°，维持±8°且膝屈曲≤15°；联合保持 ${t.hold_s}秒；抬起/放下约2–3秒（提示下限1秒）；参考线需标定`;const label={seated:"膝夹角",supine:"床面抬腿角",squat:"膝屈曲角",stand:"站直膝夹角"}[ex.id];return `${label} ≥ ${t.target_deg}°；保持 ≥ ${t.hold_s}秒；返回 ≥ ${t.return_s}秒；组间休息 ${t.rest_s}秒`}
function renderPlanEditor(){
 const labels={seated:"伸膝夹角",supine:"床面抬腿角",squat:"膝屈曲角",stand:"站直膝夹角"};
 $("#rule-editor").innerHTML=exercises.map((ex,i)=>{const t=defaultTargets(ex.id);const fields=[["sets","组数",["supine","squat","stand"].includes(ex.id)?1:2,"组",1,20],["reps","每组次数",["supine","squat","stand"].includes(ex.id)?3:10,"次",1,100],["target_deg",labels[ex.id],t.target_deg,"°",{seated:130,supine:20,squat:20,stand:130}[ex.id],{seated:180,supine:44,squat:80,stand:180}[ex.id]],["hold_s","连续保持下限",t.hold_s,"秒",0,30],["return_s","返回用时下限",t.return_s,"秒",0,20],["rest_s","组间休息",30,"秒",0,300]];return `<div class="rule-item ${i===0?"open":""}" data-rule="${ex.id}"><button class="rule-summary"><span>0${i+1}</span><b>${ex.name}</b><small>6 项设置</small><i>${i===0?"−":"+"}</i></button><div class="rule-fields">${fields.map(([key,label,value,unit,min,max])=>`<div class="rule-field"><label>${label}</label><div><input data-plan-field="${key}" type="number" min="${min}" max="${max}" step="${key==='sets'||key==='reps'?1:.1}" value="${value}"><span>${unit}</span></div></div>`).join("")}</div></div>`}).join("");
}
function populatePlanPatients(patients){
 const select=$("#plan-patient"),old=select.value;
 select.innerHTML=patients.length?patients.map(p=>`<option value="${p.id}">${escapeHtml(p.display_name)}</option>`).join(""):'<option value="">暂无已关联患者</option>';
 if(patients.some(p=>String(p.id)===old))select.value=old;
 loadPlanEditor();
}
async function loadPlanEditor(){
 const pid=$("#plan-patient").value,uid=currentUser?.id,generation=++planLoadGeneration;
 $("#condition-select").selectedIndex=0;$("#plan-side").selectedIndex=0;$("#plan-phase").selectedIndex=0;
 renderPlanEditor();$$(".picker-item").forEach(x=>{x.classList.add("selected");x.querySelector("button").textContent="✓"});$("#plan-notes").value="";$("#plan-days").value=5;$("#plan-daily").value=1;$("#plan-weeks").value=2;$("#plan-pain").value=5;
 $("#plan-summary-patient").textContent=$("#plan-patient").selectedOptions[0]?.textContent||"请选择患者";
 $("#publish-plan").disabled=$("#save-draft").disabled=true;
 if(!pid){$("#save-state").textContent="请先关联患者";return}
 try{const data=await api(`/patients/${pid}/visual-prescription`);if(generation!==planLoadGeneration||uid!==currentUser?.id)return;
 const p=data.draft||data.published;
 if(p){$("#condition-select").value=p.title;$("#plan-side").selectedIndex=p.side==="left"?1:0;$("#plan-phase").value=p.phase;$("#plan-days").value=p.days_per_week;$("#plan-daily").value=p.daily_sessions;$("#plan-weeks").value=p.duration_weeks;$("#plan-pain").value=p.pain_pause_score;$("#plan-notes").value=p.notes;
 $$(".picker-item").forEach(x=>{const item=p.items.find(i=>i.exercise_id===x.dataset.picker);x.classList.toggle("selected",!!item);x.querySelector("button").textContent=item?"✓":"+";if(item)$$(`[data-rule="${item.exercise_id}"] [data-plan-field]`).forEach(input=>input.value=item[input.dataset.planField])});}
 $("#save-state").textContent=p?(p.status==="draft"?"已加载草稿（未发布）":`已发布版本 ${p.id}`):"尚未发布方案";$("#publish-plan").disabled=$("#save-draft").disabled=false;renderSelectedSummary();
 }catch(e){$("#save-state").textContent="方案读取失败，请重新选择患者";showToast(e.message)}
}
function collectVisualPlan(status){
 const items=$$(".picker-item.selected").map(node=>{const item={exercise_id:node.dataset.picker};if(item.exercise_id==="supine")item.rule_version="slr_v0.1_surface";if(item.exercise_id==="squat")item.rule_version="squat_v0.1_joint";if(item.exercise_id==="stand")item.rule_version="sts_v0.1_dual_baseline";$$(`[data-rule="${item.exercise_id}"] [data-plan-field]`).forEach(input=>{if(!input.value||!input.checkValidity())throw Error("请检查组次及目标输入范围");item[input.dataset.planField]=Number(input.value)});return item});
 if(!items.length)throw Error("请至少选择一个动作");
 return {status,title:$("#condition-select").value,side:$("#plan-side").selectedIndex===1?"left":"right",phase:$("#plan-phase").value,days_per_week:Number($("#plan-days").value),daily_sessions:Number($("#plan-daily").value),duration_weeks:Number($("#plan-weeks").value),pain_pause_score:Number($("#plan-pain").value),notes:$("#plan-notes").value,items};
}
async function persistVisualPlan(status){
 const pid=$("#plan-patient").value;if(!pid){showToast("请先关联并选择患者");return}
 try{const body=collectVisualPlan(status);$("#publish-plan").disabled=$("#save-draft").disabled=true;
 const saved=await api(`/patients/${pid}/visual-prescription`,{method:"POST",body});$("#save-state").textContent=status==="draft"?"草稿已保存，患者不可见":`已发布版本 ${saved.id}`;showToast(status==="draft"?"草稿已保存":"已发布，患者空闲页面将在15秒内同步，下次训练生效");
 }catch(e){showToast(e.message);$("#save-state").textContent="保存失败，未发布"}finally{$("#publish-plan").disabled=$("#save-draft").disabled=false}
}
async function syncVisualPlan(){
 const uid=currentUser?.id;if(currentUser?.role!=="patient")return false;
 const data=await api("/me/visual-prescription");if(uid!==currentUser?.id)return false;
 const p=data.prescription;
 if(!p){await syncSelfSelection(uid);return true}
 if(visualPlanUser===uid&&visualPlan?.id===p.id)return true;
 visualPlan=p;visualPlanUser=uid;patientSide=p.side;patientTrainingSource="prescribed";selfSelectionSignature=null;
 exercises.forEach(ex=>{const item=p.items.find(i=>i.exercise_id===ex.id);ex.planSelected=!!item;delete ex.targets;if(item){ex.groups=ex.recommendedGroups=item.sets;ex.reps=ex.recommendedReps=item.reps;ex.dose=`${item.sets} 组 × ${item.reps} 次`;ex.targets=Object.fromEntries(['target_deg','hold_s','return_s','rest_s'].map(k=>[k,item[k]]));ex.done=false;ex.ruleVersion=item.rule_version||null}});
 renderExercises();$(".plan-stamp strong").textContent=`${p.title} · 版本 ${p.id}`;$(".plan-stamp small").textContent=`${p.side==='left'?'左腿':'右腿'} · ${p.phase} · 每周 ${p.days_per_week}天、每日${p.daily_sessions}次、${p.duration_weeks}周；疼痛达到${p.pain_pause_score}/10请暂停并联系康复师（需本人反馈） · ${p.notes||'暂无额外建议'}`;
 return true;
}

const $ = selector => document.querySelector(selector);
const $$ = selector => [...document.querySelectorAll(selector)];
const API_BASE = ["localhost","127.0.0.1","[::1]",""].includes(location.hostname)?"http://127.0.0.1:8801/api/v1":"/api/v1";
// local: 本机RTMPose；remote: 公网同源RTMPose（默认）；browser: MediaPipe仅显式对照。
//   local   —— 识别跑在用户自己电脑上的 Python 服务（8802），画面以 JPEG 上传。
//              需要先在本机装好并启动视觉服务，Safari 与手机用不了。
//   browser —— 识别跑在浏览器里，只把 33 个关键点发给服务端跑规则。
//              什么都不用装，手机和 Safari 都能用。
const VISION_LOCAL_BASE = "http://127.0.0.1:8802/api/live";
const VISION_REMOTE_BASE = "/vision/api/live";
const IS_LOCAL_HOST = ["localhost", "127.0.0.1", "[::1]", ""].includes(location.hostname);
const VISION_MODE = (() => {
  const forced = new URLSearchParams(location.search).get("vision");
  if (["local","browser","remote"].includes(forced)) return forced;
  return IS_LOCAL_HOST ? "local" : "remote";
})();
// 本机打开页面时，两种模式都直连 8802：本地没有 /vision 这条反向代理路由，
// 而且本地页面本身是 http，不存在 https 访问本机 http 的限制。
const VISION_BASE = (VISION_MODE === "local" || (IS_LOCAL_HOST&&VISION_MODE!=="remote")) ? VISION_LOCAL_BASE : VISION_REMOTE_BASE;
const EXERCISE_TO_VISION = {seated:"1",supine:"2",squat:"6",stand:"8"};
let apiToken = sessionStorage.getItem("kangshifu_api_token") || "";
let backendPlan = null;
let therapistPatients=[];
let patientSide = "left";

async function api(path, options={}){
  const headers={"Content-Type":"application/json",...(options.headers||{})};
  if(options.auth!==false&&apiToken)headers.Authorization=`Bearer ${apiToken}`;
  const response=await fetch(`${API_BASE}${path}`,{...options,headers,body:options.body&&typeof options.body!=="string"?JSON.stringify(options.body):options.body});
  const payload=await response.json().catch(()=>({detail:`HTTP ${response.status}`}));
  if(!response.ok){
    const detail=payload.error||payload.detail;
    const message=Array.isArray(detail)?"请检查输入内容：姓名不超过50字，密码为5–15位且同时包含字母和数字。":detail;
    const error=new Error(message||`请求失败（${response.status}）`);error.status=response.status;error.code=payload.code;throw error;
  }
  return payload;
}

function apiUser(user){
  const therapist=user.role==="therapist";
  return {...user,name:user.display_name,avatar:(user.display_name||user.username||"用")[0],meta:therapist?"康复治疗师":"患者"};
}

async function syncPatientData(){
  if(await syncVisualPlan())return;
  const data=await api("/me/plan/today");backendPlan=data;
  exercises.forEach(ex=>{ex.done=false;delete ex.planItemId;delete ex.exerciseCode});
  patientSide=data.patient?.affected_side==="R"?"right":"left";
  const codeToId={SLR:"supine",SQUAT:"squat",STS:"stand"};
  data.items.forEach(item=>{const ex=exercises.find(x=>x.id===codeToId[item.exercise_code]);if(!ex)return;ex.groups=item.sets;ex.reps=item.reps;ex.recommendedGroups=item.sets;ex.recommendedReps=item.reps;ex.dose=`${item.sets} 组 × ${item.reps} 次`;ex.planItemId=item.id;ex.exerciseCode=item.exercise_code;ex.done=(data.done_today[item.id]||0)>=item.sets});
  renderExercises();
  const stamp=$(".plan-stamp strong");const detail=$(".plan-stamp small");
  if(stamp)stamp.textContent=data.plan?.title||"当前暂无训练计划";
  if(detail&&data.patient)detail.textContent=`${data.patient.affected_side==="L"?"左侧":"右侧"} · ${data.patient.phase||"康复训练中"}`;
  if(detail&&!data.plan)detail.textContent="以下为演示训练项目，尚未关联康复师方案";
  $("#completed-count").textContent=exercises.filter(x=>x.done).length;
  $("#today-progress").style.width=`${exercises.filter(x=>x.done).length*25}%`;
}

async function syncTherapistData(){
  const [patients,stats]=await Promise.all([api("/patients"),api("/stats")]);
  $("#patient-rows").innerHTML=patients.map(p=>`<div class="patient-row"><div class="patient-cell-name"><i>${escapeHtml(p.display_name[0])}</i><b>${escapeHtml(p.display_name)}</b></div><span>${escapeHtml(p.surgery_type||p.phase||"康复训练")}</span><b>${p.days_trained_7d||0} 天</b><p>${p.last_session_at?`最近训练 ${escapeHtml(p.last_session_at.slice(0,10))}`:"暂无训练记录"}</p><span class="status ${p.open_alerts?"warn":"neutral"}">${p.open_alerts?`${p.open_alerts} 条提醒`:"正常"}</span><button class="text-button" data-patient-reports="${p.id}" data-patient-name="${escapeHtml(p.display_name)}" aria-label="查看${escapeHtml(p.display_name)}的训练报告">→</button></div>`).join("");
  therapistPatients=patients;
  populatePlanPatients(patients);
  $("#therapist-greeting").textContent=`${currentUser.name[0]}老师，当前有 ${stats.open_alerts||0} 条提醒需要处理`;
}

async function syncBackendData(){
  await loadServerReports();
  if(currentUser.role==="patient")await syncPatientData();else await syncTherapistData();
}
const demoUsers = [
  {key:"zhaomin",name:"赵敏",account:"p.zhaomin",password:"zhao123",role:"patient"},
  {key:"linyuqing",name:"林雨晴",account:"p.linyuqing",password:"linyu123",role:"patient"},
  {key:"zhouqiming",name:"周启明",account:"p.zhouqiming",password:"zhou123",role:"patient"},
  {key:"wu",name:"吴女士",account:"p.wu",password:"wu123",role:"patient"},
  {key:"patient",name:"张先生",account:"p.zhang",password:"zhang123",role:"patient",avatar:"张",meta:"患者"},
  {key:"therapist",name:"林康复师",account:"dr.lin",password:"lin123",role:"therapist",avatar:"林",meta:"康复治疗师"}
];
// Retire the old mock accounts, which stored passwords only in this browser.
try{localStorage.removeItem("kangshifu_registered_users")}catch(error){}
let savedDoses={}; // Legacy shared dose preferences are deliberately not imported.
exercises.forEach(ex=>{const values=ex.dose.match(/(\d+)\D+(\d+)/);ex.recommendedGroups=Number(values?.[1]||2);ex.recommendedReps=Number(values?.[2]||10);ex.groups=savedDoses[ex.id]?.groups||ex.recommendedGroups;ex.reps=savedDoses[ex.id]?.reps||ex.recommendedReps});
let currentUser = null;
let activeExercise = exercises[0];
let trainingTimer;
let cameraStream=null;
let visionSessionId=null;
let trainingRunning=false;
let frameBusy=false;
let cameraRequestGeneration=0;
let captureStart=0;
let lastVisionResult=null;
let lastTrainingReport=null;
let trainingOwner=null;
let reportPoll=null;
let reportsLoading=false;
let reportsReloadRequested=false;
let reportPatientFilter=null;
let trainingRecorder=null;
const pendingVideoFiles=new Map();
const videoUploads=new Set();
let playbackUrl=null;
let playbackGeneration=0;
let previewFlipped=true;
try{previewFlipped=localStorage.getItem("kangji_preview_flip")!=="false"}catch(e){}
let feedbackReports={};
let feedbackSelection=0;
let stoppingTraining=null;
const captureCanvas=document.createElement("canvas");
let selectedLoginRole="patient";
let selectedRegisterRole="patient";
let pendingTrainingId=null;
let activePatientName="林雨晴";
let messages=[];
try{messages=JSON.parse(localStorage.getItem("kangshifu_messages")||"[]")}catch(error){messages=[]}
if(!messages.length)messages=[{id:"seed-1",patient:"林雨晴",from:"therapist",text:"今天训练后如果疼痛超过 5 分，请在这里告诉我。",time:"今天 09:36",readByPatient:false,readByTherapist:true}];

function escapeHtml(value){return String(value).replace(/[&<>"']/g,char=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#039;"}[char]))}

function saveDosePreferences(){
  const doses=Object.fromEntries(exercises.map(ex=>[ex.id,{groups:ex.groups,reps:ex.reps}]));
  try{localStorage.setItem(`kangji_doses:${currentUser.id}`,JSON.stringify(doses))}catch(error){}
}

// Scheduling estimates only; hold/rest match the current live service.
// Outward/return motion each use 2 seconds, not a new evaluation threshold.
function estimateExerciseSeconds(ex, groups=ex.groups, reps=ex.reps){
  const t=ex.targets||defaultTargets(ex.id);
  return groups*reps*(2+t.hold_s+Math.max(2,t.return_s))+Math.max(0,groups-1)*t.rest_s;
}

function estimateMinutes(seconds){return `约 ${Math.ceil(seconds/60)} 分钟`}

function updateDurationEstimates(){
  exercises.forEach(ex=>{
    const node=$(`[data-duration="${ex.id}"]`);
    if(node){
      const seconds=estimateExerciseSeconds(ex);
      node.textContent=estimateMinutes(seconds);
      node.title=`${ex.groups}组×${ex.reps}次；${targetDescription(ex)}；按往返各至少2秒估算，不含准备与额外暂停。`;
    }
  });
  const remaining=availableExercises().filter(ex=>!ex.done).reduce((sum,ex)=>sum+estimateExerciseSeconds(ex),0);
  $("#today-remaining").textContent=!availableExercises().length?"添加动作后显示预计时间":remaining?`未完成项目预计还需${estimateMinutes(remaining)}`:"今日训练已完成";
  $("#completed-count").textContent=availableExercises().filter(ex=>ex.done).length;
  $("#exercise-total").textContent=availableExercises().length;
  $("#training-list-title").textContent=availableExercises().length?`今天的训练 · ${availableExercises().length} 个动作`:"尚未添加训练动作";
  $("#today-progress").style.width=`${availableExercises().filter(ex=>ex.done).length/Math.max(1,availableExercises().length)*100}%`;
}

function renderExercises(){
  const nextIndex=availableExercises().findIndex(ex=>!ex.done);
  $("#exercise-list").innerHTML = availableExercises().map((ex,i) => `<article class="exercise-card ${ex.done ? "done" : ""}"><button class="exercise-thumb" type="button" data-train="${ex.id}" aria-label="开始训练：${ex.name}"><img src="${ex.image}" alt="${ex.name}示范"><span class="thumb-badge ${!ex.done&&i===nextIndex?"next":""}">${ex.done?"今日已完成":i===nextIndex?"下一个":""}</span><span class="thumb-duration" data-duration="${ex.id}"></span>${ex.done?'<i class="thumb-progress"></i>':""}</button><div class="exercise-body"><span class="exercise-index">0${i+1}</span><div class="exercise-info"><h4>${ex.name}</h4><p class="exercise-meta"><span>${ex.groups} 组 × ${ex.reps} 次</span></p><p class="exercise-flow">${ex.flow}</p></div></div><div class="exercise-action"><button class="${ex.done ? "secondary-button" : "primary-button"}" data-train="${ex.id}">${ex.done ? "再练一次" : "开始训练"}</button><details class="exercise-config"><summary>调整训练量</summary><div class="dose-editor"><b>自主训练量</b><label>组数<input type="number" min="1" max="20" step="1" value="${ex.groups}" data-dose-field="groups" data-exercise-id="${ex.id}" aria-label="${ex.name}训练组数"></label><label>每组次数<input type="number" min="1" max="100" step="1" value="${ex.reps}" data-dose-field="reps" data-exercise-id="${ex.id}" aria-label="${ex.name}每组次数"></label><small>${patientTrainingSource==="prescribed"?"康复师建议":patientTrainingSource==="demo"?"演示设置":"自主设置（待康复师确认）"}：${ex.dose}</small></div></details></div></article>`).join("");
  $("#patient-plan-rows").innerHTML = availableExercises().map((ex,i)=>`<div class="plain-row"><span>0${i+1}</span><b>${ex.name}</b><p>${ex.dose} · ${estimateMinutes(estimateExerciseSeconds(ex,ex.recommendedGroups,ex.recommendedReps))}</p><p>${escapeHtml(targetDescription(ex))}</p></div>`).join("");
  if(!availableExercises().length){
    const empty='<div class="content-section"><h3>还没有训练方案</h3><p>可以先关联康复师，或自主添加膝骨关节炎训练方向与动作。自主选择不代表诊断。</p><button class="primary-button" data-add-selection>添加病症与动作</button> <button class="secondary-button" data-goto="care-connections">关联康复师</button></div>';
    $("#exercise-list").innerHTML=empty;$("#patient-plan-rows").innerHTML=empty;
  }
  $("#edit-training-selection").hidden=patientTrainingSource==="prescribed";
  $("#patient-training-intro").textContent=patientTrainingSource==="prescribed"?"按康复师发布的方案进行训练。":patientTrainingSource==="demo"?"虚构演示账号：以下为演示训练项目。":patientTrainingSource==="self"?"以下为自主选择的动作，待康复师确认。":"尚未确定训练方向，请先关联康复师或添加病症与动作。";
  const prescribed=patientTrainingSource==="prescribed",demo=patientTrainingSource==="demo",self=patientTrainingSource==="self";
  $("#my-plan-title").textContent=prescribed?visualPlan.title:demo?"演示训练方案":self?"自主选择的训练动作":"尚无训练方案";
  $("#my-plan-source").textContent=prescribed?`康复师发布 · 版本 ${visualPlan.id}`:demo?"虚构演示账号，供功能演示使用。":self?"自主选择，待康复师确认，不代表诊断。":"请先关联康复师或自主添加训练方向。";
  $("#my-plan-condition").textContent=prescribed?"请以康复师评估为准":demo?"膝骨关节炎（演示）":self?"膝骨关节炎（自主选择）":"尚未确定";
  $("#my-plan-goal").textContent=prescribed?(visualPlan.notes||"暂无额外说明"):"待康复师确认";
  $("#my-plan-frequency").textContent=prescribed?`每周 ${visualPlan.days_per_week} 天，每日 ${visualPlan.daily_sessions} 次`:"待康复师确认";
  updateDurationEstimates();
}

function feedbackStorageKey(userId){return `kangji_actual_feedback_v1:${userId}`}

function loadFeedbackReports(userId){
  feedbackReports={};
  try{
    const saved=JSON.parse(sessionStorage.getItem(feedbackStorageKey(userId))||"{}");
    for(const ex of exercises){const row=saved[ex.id];if(row?.brief?.version&&Array.isArray(row.metrics)&&Array.isArray(row.brief.sets))feedbackReports[ex.id]=row}
  }catch(error){}
  renderFeedback();
}

function buildFeedbackRecord(exerciseId,result){
  const brief=result?.brief_report;if(!brief)return null;
  const reps=(result.repetitions||[]).filter(r=>!r.needs_review);
  const values=key=>reps.map(r=>r[key]).filter(Number.isFinite);
  const average=key=>{const v=values(key);return v.length?v.reduce((a,b)=>a+b,0)/v.length:null};
  const metric=(name,value,unit,context)=>[name,Number.isFinite(value)?`${value.toFixed(1)}${unit}`:"暂无可靠数据",context];
  const metrics=[
    ["识别完成次数",`${brief.completed_reps} 次`,`本次计划 ${brief.target_reps} 次；包含未达标的完整动作`],
    ["达到角度与保持目标",`${brief.sets.reduce((n,g)=>n+g.angle_hold_met_reps,0)} 次`,"不等于所有动作指标均合格"]
  ];
  if(exerciseId==="seated"){
    const peaks=values("knee_peak_deg");
    metrics.push(metric("最大膝关节夹角",peaks.length?Math.max(...peaks):null,"°","仅取无需复核的完整动作，伸直接近180°"));
  }
  if(exerciseId==="supine"){
    const peaks=values("raise_peak_deg");
    metrics.push(metric("床面抬腿角峰值",peaks.length?Math.max(...peaks):null,"°","支撑面标定后的二维代理角"));
    metrics.push(["目标完成",`${(result.repetitions||[]).filter(r=>r.target_completed===true).length} 次`,"联合保持、膝控制与关键阶段可靠同时满足"]);
    metrics.push(["持续屈膝事件",`${(result.repetitions||[]).reduce((n,r)=>n+(r.bend_event_count||0),0)} 次`,"膝屈曲超过15°持续0.3秒"]);
  }
  if(exerciseId==="squat"){
    const peaks=values("knee_flexion_peak_deg");
    metrics[1]=["目标完成次数",`${brief.goal_reps??0} 次`,"完整动作、目标范围与连续保持同时满足，且未发生超深"];
    metrics.push(metric("最大膝屈曲角",peaks.length?Math.max(...peaks):null,"°","180°减膝夹角；不是相对初始变化"));
    metrics.push(["超出设定深度",`${(result.repetitions||[]).filter(r=>r.depth_exceeded).length} 次`,"回到目标范围后仍保留本次事件"]);
    metrics.push(["尝试 / 无法评价",`${brief.attempted_reps??"暂无"} / ${brief.unable_to_evaluate??"暂无"} 次`,"无法评价不算合规或不合规"]);
  }
  if(exerciseId==="stand"){
    metrics.push(["尝试次数",`${brief.attempted_reps??"暂无"} 次`,"包含未完成或无法评价的尝试"]);
    metrics.push(["目标完成次数",`${brief.goal_reps??"暂无"} 次`,"完整坐站且达到连续保持目标"]);
    metrics.push(["无法评价",`${brief.unable_to_evaluate??"暂无"} 次`,"不按正常动作处理"]);
    metrics.push(metric("平均起立至站立确认",average("rise_to_stand_s"),"秒","从启动到联合进入站姿"));
    metrics.push(metric("平均坐回用时",average("sit_down_s"),"秒","最终成功坐回段"));
  }
  metrics.push(metric(exerciseId==="stand"?"平均起立至站立确认":"平均到峰值用时",average("movement_to_first_peak_s"),"秒","完整动作从启动到峰值；不等同于全程上抬时间"));
  metrics.push(metric("平均连续保持",average("target_hold_s"),"秒",`本次设置保持 ${result.training_session?.plan?.hold_s??"未提供"} 秒`));
  metrics.push(metric(exerciseId==="squat"?"平均起身用时":"平均放回用时",average("return_s"),"秒","无需复核且有计时数据的完整动作"));
  return {savedAt:new Date().toISOString(),brief,metrics,
    events:(result.feedback_events||[]).map(e=>({timestamp_s:e.timestamp_s,training_set:e.training_set,message:e.message,code:e.code}))};
}

function rememberFeedback(exerciseId,result,userId){
  const record=buildFeedbackRecord(exerciseId,result);if(!record||userId==null)return;
  feedbackReports[exerciseId]=record;
  try{sessionStorage.setItem(feedbackStorageKey(userId),JSON.stringify(feedbackReports))}
  catch(error){showToast("本次反馈已显示，但浏览器存储不足，刷新后可能丢失，请下载简报")}
  renderFeedback(exercises.findIndex(ex=>ex.id===exerciseId));
}

function renderFeedback(index=feedbackSelection){
  feedbackSelection=Math.max(0,index);const ex=exercises[feedbackSelection],record=feedbackReports[ex.id],brief=record?.brief;
  $("#feedback-index").innerHTML=exercises.map((item,i)=>`<button class="${i===feedbackSelection?"active":""}" data-feedback="${i}"><span>0${i+1}</span><div><b>${item.short}</b><small>${feedbackReports[item.id]?`最近识别 ${feedbackReports[item.id].brief.completed_reps} 次`:"暂无训练记录"}</small></div></button>`).join("");
  $("#feedback-kicker").textContent=`动作 0${feedbackSelection+1}`;$("#feedback-title").textContent=ex.name;
  $("#feedback-status").className="status neutral";
  $("#feedback-sets").innerHTML="";$("#feedback-events").innerHTML="";
  if(!brief){
    $("#feedback-status").textContent="暂无记录";$("#feedback-source").textContent="尚无本账号的训练结果";
    $("#feedback-hero").innerHTML="<strong>完成一次训练后查看真实反馈</strong><p>开始识别并结束训练后，这里会显示本次测量值、分组总结和调整提示。</p><button class='primary-button' data-goto='patient-home'>去今日训练</button>";
    $("#feedback-metrics").innerHTML="";$("#therapist-note").textContent="暂无基于实际动作的建议。";return;
  }
  const problems=brief.sets.some(g=>g.problems?.length),review=brief.interrupted_attempts||brief.sets.some(g=>g.needs_review_reps);
  $("#feedback-status").textContent=!brief.completed_reps?"未识别完整动作":problems?"有待调整项":review?"部分数据需复核":"已生成反馈";
  $("#feedback-status").className=`status ${problems||review?"warn":"neutral"}`;
  $("#feedback-source").textContent=`最近一次训练 · ${new Date(record.savedAt).toLocaleString("zh-CN")} · ${brief.side} · ${record.serverId?"已保存到账号":"本次结果还没保存到账号"}`;
  $("#feedback-hero").innerHTML=`<strong>识别完成 ${brief.completed_reps} / 计划 ${brief.target_reps} 次</strong><p>${escapeHtml(brief.scope)}</p>`;
  $("#feedback-metrics").innerHTML=record.metrics.map(m=>`<div class="metric-row"><span>${escapeHtml(m[0])}</span><b>${escapeHtml(m[1])}</b><small>${escapeHtml(m[2])}</small><span class="metric-result neutral">实际记录</span></div>`).join("");
  $("#feedback-sets").innerHTML=brief.sets.map(g=>`<section class="report-set"><h3>第 ${g.set} 组 · ${escapeHtml(g.status)}</h3><p>识别 ${g.completed_reps} / ${g.target_reps} 次，${g.angle_hold_met_reps} 次${ex.id==="squat"?"完成本次微蹲目标":"达到角度与保持目标"}。</p><p>${escapeHtml(g.finding)}</p>${g.needs_review_reps?`<p>${g.needs_review_reps} 次需复核，缺失测量未当成正常。</p>`:""}</section>`).join("");
  $("#feedback-events").innerHTML=record.events.length?`<details><summary>查看本次 ${record.events.length} 条提醒（时间相对本次训练开始）</summary>${record.events.slice(0,100).map(e=>`<p>${Number.isFinite(e.timestamp_s)?e.timestamp_s.toFixed(1)+"秒":"时间未记录"} · 第${escapeHtml(e.training_set??"—")}组 · ${escapeHtml(e.message||e.code)}</p>`).join("")}${record.events.length>100?"<p>此处展示前100条，分组总结已汇总全部提醒。</p>":""}</details>`:"<p>本次没有记录到规则提醒；不代表动作一定合格。</p>";
  $("#therapist-note").textContent=brief.suggestions.join(" ");
}

function renderTherapist(){
  const patients=[["赵敏","膝骨关节炎 · 功能恢复期","2 / 4","训练后疼痛 6 分","需联系","danger"],["林雨晴","膝骨关节炎 · 功能恢复期","1 / 4","伸膝保持不足","需复核","warn"],["周启明","前交叉韧带术后 · 力量重建期","0 / 5","连续两日未训练","待提醒","neutral"],["郭莹","肩袖修复术后 · 活动度恢复期","3 / 3","外旋角度稳定改善","正常","neutral"],["宋泽","非特异性腰痛 · 回归活动期","4 / 4","动作控制稳定","正常","neutral"]];
  $("#patient-rows").innerHTML=patients.map(p=>`<div class="patient-row"><div class="patient-cell-name"><i>${p[0][0]}</i><b>${p[0]}</b></div><span>${p[1]}</span><b>${p[2]}</b><p>${p[3]}</p><span class="status ${p[5]}">${p[4]}</span><button class="text-button">→</button></div>`).join("");
  $("#action-picker").innerHTML=exercises.map(ex=>`<div class="picker-item selected" data-picker="${ex.id}"><img src="${ex.image}" alt=""><div><b>${ex.name}</b><small>${ex.focus.length} 项独立指标</small></div><button aria-label="选择${ex.name}">✓</button></div>`).join("");
  renderRules();
  $("#rule-library").innerHTML=exercises.map((ex,i)=>`<article class="library-row"><span class="exercise-index">0${i+1}</span><div><img src="${ex.image}" alt="${ex.name}"></div><div><h3>${ex.name}</h3><p>${ex.flow}</p></div><div class="library-tags">${ex.focus.map(x=>`<span>${x}</span>`).join("")}</div><small>${ex.rules.length} 条识别规则</small></article>`).join("");
  renderSelectedSummary();
}

function renderRules(){renderPlanEditor()}

function renderSelectedSummary(){
  $("#plan-frequency-summary").textContent=`每周${$("#plan-days").value}天，每日${$("#plan-daily").value}次`;
  const selected=$$(".picker-item.selected").map(x=>exercises.find(ex=>ex.id===x.dataset.picker)).filter(Boolean);
  $("#selected-count").textContent=`${selected.length} 项`;
  $("#selected-duration").textContent=estimateMinutes(selected.reduce((sum,ex)=>sum+estimateExerciseSeconds({...ex,targets:{hold_s:Number($(`[data-rule="${ex.id}"] [data-plan-field="hold_s"]`).value),return_s:Number($(`[data-rule="${ex.id}"] [data-plan-field="return_s"]`).value),rest_s:Number($(`[data-rule="${ex.id}"] [data-plan-field="rest_s"]`).value)}},Number($(`[data-rule="${ex.id}"] [data-plan-field="sets"]`).value),Number($(`[data-rule="${ex.id}"] [data-plan-field="reps"]`).value)),0));
  $("#selected-summary").innerHTML=selected.map((ex,i)=>`<span>0${i+1} · ${ex.name}</span>`).join("");
}

function setRole(kind,role){
  const selector=kind==="login"?"[data-login-role]":"[data-register-role]";
  $$(selector).forEach(button=>{const active=button.dataset[kind+"Role"]===role;button.classList.toggle("active",active);button.setAttribute("aria-pressed",String(active))});
  if(kind==="login")selectedLoginRole=role;else selectedRegisterRole=role;
}

function showAuthScreen(screen){
  $("#login-screen").classList.toggle("hidden",screen!=="login");
  $("#register-screen").classList.toggle("hidden",screen!=="register");
  if(screen==="register")$("#register-name").focus();else $("#login-account").focus();
}

function openGuide(id){
  const ex=availableExercises().find(item=>item.id===id);if(!ex)return;pendingTrainingId=id;
  $("#guide-title").textContent=ex.name;
  $("#guide-steps").innerHTML=ex.flow.split("→").map(step=>`<li>${step.trim()}</li>`).join("");
  $("#guide-note").textContent=ex.note+"；"+targetDescription(ex);
  $("#guide-dose").textContent=`本次计划：${ex.groups} 组 × ${ex.reps} 次`;
  $("#training-side").value=patientSide;
  $("#exercise-guide-dialog").showModal();
}

function saveMessages(){try{localStorage.setItem("kangshifu_messages",JSON.stringify(messages))}catch(error){}}

function updateMessageBadge(){
  if(!currentUser)return;
  const unread=messages.filter(message=>currentUser.role==="patient"?message.patient===currentUser.name&&message.from==="therapist"&&!message.readByPatient:message.from==="patient"&&!message.readByTherapist).length;
  $("#message-count").textContent=unread;$("#message-count").classList.toggle("empty",unread===0);
}

function renderMessageContacts(){
  if(currentUser?.role!=="therapist"){$("#message-contacts").innerHTML="";return}
  const names=therapistPatients.map(p=>p.display_name);
  $("#message-contacts").innerHTML=names.map(name=>{const unread=messages.filter(message=>message.patient===name&&message.from==="patient"&&!message.readByTherapist).length;return `<button type="button" class="${name===activePatientName?"active":""}" data-message-contact="${name}">${name}${unread?`<i>${unread}</i>`:""}</button>`}).join("");
}

function renderMessages(){
  const conversation=messages.filter(message=>message.patient===activePatientName);
  $("#message-title").textContent=currentUser.role==="therapist"?`与${activePatientName}沟通`:`与陈晓雯康复师沟通`;
  $("#message-thread").innerHTML=conversation.length?conversation.map(message=>{const mine=message.from===currentUser.role;const sender=message.from==="therapist"?"康复师":"患者";return `<article class="message-bubble ${mine?"mine":""}"><span>${sender} · ${escapeHtml(message.time)}</span><p>${escapeHtml(message.text)}</p></article>`}).join(""):'<p class="empty-thread">还没有消息，可以从这里开始沟通。</p>';
  $("#message-thread").scrollTop=$("#message-thread").scrollHeight;
  renderMessageContacts();
}

function openMessages(patientName){
  activePatientName=currentUser.role==="patient"?currentUser.name:(patientName||activePatientName||"林雨晴");
  messages.forEach(message=>{if(message.patient!==activePatientName)return;if(currentUser.role==="patient"&&message.from==="therapist")message.readByPatient=true;if(currentUser.role==="therapist"&&message.from==="patient")message.readByTherapist=true});
  saveMessages();renderMessages();updateMessageBadge();$("#message-dialog").showModal();setTimeout(()=>$("#message-input").focus(),50);
}

function enterApp(user){
  currentUser=user;patientTrainingSource="empty";selfTrainingSelection=null;selfSelectionSignature=null;resetPatientExercises();therapistPatients=[];reportPatientFilter=null;visualPlan=null;visualPlanUser=null;exercises.forEach(ex=>{delete ex.targets;ex.planSelected=false});patientSide="left";
  restoreTrainingVideos().then(()=>loadServerReports());
  for(const prefix of ["patient","therapist"]){$("#"+prefix+"-report-list").innerHTML="";$("#"+prefix+"-report-status").textContent="正在加载账号报告…"}
  $("#report-unread-count").textContent="";
  lastTrainingReport=null;$("#view-last-report").hidden=true;
  clearInterval(reportPoll);
  reportPoll=setInterval(()=>{if(!document.hidden&&currentUser?.id===user.id){loadServerReports();if(user.role==="patient"&&!trainingRunning&&!$("#exercise-guide-dialog").open&&!$("#training-screen").classList.contains("active"))syncVisualPlan().catch(()=>{})}},15000);
  renderExercises();$(".plan-stamp strong").textContent="正在读取方案";$(".plan-stamp small").textContent="";
  loadFeedbackReports(user.id);
  $("#login-screen").classList.add("hidden"); $("#register-screen").classList.add("hidden"); $("#app-shell").classList.remove("hidden");
  const therapist=user.role==="therapist";
  $("#patient-nav").classList.toggle("hidden",therapist); $("#therapist-nav").classList.toggle("hidden",!therapist); $("#patient-tabbar").classList.toggle("hidden",therapist);
  $("#profile-avatar").textContent=user.avatar; $("#profile-name").textContent=user.name; $("#profile-meta").textContent=user.meta;
  $("#patient-greeting").textContent=`${user.name}的今日训练`;
  {const d=new Date();$("#patient-date").textContent=`${d.getMonth()+1}月${d.getDate()}日 · 周${"日一二三四五六"[d.getDay()]}`;}
  $("#therapist-greeting").textContent=`${user.name[0]}老师，今天有 5 个动作需要复核`;
  $("#section-label").textContent=therapist?"康复师端":"患者端";
  gotoPage(therapist?"therapist-overview":"patient-home");
  updateMessageBadge();
}

function gotoPage(page){
  $$(".page").forEach(x=>x.classList.toggle("active-page",x.id===page));
  $$(".nav-item").forEach(x=>x.classList.toggle("active",x.dataset.page===page));
  const active=$(`${currentUser?.role==="therapist"?"#therapist-nav":"#patient-nav"} .nav-item[data-page="${page}"]`); $("#page-label").textContent=active?active.textContent.trim().replace(/^\d+/,""):"康复方案";
  if(page==="care-connections"){ $("#care-search-results").innerHTML="";$("#care-search-account").value="";loadCareConnections() }
  if(["patient-feedback","patient-history","therapist-reports"].includes(page))loadServerReports();
  $(".sidebar").classList.remove("mobile-open"); window.scrollTo({top:0,behavior:"smooth"});
}

function openTraining(id){
  const ex=availableExercises().find(x=>x.id===id); if(!ex)return; activeExercise=ex;
  const i=exercises.indexOf(ex); $("#training-kicker").textContent=`动作 0${i+1}`; $("#training-title").textContent=ex.name; $("#training-image").src=ex.image;
  $(".camera-state").innerHTML="<i></i>摄像头未开启"; $("#phase-name").textContent="准备"; $("#live-cue").textContent="请调整位置并保持训练侧髋、膝、踝入镜"; $("#live-cue-detail").textContent=ex.flow;
  $("#live-metrics").innerHTML=ex.live.map(m=>`<div class="live-metric"><span>${m[0]}</span><b>--</b><small>${m[0]==="本组次数"?`/ ${ex.reps}`:m[2]}</small></div>`).join("");
  $("#cue-log").innerHTML=`<li><time>准备</time><p>${ex.note}</p></li>`; $("#start-training").textContent="允许摄像头并开始识别"; $("#start-training").disabled=false; clearTimeout(trainingTimer);
  $("#training-screen").classList.add("active"); $("#training-screen").setAttribute("aria-hidden","false"); document.body.classList.add("training-open");
}

function visionHeaders(extra){
  // 浏览器模式下视觉服务对公网开放，复用业务后端同一套登录令牌。
  const headers={...(extra||{})};
  if(VISION_MODE!=="local"&&apiToken)headers.Authorization=`Bearer ${apiToken}`;
  return headers;
}

async function visionApi(path,body){
  const queue=VISION_MODE==="remote"&&path!=="/start"?remoteFrames:null;
  if(!queue)return rawVisionApi(path,body);
  queue.paused=true;
  try{await queue.drain();return await rawVisionApi(path,body)}finally{queue.paused=false}
}
async function rawVisionApi(path,body){
  const response=await fetch(`${VISION_BASE}${path}`,{method:"POST",headers:visionHeaders({"Content-Type":"application/json"}),body:JSON.stringify(body||{}),signal:AbortSignal.timeout(15000)});
  const payload=await response.json().catch(()=>({error:`HTTP ${response.status}`}));
  if(!response.ok){const error=new Error(payload.error||payload.detail||`识别服务出错（${response.status}）`);error.status=response.status;throw error}
  return payload;
}

function expireVisionSession(){
  finishTrainingVideo();
  cameraRequestGeneration++;trainingRunning=false;clearTimeout(trainingTimer);
  visionSessionId=null;trainingOwner=null;lastVisionResult=null;
  cameraStream?.getTracks().forEach(track=>track.stop());cameraStream=null;
  $("#training-video").srcObject=null;$(".camera-stage").classList.remove("live");
  const canvas=$("#pose-overlay");canvas.getContext("2d").clearRect(0,0,canvas.width,canvas.height);
  $(".camera-state").innerHTML="<i></i>识别已结束";
  $("#live-cue").textContent="请重新开始识别";
  $("#live-cue-detail").textContent="识别中断了，点下方按钮重新开始。这不是你的动作有问题。本次还没保存的结果无法恢复。";
  $("#phase-name").textContent="等待重新开始";
  $("#start-training").disabled=false;$("#start-training").textContent="重新开始识别";
}

function applyPreviewDirection(){
  $("#training-video").style.transform=previewFlipped?"scaleX(-1)":"none";
  $("#flip-preview").setAttribute("aria-pressed",String(previewFlipped));
  const canvas=$("#pose-overlay");canvas.getContext("2d").clearRect(0,0,canvas.width,canvas.height);
}
$("#flip-preview").addEventListener("click",()=>{previewFlipped=!previewFlipped;try{localStorage.setItem("kangji_preview_flip",String(previewFlipped))}catch(e){}applyPreviewDirection()});
applyPreviewDirection();

function drawPose(result){
  const video=$("#training-video"),canvas=$("#pose-overlay"),ctx=canvas.getContext("2d");
  // The backend returns pixel coordinates in the resized upload frame, not in
  // the camera's native resolution. Keep the overlay's intrinsic size equal to
  // that upload frame so CSS object-fit scales video and skeleton identically.
  const fw=result.frame_size?.width||captureCanvas.width,fh=result.frame_size?.height||captureCanvas.height;
  if(canvas.width!==fw)canvas.width=fw;if(canvas.height!==fh)canvas.height=fh;ctx.clearRect(0,0,canvas.width,canvas.height);
  ctx.save();if(previewFlipped){ctx.translate(canvas.width,0);ctx.scale(-1,1)}
  ctx.drawImage(captureCanvas,0,0,canvas.width,canvas.height);
  lastVisionResult=result;
  const points=result.keypoints||{};const color=result.visible?"#c8f26b":"#f2a65a";
  ctx.strokeStyle=color;ctx.fillStyle=color;const displayScale=Math.min(canvas.clientWidth/canvas.width,canvas.clientHeight/canvas.height)||1;ctx.lineWidth=2/displayScale;ctx.lineCap="round";
  [["shoulder","hip"],["hip","knee"],["knee","ankle"]].forEach(([a,b])=>{if(!points[a]||!points[b])return;ctx.beginPath();ctx.moveTo(points[a].x,points[a].y);ctx.lineTo(points[b].x,points[b].y);ctx.stroke()});
  if(result.subject && result.subject.status!=="locked"){
    ctx.strokeStyle="#ffffff";
    for(const b of result.subject.boxes||[])ctx.strokeRect(b[0],b[1],b[2]-b[0],b[3]-b[1]);
  }
  Object.values(points).forEach(point=>{if(point.x==null||point.y==null)return;ctx.beginPath();ctx.arc(point.x,point.y,3/displayScale,0,Math.PI*2);ctx.fill()});
  if(result.calibration?.surface_points){
    const [a,b]=result.calibration.surface_points;ctx.strokeStyle="#ffffff";ctx.beginPath();ctx.moveTo(a[0]*canvas.width,a[1]*canvas.height);ctx.lineTo(b[0]*canvas.width,b[1]*canvas.height);ctx.stroke();
  }
  ctx.restore();
}

function fmt(value,digits=1){return Number.isFinite(value)?Number(value).toFixed(digits):"--"}

function updateLiveResult(result,options){
  if(VISION_MODE==="browser")lastVisionResult={...result,subject:browserSubject};
  // 浏览器模式下骨架已用本地关键点画好（不等服务端往返），这里不再重画。
  if(!(options&&options.skipOverlay))drawPose(result);
  const phaseNames={waiting_for_rest:"等待起始姿势",rest:"起始位",extending:"运动中",holding:"保持",returning:"返回",waiting_for_points:"识别暂停"};
  $("#phase-name").textContent=phaseNames[result.phase]||result.phase;
  $("#live-cue").textContent=result.guidance?.message||"正在识别";
  $("#live-cue-detail").textContent=result.visible?`置信度 ${Math.round((result.confidence||0)*100)}% · ${result.side==="left"?"左腿":"右腿"}`:"当前帧不参与角度和计数";
  const m=result.measurement_metrics||{};let values;
  if(activeExercise.id==="supine")values=[["床面抬腿角",fmt(m.slr_thigh_surface_deg),"°"],["膝屈曲",fmt(m.knee_flexion_deg),"°"],["本组次数",result.training_progress?.reps_in_set??0,`/ ${activeExercise.reps}`],["抬腿速度",fmt(m.raise_velocity_deg_s),"°/秒"]];
  else if(activeExercise.id==="stand")values=[["膝关节夹角",fmt(m.knee_included_deg),"°"],["髋上升进度",Number.isFinite(m.hip_rise_progress)?fmt(m.hip_rise_progress*100):"--","%"],["本组完整次数",result.training_progress?.reps_in_set??0,`/ ${activeExercise.reps}`],["距站姿躯干基线",fmt(m.trunk_stand_delta_deg),"°"]];
  else if(activeExercise.id==="squat")values=[["膝屈曲",fmt(m.knee_flexion_deg),"°"],["髋下降 / 小腿长",fmt(m.hip_drop_shank_ratio,3),""],["本组次数",result.training_progress?.reps_in_set??0,`/ ${activeExercise.reps}`],["膝角速度",fmt(m.knee_velocity_deg_s),"°/秒"]];
  else values=[["膝关节夹角",fmt(m.knee_included_deg),"°"],["躯干变化",fmt(m.trunk_delta_deg),"°"],["本组次数",result.training_progress?.reps_in_set??0,`/ ${activeExercise.reps}`],["膝角速度",fmt(m.knee_velocity_deg_s),"°/秒"]];
  const metrics=$("#live-metrics");
  if(metrics.children?.length===values.length){
    values.forEach((v,i)=>["span","b","small"].forEach((tag,j)=>{const node=metrics.children[i].querySelector(tag),text=String(v[j]);if(node.textContent!==text)node.textContent=text}));
  }else metrics.innerHTML=values.map(v=>`<div class="live-metric"><span>${v[0]}</span><b>${v[1]}</b><small>${v[2]}</small></div>`).join("");
  (result.feedback_events||[]).forEach(event=>$("#cue-log").insertAdjacentHTML("afterbegin",`<li><time>${fmt(event.timestamp_s)}秒</time><p>${event.rep_index?`第 ${event.rep_index} 次：`:""}${escapeHtml(event.message)}</p></li>`));
}

// ===== 浏览器端识别 =====
// 识别在本页面里完成，只把 33 个关键点发给服务端跑规则；画面不离开用户设备。
let poseWorker=null,poseWorkerReady=null,poseFrameSeq=0;
const poseWaiters=new Map();

function ensurePoseWorker(){
  if(poseWorkerReady)return poseWorkerReady;
  poseWorkerReady=new Promise((resolve,reject)=>{
    let worker;
    try{worker=new Worker("pose-worker.js")}
    catch(error){reject(new Error("当前浏览器不支持所需的识别模块，请换用较新的浏览器"));return}
    poseWorker=worker;
    // 首次要下载约 20MB 的运行库与模型，网络慢时给足时间。
    const timer=setTimeout(()=>reject(new Error("识别模型加载超时，请检查网络后重试")),180000);
    worker.onmessage=event=>{
      const msg=event.data||{};
      if(msg.type==="ready"){clearTimeout(timer);resolve();return}
      if(msg.type==="error"){clearTimeout(timer);reject(new Error(msg.message||"识别模型加载失败"));return}
      if(msg.type==="result"){const waiter=poseWaiters.get(msg.id);if(waiter){poseWaiters.delete(msg.id);waiter(msg)}}
    };
    worker.onerror=()=>{clearTimeout(timer);reject(new Error("识别模块加载失败"))};
    worker.postMessage({type:"init"});
  }).catch(error=>{poseWorker=null;poseWorkerReady=null;throw error});
  return poseWorkerReady;
}

function releasePoseWorker(){
  poseWaiters.clear();
  if(poseWorker){poseWorker.terminate();poseWorker=null;poseWorkerReady=null}
}

function detectLandmarks(bitmap,width,height,timestamp_s){
  return new Promise((resolve,reject)=>{
    const id=++poseFrameSeq;
    const timer=setTimeout(()=>{if(poseWaiters.delete(id))reject(new Error("识别超时"))},15000);
    poseWaiters.set(id,msg=>{clearTimeout(timer);msg.error?reject(new Error(msg.error)):resolve(msg)});
    // bitmap 直接转交给 worker，不复制像素。
    poseWorker.postMessage({type:"frame",id,bitmap,width,height,timestamp_s},[bitmap]);
  });
}

// 关键点先在本地画出来，不等服务端往返，这样公网延迟不会变成画面卡顿。
const browserLock=new BrowserSubjectLock();
let browserSubject=null,browserSelectionBusy=false,browserLastTime=0,browserLockEpoch=0;
const POSE_LINES=[[11,23],[23,25],[25,27],[12,24],[24,26],[26,28],[11,12],[23,24]];
function drawLocalSkeleton(landmarks,width,height,append=false){
  const canvas=$("#pose-overlay"),context=canvas.getContext("2d");
  if(canvas.width!==width||canvas.height!==height){canvas.width=width;canvas.height=height}
  if(!append)context.clearRect(0,0,canvas.width,canvas.height);
  if(!landmarks)return;
  const visible=point=>point&&Math.min(point.visibility,point.presence)>=.5;
  context.lineWidth=Math.max(2,width/240);context.strokeStyle="rgba(46,160,120,.9)";
  POSE_LINES.forEach(([a,b])=>{
    const from=landmarks[a],to=landmarks[b];
    if(!visible(from)||!visible(to))return;
    context.beginPath();context.moveTo((previewFlipped?1-from.x:from.x)*width,from.y*height);context.lineTo((previewFlipped?1-to.x:to.x)*width,to.y*height);context.stroke();
  });
  context.fillStyle="rgba(255,255,255,.95)";
  [11,12,23,24,25,26,27,28].forEach(index=>{
    const point=landmarks[index];if(!visible(point))return;
    context.beginPath();context.arc((previewFlipped?1-point.x:point.x)*width,point.y*height,Math.max(3,width/260),0,Math.PI*2);context.fill();
  });
}

// 采集与上报分成两条独立的循环。
//
// 采集循环只做"识别 + 本地画骨架 + 入队"，不等网络，所以画面永远跟手。
// 上报循环把队列里攒下的帧一次发走，公网往返实测在几百毫秒量级，逐帧单发会把
// 帧率压到 1-2 fps；合批之后往返被摊薄，而时间戳是采集时打的，规则层对时长和
// 保持时间的判断不受影响。
const LANDMARK_QUEUE=[];
const MAX_BATCH=40;          // 与服务端 MAX_FRAMES_PER_BATCH 一致
const MAX_QUEUE=120;         // 网络长时间卡住时最多积压 8 秒，超出丢最旧的
let uploadBusy=false,captureTimer=null;

async function captureLandmarksLoop(){
  if(!trainingRunning)return;
  const lockEpoch=browserLockEpoch;
  const generation=cameraRequestGeneration;
  const video=$("#training-video");
  if(video.readyState<2){captureTimer=setTimeout(captureLandmarksLoop,180);return}
  const frameStart=performance.now();
  try{
    const timestamp_s=(frameStart-captureStart)/1000;
    const width=video.videoWidth,height=video.videoHeight;
    const bitmap=await createImageBitmap(video);
    const detected=await detectLandmarks(bitmap,width,height,timestamp_s);
    if(browserSelectionBusy||lockEpoch!==browserLockEpoch||generation!==cameraRequestGeneration||!trainingRunning)return;
    browserLastTime=timestamp_s;
    const tracked=browserLock.update(detected.candidates||[],timestamp_s);
    browserSubject={...tracked.subject,boxes:tracked.subject.boxes.map(b=>[b[0]*width,b[1]*height,b[2]*width,b[3]*height])};
    detected.landmarks=tracked.landmarks;detected.pose_status=tracked.pose_status;
    if(generation!==cameraRequestGeneration||!trainingRunning)return;
    // Show detected bodies before selection, without sending an unconfirmed
    // person's landmarks to the rule engine. Counting still requires a lock.
    drawLocalSkeleton(detected.landmarks,width,height);
    if(browserSubject.status==="select_subject"||browserSubject.status==="subject_lost_reconfirm"){
      for(const candidate of browserLock.candidates){
        drawLocalSkeleton(candidate.landmarks,width,height,true);
      }
    }
    lastVisionResult={...(lastVisionResult||{}),subject:browserSubject};
    const ctx=$("#pose-overlay").getContext("2d");
    if(browserSubject.status!=="locked"){ctx.strokeStyle="#f2a65a";ctx.lineWidth=2;for(const b of browserSubject.boxes)ctx.strokeRect(previewFlipped?width-b[2]:b[0],b[1],b[2]-b[0],b[3]-b[1]);}
    showBrowserLockStatus();
    LANDMARK_QUEUE.push({landmarks:detected.landmarks||[],pose_status:detected.pose_status,width,height,timestamp_s});
    // 丢最旧的而不是最新的：规则层要求时间戳递增，丢掉已经排在前面的帧不影响后续判定。
    while(LANDMARK_QUEUE.length>MAX_QUEUE)LANDMARK_QUEUE.shift();
    $(".camera-state").innerHTML="<i></i>正在识别";$(".camera-state").title=`浏览器识别 · ${Math.round(performance.now()-frameStart)} ms/帧`;
    uploadLandmarksLoop();
  }catch(error){
    if(generation===cameraRequestGeneration&&trainingRunning){$("#live-cue").textContent="识别暂时中断";$("#live-cue-detail").textContent=error.message}
  }
  finally{
    if(trainingRunning&&generation===cameraRequestGeneration)
      captureTimer=setTimeout(captureLandmarksLoop,Math.max(0,66-(performance.now()-frameStart)));
  }
}

async function uploadLandmarksLoop(){
  if(uploadBusy||browserSelectionBusy||!trainingRunning||!LANDMARK_QUEUE.length)return;
  uploadBusy=true;
  const generation=cameraRequestGeneration,id=visionSessionId;
  const batch=LANDMARK_QUEUE.splice(0,MAX_BATCH);
  try{
    const response=await fetch(`${VISION_BASE}/${id}/landmarks`,{
      method:"POST",headers:visionHeaders({"Content-Type":"application/json"}),
      body:JSON.stringify({frames:batch}),signal:AbortSignal.timeout(20000)});
    const result=await response.json();
    if(!response.ok){const error=new Error(result.error||"识别失败");error.status=response.status;throw error}
    if(generation===cameraRequestGeneration&&trainingRunning){
      updateLiveResult(result,{skipOverlay:true});showBrowserLockStatus();
      if(result.training_progress?.status==="completed"){await stopLiveTraining();return}
    }
  }catch(error){
    if(generation===cameraRequestGeneration&&trainingRunning&&error.status===404){expireVisionSession();return}
    if(generation===cameraRequestGeneration&&trainingRunning){$("#live-cue").textContent="识别暂时中断";$("#live-cue-detail").textContent=error.message}
  }
  finally{
    uploadBusy=false;
    // 队列里还有就接着发，保持单飞，避免乱序到达
    if(trainingRunning&&generation===cameraRequestGeneration&&LANDMARK_QUEUE.length)setTimeout(uploadLandmarksLoop,0);
  }
}

function startLandmarksPipeline(){browserLock.reset();browserSubject=null;LANDMARK_QUEUE.length=0;uploadBusy=false;captureLandmarksLoop()}

function sendVisionFrame(){return VISION_MODE==="browser"?startLandmarksPipeline():VISION_MODE==="remote"?startRemoteFrames():sendCameraFrame()}

let localEncoder=null;
async function sendCameraFrame(){
  if(!trainingRunning||frameBusy)return;
  const video=$("#training-video");if(video.readyState<2){trainingTimer=setTimeout(sendCameraFrame,180);return}
  frameBusy=true;const generation=cameraRequestGeneration,id=visionSessionId,frameStart=performance.now();
  let retryDelay=0;
  try{
    const maxWidth=960,scale=Math.min(1,maxWidth/video.videoWidth,maxWidth/video.videoHeight);const width=Math.round(video.videoWidth*scale),height=Math.round(video.videoHeight*scale);if(captureCanvas.width!==width)captureCanvas.width=width;if(captureCanvas.height!==height)captureCanvas.height=height;
    captureCanvas.getContext("2d").drawImage(video,0,0,captureCanvas.width,captureCanvas.height);
    const timestamp_s=(frameStart-captureStart)/1000;
    const encodeStart=performance.now();localEncoder ||= new FrameEncoder();
    const blob=await localEncoder.encode(captureCanvas),encodeEnd=performance.now();
    if(generation!==cameraRequestGeneration||!trainingRunning)return;
    if(!blob)throw new Error("画面编码失败");
    const response=await fetch(`${VISION_BASE}/${id}/frame`,{method:"POST",headers:visionHeaders({"Content-Type":"image/jpeg","X-Capture-Time":String(timestamp_s)}),body:blob,signal:AbortSignal.timeout(15000)});
    const result=await response.json();if(!response.ok){const error=new Error(result.error||"识别失败");error.status=response.status;throw error}
    if(generation===cameraRequestGeneration&&trainingRunning){const received=performance.now();updateLiveResult(result);
      const sample={encode_ms:encodeEnd-encodeStart,request_ms:received-encodeEnd,server_ms:result.processing_ms,render_ms:performance.now()-received,total_ms:performance.now()-frameStart};
      const samples=window.__posePerformance ||= [];samples.push(sample);if(samples.length>120)samples.shift();
      $(".camera-state").title=`编码 ${Math.round(sample.encode_ms)} ms；请求 ${Math.round(sample.request_ms)} ms（含服务处理 ${sample.server_ms??"未知"} ms）；绘制 ${Math.round(sample.render_ms)} ms`;
      $(".camera-state").innerHTML="<i></i>正在识别";$(".camera-state").dataset.perf=`${result.backend} · ${Math.round(performance.now()-frameStart)} ms/帧`;
      if(result.training_progress?.status==="completed")await stopLiveTraining();
    }
  }catch(error){if(generation===cameraRequestGeneration&&trainingRunning&&error.status===404){expireVisionSession();return}retryDelay=500;if(generation===cameraRequestGeneration&&trainingRunning){$("#pose-overlay").getContext("2d").clearRect(0,0,$("#pose-overlay").width,$("#pose-overlay").height);$("#live-cue").textContent="识别暂时中断";$("#live-cue-detail").textContent=error.message}}
  finally{frameBusy=false;if(trainingRunning&&generation===cameraRequestGeneration)trainingTimer=setTimeout(sendCameraFrame,Math.max(retryDelay,50-(performance.now()-frameStart)))}
}

let surfaceSelection=null;
$("#calibrate-surface").addEventListener("click",()=>{
 if(!trainingRunning||activeExercise.id!=="supine")return;
 surfaceSelection=[];showToast("在同一侧面床沿上先点头端，再点脚端，参考线不能太短。");
});
document.addEventListener("click",async event=>{
 const b=event.target.closest("[data-sts-stage]");if(!b||!trainingRunning||activeExercise.id!=="stand")return;
 try{await visionApi(`/${visionSessionId}/sts-calibration`,{stage:b.dataset.stsStage,setup:{seat_height_cm:$("#sts-seat").value?Number($("#sts-seat").value):null,cushion:$("#sts-cushion").checked,foot_position:$("#sts-feet").value,assistance:$("#sts-assistance").value}});showToast("请按画面提示保持姿势，等待标定完成")}catch(e){showToast(e.message)}
});
$("#squat-confirm").addEventListener("click",async()=>{
 if(!trainingRunning||activeExercise.id!=="squat")return;
 try{await visionApi(`/${visionSessionId}/squat-setup`,{support:$("#squat-support").value,support_confirmed:$("#squat-support-confirmed").checked,foot_position:$("#squat-feet").value});showToast("请扶稳并舒适站立2秒，等待标定完成")}catch(e){showToast(e.message)}
});
async function startLiveTraining(){
 if(activeExercise.id==="stand"&&visualPlan&&activeExercise.ruleVersion!=="sts_v0.1_dual_baseline"){showToast("坐站需要康复师按新版双基线规则重新发布方案。");return}
 if(activeExercise.id==="squat"&&visualPlan&&activeExercise.ruleVersion!=="squat_v0.1_joint"){showToast("微蹲需要康复师按新版膝屈曲规则重新发布方案。");return}
 $("#squat-setup").hidden=activeExercise.id!=="squat";$("#squat-support-confirmed").checked=false;
 $("#sts-setup").hidden=activeExercise.id!=="stand";
 if(activeExercise.id==="supine"&&visualPlan&&activeExercise.ruleVersion!=="slr_v0.1_surface"){showToast("此动作仍是旧版相对起始角方案，请康复师按床面角标准重新发布。");return}
 surfaceSelection=null;
 $("#calibrate-surface").hidden=activeExercise.id!=="supine";
  const requestGeneration=++cameraRequestGeneration;
  if(VISION_MODE==="remote"){$("#live-cue-detail").textContent="画面将临时上传服务器，由与本地相同的模型分析；识别画面可能有网络延迟。";}
  const button=$("#start-training");button.disabled=true;button.textContent="正在启动摄像头…";
  try{
    activePrescriptionSnapshot={id:visualPlan?.id??null,requirements:visualPlan?structuredClone(visualPlan):null,exercise_id:activeExercise.id,sets:activeExercise.groups,reps:activeExercise.reps,targets:structuredClone(activeExercise.targets||defaultTargets(activeExercise.id))};
    if(VISION_MODE==="browser"){
      button.textContent="正在准备识别模型…";
      $("#live-cue").textContent="正在准备识别模型";
      $("#live-cue-detail").textContent="首次使用需要下载约 20MB 的识别模型，之后会被浏览器缓存。";
      await ensurePoseWorker();
      button.textContent="正在启动摄像头…";
    }
    const requestedStream=await navigator.mediaDevices.getUserMedia({video:{width:{ideal:1280},height:{ideal:720}},audio:false});
    if(requestGeneration!==cameraRequestGeneration){requestedStream.getTracks().forEach(track=>track.stop());return}
    cameraStream=requestedStream;
    const video=$("#training-video");video.srcObject=cameraStream;await video.play();
    const started=await visionApi("/start",{backend:VISION_MODE==="browser"?"browser":"rtmpose",required_reference:VISION_MODE==="remote"?RTM_REFERENCE:undefined,rule_version:activeExercise.id==="supine"?"slr_v0.1_surface":activeExercise.id==="stand"?"sts_v0.1_dual_baseline":activeExercise.id==="squat"?"squat_v0.1_joint":null,exercise:EXERCISE_TO_VISION[activeExercise.id],side:$("#training-side").value,sets:activeExercise.groups,reps:activeExercise.reps,targets:activeExercise.targets||defaultTargets(activeExercise.id)});
    if(requestGeneration!==cameraRequestGeneration){await visionApi(`/${started.session_id}/stop`,{});return}
    trainingOwner={userId:currentUser.id,exerciseId:activeExercise.id,clientId:started.session_id};captureStart=performance.now();visionSessionId=started.session_id;trainingRunning=true;startTrainingVideo(trainingOwner);$(".camera-stage").classList.add("live");$(".camera-state").innerHTML="<i></i>识别已连接";button.disabled=false;button.textContent="结束本次训练";sendVisionFrame();
  }catch(error){cameraStream?.getTracks().forEach(track=>track.stop());cameraStream=null;button.disabled=false;button.textContent="重新允许摄像头";$("#live-cue").textContent="无法开始识别";$("#live-cue-detail").textContent=cameraErrorText(error)}
}

function cameraErrorText(error){
  const name=error?.name||"";
  if(name==="NotAllowedError"||/permission/i.test(error?.message||""))return "摄像头权限被拒绝。请在浏览器地址栏左侧允许使用摄像头，再点「重新允许摄像头」";
  if(name==="NotFoundError")return "没有找到摄像头，请接好摄像头后重试";
  if(name==="NotReadableError")return "摄像头正被其他程序占用，关掉后重试";
  return error?.message||"摄像头启动失败，请重试";
}

async function stopLiveTraining(){
  if(stoppingTraining)return stoppingTraining;
  stoppingTraining=finishLiveTraining().finally(()=>{stoppingTraining=null});
  return stoppingTraining;
}
async function finishLiveTraining(){
  if(VISION_MODE==="remote"){remoteCapturing=false;clearTimeout(remoteTimer);clearTimeout(remoteWatchdog);if(remoteFrames)await remoteFrames.finish()}
  const videoFinished=finishTrainingVideo();
  cameraRequestGeneration++;trainingRunning=false;clearTimeout(trainingTimer);clearTimeout(captureTimer);LANDMARK_QUEUE.length=0;const id=visionSessionId;visionSessionId=null;cameraStream?.getTracks().forEach(track=>track.stop());cameraStream=null;$("#training-video").srcObject=null;$(".camera-stage").classList.remove("live");$("#pose-overlay").getContext("2d").clearRect(0,0,$("#pose-overlay").width,$("#pose-overlay").height);$(".camera-state").innerHTML="<i></i>摄像头已停止";
  const owner=trainingOwner;trainingOwner=null;
  let result=null;if(id){try{result=await visionApi(`/${id}/stop`,{})}catch(error){showToast(error.message)}}
  const button=$("#start-training");button.disabled=false;button.textContent="允许摄像头并开始识别";
  if(VISION_MODE==="remote"&&(remoteFrames?.failed||remoteFrames?.dropped)&&result?.brief_report){
    result.brief_report.suggestions.unshift("本次发生网络中断或跳过拥塞画面，次数仅代表已识别部分，不能判断完整训练完成情况。");
  }
  await videoFinished;
  if(result&&owner&&currentUser?.id===owner.userId){
    result._sync={...owner,status:"pending"};
    const completedExercise=exercises.find(ex=>ex.id===owner.exerciseId);
    if(completedExercise)completedExercise.done=result.training_session?.progress?.status==="completed";renderExercises();
    lastTrainingReport=result;
    rememberFeedback(owner.exerciseId,result,owner.userId);
    $("#view-last-report").hidden=false;
    showTrainingReport(result);
    result.training_session.prescription_snapshot=activePrescriptionSnapshot;
    await saveTrainingReport(result);
  }
  return result;
}

async function closeTraining(){await stopLiveTraining();$("#training-screen").classList.remove("active");$("#training-screen").setAttribute("aria-hidden","true");document.body.classList.remove("training-open")}

async function toggleLiveTraining(){if(trainingRunning)await stopLiveTraining();else await startLiveTraining()}

function showToast(message){const toast=$("#toast");toast.textContent=message;toast.classList.add("show");setTimeout(()=>toast.classList.remove("show"),2600)}

async function loadCareConnections(){
  if(!currentUser)return;
  const uid=currentUser.id,therapist=currentUser.role==="therapist";
  $("#care-title").textContent=therapist?"我的患者":"我的康复师";
  $("#care-search-title").textContent=therapist?"查找患者":"查找康复师";
  $("#care-my-account").textContent=`${currentUser.name} · ${currentUser.username}`;
  $("#care-status").textContent="正在读取关联和申请…";
  $("#care-linked").innerHTML="";$("#care-requests").innerHTML="";
  try{
    const data=await api("/care/connections");if(currentUser?.id!==uid)return;
    $("#care-linked").innerHTML=data.connections.length?data.connections.map(r=>`<div class="plain-row"><b>${escapeHtml(therapist?r.patient_name:r.therapist_name)}</b><span>已关联</span><button class="text-button" data-care-unlink="${r.patient_id}">解除关联</button></div>`).join(""):"<p>暂无关联。可以在上方查找对方并发起申请。</p>";
    $("#care-requests").innerHTML=data.requests.length?data.requests.map(r=>{
      const incoming=r.recipient_id===uid;
      return `<div class="report-set"><b>${escapeHtml(incoming?r.sender_name:r.recipient_name)}</b><p>${incoming?"对方向你发起关联申请":"已发出，等待对方接受"} · ${escapeHtml(r.created_at)}</p>${incoming?`<button class="primary-button" data-care-action="accept" data-care-request="${r.id}">接受关联</button> <button class="secondary-button" data-care-action="reject" data-care-request="${r.id}">拒绝</button>`:`<button class="secondary-button" data-care-action="cancel" data-care-request="${r.id}">撤回申请</button>`}</div>`;
    }).join(""):"<p>没有待处理的申请。</p>";
    $("#care-status").textContent="已更新。患者暂时只能关联一位主责康复师。";
  }catch(error){if(currentUser?.id===uid)$("#care-status").textContent=`加载失败：${error.message}`}
}

$("#care-refresh").addEventListener("click",loadCareConnections);
$("#care-search-form").addEventListener("submit",async event=>{
  event.preventDefault();if(!currentUser)return;const uid=currentUser.id,button=event.currentTarget.querySelector('[type="submit"]');
  button.disabled=true;$("#care-search-results").innerHTML="";$("#care-status").textContent="正在查找…";
  try{
    const data=await api("/care/search",{method:"POST",body:{account:$("#care-search-account").value.trim()}});if(currentUser?.id!==uid)return;
    $("#care-search-results").innerHTML=data.users.length?data.users.map(u=>`<div class="plain-row"><b>${escapeHtml(u.display_name)}</b><span>${u.role==="therapist"?"康复师账号":"患者账号"}</span><button class="primary-button" data-care-invite="${u.id}">申请关联</button></div>`).join(""):"<p>未找到对应身份的账号。请确认输入完整、选择了对方的注册手机号或邮箱，并且对方已完成注册。</p>";
    $("#care-status").textContent="查找完成。请核对姓名后发起申请。";
  }catch(error){if(currentUser?.id===uid)$("#care-status").textContent=error.message}
  finally{button.disabled=false}
});
$("#care-connections").addEventListener("click",async event=>{
  const button=event.target.closest('[data-care-invite],[data-care-action],[data-care-unlink]');if(!button||!currentUser)return;
  const uid=currentUser.id;
  if(button.dataset.careUnlink&&!window.confirm("解除后，原康复师将失去关联访问权限，现有进行中的计划会暂停。确定解除吗？"))return;
  button.disabled=true;
  try{
    if(button.dataset.careInvite)await api("/care/requests",{method:"POST",body:{user_id:Number(button.dataset.careInvite)}});
    else if(button.dataset.careUnlink)await api(`/care/connections/${button.dataset.careUnlink}`,{method:"DELETE"});
    else await api(`/care/requests/${button.dataset.careRequest}/respond`,{method:"POST",body:{action:button.dataset.careAction}});
    if(currentUser?.id!==uid)return;
    $("#care-search-results").innerHTML="";await loadCareConnections();
    try{await syncBackendData()}catch(error){showToast(`关联已更新，工作台加载失败：${error.message}`)}
  }catch(error){if(currentUser?.id===uid)$("#care-status").textContent=error.message}
  finally{button.disabled=false}
});

renderExercises(); renderFeedback(); renderTherapist();

document.addEventListener("click",async event=>{
  const demo=event.target.closest("[data-demo-account]"); if(demo){const user=demoUsers.find(item=>item.key===demo.dataset.demoAccount);if(user){setRole("login",user.role);$("#login-account").value=user.account;$("#login-password").value=user.password;$("#login-error").textContent=""}}
  const loginRole=event.target.closest("[data-login-role]");if(loginRole)setRole("login",loginRole.dataset.loginRole);
  const registerRole=event.target.closest("[data-register-role]");if(registerRole)setRole("register",registerRole.dataset.registerRole);
  if(event.target.closest("#show-register"))showAuthScreen("register");
  if(event.target.closest("#show-login"))showAuthScreen("login");
  const nav=event.target.closest("[data-page]"); if(nav)gotoPage(nav.dataset.page);
  const direct=event.target.closest("[data-goto]"); if(direct)gotoPage(direct.dataset.goto);
  const training=event.target.closest("[data-train]"); if(training)openGuide(training.dataset.train);
  const feedback=event.target.closest("[data-feedback]"); if(feedback)renderFeedback(Number(feedback.dataset.feedback));
  if(event.target.closest("[data-close-guide]"))$("#exercise-guide-dialog").close();
  if(event.target.closest("#confirm-training")&&pendingTrainingId){$("#exercise-guide-dialog").close();openTraining(pendingTrainingId);pendingTrainingId=null}
  if(event.target.closest("[data-close-training]"))await closeTraining();
  if(event.target.closest("#start-training"))await toggleLiveTraining();
  if(event.target.closest("#open-messages"))openMessages();
  if(event.target.closest("[data-close-messages]"))$("#message-dialog").close();
  const chat=event.target.closest("[data-chat-patient]");if(chat)openMessages(chat.dataset.chatPatient);
  const contact=event.target.closest("[data-message-contact]");if(contact)openMessages(contact.dataset.messageContact);
  const rule=event.target.closest(".rule-summary"); if(rule){const item=rule.parentElement;item.classList.toggle("open");rule.querySelector("i").textContent=item.classList.contains("open")?"−":"+"}
  const picker=event.target.closest(".picker-item"); if(picker){picker.classList.toggle("selected");picker.querySelector("button").textContent=picker.classList.contains("selected")?"✓":"+";renderSelectedSummary();$("#save-state").textContent="有未保存更改"}
  if(event.target.closest("#save-draft"))await persistVisualPlan("draft");
  if(event.target.closest("#publish-plan"))await persistVisualPlan("published");
  if(event.target.closest("#logout")){closeTrainingPlayback();await closeTraining();clearInterval(reportPoll);try{await api("/auth/logout",{method:"POST"})}catch(error){}apiToken="";sessionStorage.removeItem("kangshifu_api_token");await closeTraining();if($("#message-dialog").open)$("#message-dialog").close();$("#training-report-dialog").close();lastTrainingReport=null;$("#view-last-report").hidden=true;currentUser=null;$("#app-shell").classList.add("hidden");showAuthScreen("login");$("#login-form").reset();setRole("login","patient");$("#login-error").textContent=""}
  if(event.target.closest("#mobile-menu"))$(".sidebar").classList.toggle("mobile-open");
  if(event.target.closest(".sidebar-backdrop"))$(".sidebar").classList.remove("mobile-open");
});

$("#login-form").addEventListener("submit",async event=>{
  event.preventDefault();
  const account=$("#login-account").value.trim();
  const password=$("#login-password").value;
  const button=event.currentTarget.querySelector('[type="submit"]');button.disabled=true;
  $("#login-error").textContent="正在登录…";
  try{
    const result=await api("/auth/login",{method:"POST",auth:false,body:{username:account,password}});
    if(result.user.role!==selectedLoginRole){
      await api("/auth/logout",{method:"POST",auth:false,headers:{Authorization:`Bearer ${result.token}`}}).catch(()=>{});
      throw new Error("账号身份与所选登录端不一致，请切换登录身份");
    }
    apiToken=result.token;sessionStorage.setItem("kangshifu_api_token",apiToken);
    $("#login-error").textContent="";$("#login-password").value="";enterApp(apiUser(result.user));
    try{await syncBackendData();showToast("登录成功")}catch(error){showToast(`已登录，工作台数据暂未加载：${error.message}`)}
  }catch(error){if(error.code==="PASSWORD_RESET_REQUIRED")openPasswordReset(account);apiToken="";sessionStorage.removeItem("kangshifu_api_token");$("#login-error").textContent=error instanceof TypeError?"暂时连不上服务器，请检查网络后重试。":error.status===401?"账号或密码不正确。旧版仅在浏览器保存的账号，请先重新注册。":error.message}
  finally{button.disabled=false}
});

$("#register-form").addEventListener("submit",async event=>{
  event.preventDefault();
  const name=$("#register-name").value.trim();const identifier=$("#register-account").value.trim().toLowerCase();const password=$("#register-password").value;
  if(!name){$("#register-error").textContent="请填写用户名。";return}
  if(!(/^[1][3-9]\d{9}$/.test(identifier)||/^\S+@\S+\.\S+$/.test(identifier))){$("#register-error").textContent="请输入有效的手机号或邮箱。";return}
  if(name.length>50){$("#register-error").textContent="姓名不超过50字。";return}
  if(!passwordCompliant(password)){$("#register-error").textContent="密码须为5–15位，且同时包含字母和数字，请重新设置。";return}
  if(password!==$("#register-confirm").value){$("#register-error").textContent="两次输入的密码不一致。";return}
  const button=event.currentTarget.querySelector('[type="submit"]');button.disabled=true;
  $("#register-error").textContent="正在创建账号…";
  try{
    const result=await api("/auth/register",{method:"POST",auth:false,body:{username:identifier,password,display_name:name,role:selectedRegisterRole}});
    $("#register-error").textContent="";$("#register-form").reset();setRole("register","patient");setRole("login",result.role);showAuthScreen("login");$("#login-account").value=result.username;$("#login-password").value="";$("#login-error").textContent="注册成功，请输入密码登录。";showToast("注册成功");
  }catch(error){$("#register-error").textContent=error instanceof TypeError?"暂时连不上服务器，请检查网络后重试。":error.message}
  finally{button.disabled=false}
});

$("#message-form").addEventListener("submit",event=>{
  event.preventDefault();const input=$("#message-input");const text=input.value.trim();if(!text)return;
  messages.push({id:`message-${Date.now()}`,patient:activePatientName,from:currentUser.role,text,time:new Date().toLocaleTimeString("zh-CN",{hour:"2-digit",minute:"2-digit",hour12:false}),readByPatient:currentUser.role==="patient",readByTherapist:currentUser.role==="therapist"});
  input.value="";saveMessages();renderMessages();updateMessageBadge();showToast("消息已发送，对方将收到提醒");
});

$("#condition-select").addEventListener("change",event=>{$("#summary-condition").textContent=event.target.value;$("#save-state").textContent="有未保存更改";showToast(`已切换为${event.target.value}方案，可重新选择推荐动作`)});
$("#theme-toggle").addEventListener("click",()=>{const dark=document.documentElement.dataset.theme!=="dark";document.documentElement.dataset.theme=dark?"dark":"light";showToast(dark?"已切换深色模式":"已切换浅色模式")});
$("#library-filter").addEventListener("click",event=>{if(event.target.tagName!=="BUTTON")return;$$("#library-filter button").forEach(x=>x.classList.remove("active"));event.target.classList.add("active");showToast(`${event.target.textContent}筛选已应用`)});
document.addEventListener("input",event=>{
  const doseField=event.target.closest("[data-dose-field]");if(!doseField||doseField.value==="")return;
  const ex=exercises.find(item=>item.id===doseField.dataset.exerciseId);if(!ex)return;
  const limit=doseField.dataset.doseField==="groups"?20:100;ex[doseField.dataset.doseField]=Math.max(1,Math.min(limit,Math.round(Number(doseField.value)||1)));
  const summary=doseField.closest(".exercise-card")?.querySelector(".exercise-meta span");if(summary)summary.textContent=`${ex.groups} 组 × ${ex.reps} 次`;ex.done=false;saveDosePreferences();updateDurationEstimates();
});
document.addEventListener("change",event=>{
  const doseField=event.target.closest("[data-dose-field]");
  if(doseField){const ex=exercises.find(item=>item.id===doseField.dataset.exerciseId);if(ex){const limit=doseField.dataset.doseField==="groups"?20:100;const value=Math.max(1,Math.min(limit,Math.round(Number(doseField.value)||1)));ex[doseField.dataset.doseField]=value;ex.done=false;saveDosePreferences();renderExercises();showToast(`${ex.name}已调整为 ${ex.groups} 组，每组 ${ex.reps} 次`)}return}
  if(event.target.closest("#therapist-plans"))$("#save-state").textContent="有未保存更改";
});

// Selection uses the same contain-fit transform as the displayed frame.
$("#pose-overlay").addEventListener("click",async event=>{
  const r=lastVisionResult;if(!trainingRunning||!r?.subject||(!surfaceSelection&&r.subject.status==="locked"))return;
  const c=event.currentTarget,b=c.getBoundingClientRect(),scale=Math.min(b.width/c.width,b.height/c.height);
  const displayedX=(event.clientX-b.left-(b.width-c.width*scale)/2)/scale;
  const x=previewFlipped?c.width-displayedX:displayedX;
  const y=(event.clientY-b.top-(b.height-c.height*scale)/2)/scale;
  if(x<0||y<0||x>c.width||y>c.height)return;
  if(surfaceSelection){
    if(r.subject.status!=="locked"){showToast("请先锁定训练者，再标定床面");surfaceSelection=null;return}
    surfaceSelection.push([x/c.width,y/c.height]);
    if(surfaceSelection.length===1){showToast("再点击床沿靠脚端的第二点");return}
    try{await visionApi(`/${visionSessionId}/surface`,{points:surfaceSelection});showToast("床面已标定，请放平训练腿并保持2秒");surfaceSelection=null}catch(e){surfaceSelection=[];showToast(e.message)}return;
  }
  try{if(VISION_MODE==="browser")await selectBrowserSubject(x/c.width,y/c.height);else await visionApi(`/${visionSessionId}/subject`,{x,y})}catch(e){if(e.status===404)expireVisionSession();else showToast(e.message)}
});
$("#reselect-subject").addEventListener("click",async()=>{
  if(!trainingRunning)return;
  try{if(VISION_MODE==="browser")await selectBrowserSubject(null,null);else await visionApi(`/${visionSessionId}/subject`,{reset:true})}catch(e){if(e.status===404)expireVisionSession();else showToast(e.message)}
});

function showTrainingReport(result){
  const report=result?.brief_report;
  if(!report){showToast("本次没有生成训练简报，请刷新页面后重试");return}
  $("#report-overview").textContent=`${report.exercise} · ${report.side}：识别完成 ${report.completed_reps} / 计划 ${report.target_reps} 次`;
  $("#report-sets").innerHTML=report.sets.map(row=>`<section class="report-set"><h3>第 ${row.set} 组 · ${escapeHtml(row.status)}</h3><p>识别完成 ${row.completed_reps} / ${row.target_reps} 次；其中 ${row.angle_hold_met_reps} 次${result.training_session?.rule_version==="squat_v0.1_joint"?"完成本次微蹲目标":"达到角度与保持目标"}。</p><p>${escapeHtml(row.finding)}</p>${row.needs_review_reps?`<small>${row.needs_review_reps} 次动作有部分指标无法判断，需复核。</small>`:""}</section>`).join("");
  if(Number.isFinite(report.attempted_reps)){
    $("#report-overview").textContent+=`；尝试 ${report.attempted_reps} 次，目标完成 ${report.goal_reps} 次，未完成 ${report.incomplete_attempts} 次，无法评价 ${report.unable_to_evaluate} 次`;
    if(result.rule_version==="sts_v0.1_dual_baseline"||result.training_session?.rule_version==="sts_v0.1_dual_baseline")$("#report-sets").innerHTML+=(result.repetitions||[]).map(r=>`<section class="report-set"><h3>第 ${r.index} 次坐站</h3><p>起立 ${fmt(r.rise_to_stand_s)} 秒 · 坐回 ${fmt(r.sit_down_s)} 秒 · 连续站稳 ${fmt(r.target_hold_s)} 秒</p><p>站姿膝角 ${fmt(r.stand_knee_deg)}° · 髋上升峰值 ${fmt(r.hip_rise_peak)} · 前倾峰值 ${fmt(r.trunk_forward_peak_deg)}°（仅记录）</p><p>辅助方式：${escapeHtml({none:"无辅助",thighs:"手扶大腿",armrests:"手扶固定扶手"}[r.setup?.assistance]||"未记录")}；座面接触未验证。</p></section>`).join("");
  }

  if(result.rule_version==="squat_v0.1_joint"||result.training_session?.rule_version==="squat_v0.1_joint"){
    $("#report-sets").innerHTML+=(result.repetitions||[]).map(r=>`<section class="report-set"><h3>第 ${r.index} 次微蹲 · ${r.goal_met?"目标完成":"目标未完成"}</h3><p>屈膝峰值 ${fmt(r.knee_flexion_peak_deg)}° · 连续保持 ${fmt(r.target_hold_s)} 秒 · 起身 ${fmt(r.rise_s)} 秒</p><p>髋下降 / 小腿长 ${fmt(r.hip_drop_peak,3)} · ${r.depth_exceeded?"曾超出设定深度，本次保留记录":"未记录持续超深事件"}</p><p>脚跟接触、左右负重与支撑力未验证。</p></section>`).join("");
  }
  $("#report-suggestions").innerHTML=report.suggestions.map(text=>`<li>${escapeHtml(text)}</li>`).join("");
  $("#report-scope").textContent=report.scope;
  const metrics=buildFeedbackRecord(result._sync?.exerciseId||"",result)?.metrics||[];
  $("#report-metrics").innerHTML=metrics.map(m=>`<div class="metric-row"><span>${escapeHtml(m[0])}</span><b>${escapeHtml(m[1])}</b><small>${escapeHtml(m[2])}</small></div>`).join("");
  $("#report-video-actions").innerHTML=result._sync?.id?videoReportButton({id:result._sync.id,client_id:result._sync.clientId,video:result._sync.video}):"录像将随报告保存后上传。";
  $("#report-delivery").textContent=reportDeliveryText(result);
  $("#retry-report-sync").hidden=!(result._sync?.status==="failed");
  $("#go-feedback").hidden=currentUser?.role!=="patient";
  if(!$("#training-report-dialog").open)$("#training-report-dialog").showModal();
}
$("#close-training-report").addEventListener("click",()=>$("#training-report-dialog").close());
$("#view-last-report").addEventListener("click",()=>showTrainingReport(lastTrainingReport));
$("#download-training-report").addEventListener("click",()=>{
  if(!lastTrainingReport)return;
  const blob=new Blob(["\ufeff"+reportDownloadText(lastTrainingReport)],{type:"text/plain;charset=utf-8"});
  const url=URL.createObjectURL(blob),a=document.createElement("a");a.href=url;a.download=`康师复训练简报-${new Date().toISOString().slice(0,10)}.txt`;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
});

function pendingReportKey(uid){return `kangji_pending_reports_v1:${uid}`}
function pendingReports(uid){try{return JSON.parse(sessionStorage.getItem(pendingReportKey(uid))||"{}")}catch(e){return {}}}
function cachePending(result,remove=false){
  const meta=result._sync;if(!meta)return;
  try{const pending=pendingReports(meta.userId);if(remove)delete pending[meta.clientId];else pending[meta.clientId]=result;sessionStorage.setItem(pendingReportKey(meta.userId),JSON.stringify(pending))}
  catch(e){showToast("浏览器暂存不足，请保持本页并重试保存，或下载备份")}
}
function reportDeliveryText(result){
  const m=result?._sync;
  if(!m||m.status==="pending")return "本次反馈已生成，正在保存到账号并同步给已关联康复师…";
  if(m.status==="failed")return `尚未保存到账号，康复师暂不可查看：${m.error||"请重试"}。本标签页保留待同步结果。`;
  const d=m.delivery;
  if(d?.status!=="available")return "已保存到账号并同步动作反馈；尚未关联康复师。接受关联后，对方可查看这些历史报告。";
  return `已同步给${d.therapist_name||"已关联康复师"}，${d.read_at?"康复师已查看":"康复师端可查看，尚未查看"}。`;
}
function reportDownloadText(result){
  const b=result.brief_report;
  return [b.title||"训练简报",`${b.exercise} · ${b.side}`,`识别 ${b.completed_reps}/${b.target_reps} 次`,...b.sets.map(g=>`第${g.set}组 ${g.completed_reps}/${g.target_reps}次：${g.finding}`),"下次留意",...b.suggestions,b.scope,reportDeliveryText(result)].join("\n");
}
function resultFromServer(row){
  return {...row.result,_sync:{status:"saved",id:row.id,userId:currentUser.id,exerciseId:row.exercise_id,clientId:row.client_id,savedAt:row.created_at,delivery:row.delivery,video:row.video}};
}
function rememberServerFeedback(row){
  const record=buildFeedbackRecord(row.exercise_id,row.result);if(!record)return;
  record.savedAt=row.created_at.replace(" ","T");record.serverId=row.id;
  const existing=feedbackReports[row.exercise_id];
  if(!existing||new Date(record.savedAt)>=new Date(existing.savedAt)||existing.serverId===row.id)feedbackReports[row.exercise_id]=record;
  try{sessionStorage.setItem(feedbackStorageKey(currentUser.id),JSON.stringify(feedbackReports))}catch(e){}
  renderFeedback();
}
async function saveTrainingReport(result){
  const meta=result._sync;if(!meta||currentUser?.role!=="patient"||currentUser.id!==meta.userId||meta.status==="saving")return;
  meta.status="saving";cachePending(result);
  $("#retry-report-sync").hidden=true;$("#report-delivery").textContent="正在保存到账号并同步…";
  try{
    const payload=Object.fromEntries(["brief_report","repetitions","feedback_events","training_session"].map(k=>[k,result[k]]));
    const row=await api("/training-reports",{method:"POST",body:{client_id:meta.clientId,exercise_id:meta.exerciseId,result:payload}});
    if(currentUser?.id!==meta.userId)return;
    Object.assign(meta,{status:"saved",id:row.id,delivery:row.delivery,video:row.video});cachePending(result,true);
    const local=feedbackReports[meta.exerciseId];
    if(local?.brief===result.brief_report){local.serverId=row.id;local.savedAt=row.created_at.replace(" ","T")}
    rememberServerFeedback(row);await uploadTrainingVideo(row);await loadServerReports();
  }catch(error){if(currentUser?.id!==meta.userId)return;meta.status="failed";meta.error=error.message;cachePending(result)}
  if(lastTrainingReport===result){$("#report-delivery").textContent=reportDeliveryText(result);$("#retry-report-sync").hidden=meta.status!=="failed"}
}
async function loadServerReports(){
  if(!currentUser)return;
  if(reportsLoading){reportsReloadRequested=true;return}
  reportsLoading=true;const uid=currentUser.id,isPatient=currentUser.role==="patient";
  const target=isPatient?"patient":"therapist";
  try{
    const selectedPatient=isPatient?null:reportPatientFilter;
    const data=await api("/training-reports"+(selectedPatient?`?patient_id=${selectedPatient.id}`:""));if(currentUser?.id!==uid||(!isPatient&&selectedPatient!==reportPatientFilter))return;
    $("#"+target+"-report-status").textContent=data.reports.length?`${selectedPatient?selectedPatient.name+" · ":""}共 ${data.reports.length} 份训练报告${data.reports.length>=50?"（显示最近 50 份）":""}`:"";
    $("#"+target+"-report-list").innerHTML=data.reports.length?data.reports.map(row=>`<section class="report-set"><h3>${escapeHtml(row.patient_name)} · ${escapeHtml(row.brief_report.exercise)}</h3><p>${escapeHtml(row.created_at)} · ${escapeHtml(row.brief_report.side)} · 识别 ${row.brief_report.completed_reps}/${row.brief_report.target_reps} 次</p><p>${escapeHtml(isPatient?(row.delivery.status==="available"?(row.read_at?"康复师已查看":"已同步给关联康复师，尚未查看"):"已保存，尚未关联康复师"):(row.read_at?"已查看":"未查看"))}</p><button class="secondary-button" data-open-report="${row.id}">查看报告</button> ${videoReportButton(row)}</section>`).join(""):(isPatient?"<div class='report-empty'><p>还没有训练报告。练完一次，报告会自动出现在这里。</p><button class='primary-button' data-goto='patient-home'>去今日训练</button></div>":"<div class='report-empty'><p>关联的患者还没有训练报告。</p></div>");
    if(!isPatient){if(!selectedPatient)$("#report-unread-count").textContent=data.reports.filter(r=>!r.read_at).length||"";return}
    const pending=pendingReports(uid);
    for(const [id,result] of Object.entries(pending)){
      result._sync.status="failed";
      $("#patient-report-list").innerHTML+=`<section class="report-set"><h3>待保存：${escapeHtml(result.brief_report.exercise)}</h3><p>尚未同步到康复师，本标签页有暂存结果。</p><button class="secondary-button" data-retry-report="${escapeHtml(id)}">打开并重试保存</button></section>`;
    }
    const latest=new Map();for(const row of data.reports)if(!latest.has(row.exercise_id))latest.set(row.exercise_id,row);
    const details=await Promise.all([...latest.values()].map(row=>api(`/training-reports/${row.id}`)));
    if(currentUser?.id!==uid)return;
    details.forEach(rememberServerFeedback);
  }catch(error){if(currentUser?.id===uid){$("#"+target+"-report-status").textContent=`报告加载失败：${error.message}。已有的反馈不会丢，可以点刷新重试。`;$("#"+target+"-report-list").innerHTML=""}}
  finally{reportsLoading=false;if(reportsReloadRequested){reportsReloadRequested=false;queueMicrotask(loadServerReports)}}
}
async function openSavedReport(id){
  const uid=currentUser?.id;
  try{
    const row=await api(`/training-reports/${id}`);if(currentUser?.id!==uid)return;
    lastTrainingReport=resultFromServer(row);showTrainingReport(lastTrainingReport);
    if(currentUser.role==="therapist"){
      const read=await api(`/training-reports/${id}/read`,{method:"POST"});
      if(currentUser?.id===uid){lastTrainingReport._sync.delivery=read.delivery;$("#report-delivery").textContent=reportDeliveryText(lastTrainingReport);await loadServerReports()}
    }else{rememberServerFeedback(row);renderFeedback(exercises.findIndex(ex=>ex.id===row.exercise_id))}
  }catch(error){showToast(error.message)}
}
document.addEventListener("click",event=>{
  if(event.target.closest("[data-refresh-reports]"))loadServerReports();
  const open=event.target.closest("[data-open-report]");if(open)openSavedReport(Number(open.dataset.openReport));
  const retry=event.target.closest("[data-retry-report]");if(retry){const result=pendingReports(currentUser.id)[retry.dataset.retryReport];if(result){lastTrainingReport=result;result._sync.status="failed";showTrainingReport(result)}}
});
$("#retry-report-sync").addEventListener("click",()=>{if(lastTrainingReport)saveTrainingReport(lastTrainingReport)});
$("#go-feedback").addEventListener("click",async()=>{$("#training-report-dialog").close();await closeTraining();gotoPage("patient-feedback")});

function videoKey(uid,clientId){return `${uid}:${clientId}`}
function videoStore(action,key,value){
  return new Promise((resolve,reject)=>{
    const request=indexedDB.open("kangji-video-upload",1);
    request.onupgradeneeded=()=>request.result.createObjectStore("pending",{keyPath:"key"});
    request.onerror=()=>reject(request.error);
    request.onsuccess=()=>{const db=request.result,tx=db.transaction("pending",action==="getAll"?"readonly":"readwrite"),store=tx.objectStore("pending");
      const op=action==="put"?store.put(value):action==="delete"?store.delete(key):store.getAll();
      tx.oncomplete=()=>{db.close();resolve(op.result)};tx.onerror=()=>{db.close();reject(tx.error)};
    };
  });
}
async function restoreTrainingVideos(){try{for(const entry of await videoStore("getAll"))pendingVideoFiles.set(entry.key,entry)}catch(e){showToast("录像本地暂存不可用，请训练结束后保持页面直到上传成功")}}
function startTrainingVideo(owner){
  if(typeof MediaRecorder==="undefined"){showToast("此浏览器不支持录像，本次仅生成动作报告，请改用最新版Edge或Chrome");return}
  try{
    const mime=["video/webm;codecs=vp8","video/webm","video/mp4"].find(m=>MediaRecorder.isTypeSupported(m));
    if(!mime)throw Error("浏览器不支持当前录像格式");
    const recorder=new MediaRecorder(cameraStream,{mimeType:mime,videoBitsPerSecond:1000000});
    const record={recorder,owner:{...owner},chunks:[],size:0,started:performance.now(),flipped:previewFlipped};
    record.done=new Promise(resolve=>{record.resolve=resolve});
    recorder.ondataavailable=e=>{if(e.data.size){record.chunks.push(e.data);record.size+=e.data.size;if(record.size>240*1048576&&trainingRunning){showToast("本次录像已达到大小上限，正在结束并保存训练");stopLiveTraining()}}};
    recorder.onerror=()=>{showToast("录像发生错误，结束后请检查视频是否完整");record.error=true};
    recorder.onstop=async()=>{
      try{
        const blob=new Blob(record.chunks,{type:recorder.mimeType.split(";")[0]});
        if(blob.size){const key=videoKey(owner.userId,owner.clientId),entry={key,owner:record.owner,blob,duration_s:(performance.now()-record.started)/1000,preview_flipped:record.flipped,incomplete:!!record.error};pendingVideoFiles.set(key,entry);
          try{await videoStore("put",key,entry)}catch(e){showToast("录像暂存在本页，保存完成前请勿关闭")}
        }
      }finally{record.resolve()}
    };
    trainingRecorder=record;recorder.start(1000);
  }catch(error){trainingRecorder=null;showToast(`无法录制视频：${error.message}。本次仍可生成动作报告。`)}
}
function finishTrainingVideo(){
  const r=trainingRecorder;trainingRecorder=null;if(!r)return Promise.resolve();
  if(r.recorder.state!=="inactive")r.recorder.stop();return r.done;
}
function videoReportButton(row){
  if(row.video?.state==="ready")return `<button class="secondary-button" data-play-training-video="${row.id}">查看视频</button>`;
  const local=currentUser?.role==="patient"&&pendingVideoFiles.has(videoKey(currentUser.id,row.client_id));
  if(local)return `<button class="secondary-button" data-retry-training-video="${row.id}">重试视频上传</button>`;
  return `<span class="report-note">${row.video?"视频尚未上传完成":"无录像"}</span>`;
}
async function videoRequest(path,options={}){
  const response=await fetch(`${API_BASE}${path}`,{...options,headers:{Authorization:`Bearer ${apiToken}`,...options.headers},signal:AbortSignal.timeout(60000)});
  if(!response.ok){const error=await response.json().catch(()=>({}));throw Error(error.error||error.detail||`视频请求失败 ${response.status}`)}
  return response;
}
async function uploadTrainingVideo(row){
  const uid=currentUser?.id,key=videoKey(uid,row.client_id),entry=pendingVideoFiles.get(key);if(!entry||videoUploads.has(key))return;
  videoUploads.add(key);const status=$("#report-video-actions");status.textContent="正在保存训练视频…";
  try{
    if(entry.incomplete)throw Error("录制过程中发生错误，录像可能不完整，已先保存在这台设备上") ;
    if(!entry.sha256){const hash=await crypto.subtle.digest("SHA-256",await entry.blob.arrayBuffer());entry.sha256=Array.from(new Uint8Array(hash),x=>x.toString(16).padStart(2,"0")).join("");await videoStore("put",key,entry).catch(()=>{})}
    const base=`/training-reports/${row.id}/video`;
    const v=await api(base,{method:"POST",body:{mime:entry.blob.type,size:entry.blob.size,sha256:entry.sha256,duration_s:entry.duration_s,preview_flipped:entry.preview_flipped}});
    for(let i=0;v.state!=="ready"&&i<v.chunk_count;i++){
      if(currentUser?.id!==uid)throw Error("账号已切换，请用原患者账号重试");
      await videoRequest(`${base}/chunks/${i}`,{method:"PUT",headers:{"Content-Type":"application/octet-stream"},body:entry.blob.slice(i*v.chunk_size,(i+1)*v.chunk_size)});
      status.textContent=`视频上传中 ${Math.round((i+1)/v.chunk_count*100)}%，请保持页面打开`;
    }
    if(currentUser?.id!==uid)return;
    const ready=await api(base+"/complete",{method:"POST"});row.video=ready;
    pendingVideoFiles.delete(key);await videoStore("delete",key).catch(()=>{});
    if(lastTrainingReport?._sync?.id===row.id)lastTrainingReport._sync.video=ready;
    status.innerHTML=videoReportButton(row);
  }catch(error){if(currentUser?.id===uid)status.innerHTML=`<p>${escapeHtml(error.message)}。报告已保存，视频未完成上传。</p>${videoReportButton(row)}`}
  finally{videoUploads.delete(key)}
}
function closeTrainingPlayback(){
  playbackGeneration++;const player=$("#saved-training-video");player.pause();player.removeAttribute("src");player.load();
  if(playbackUrl)URL.revokeObjectURL(playbackUrl);playbackUrl=null;
  $("#training-video-dialog").close();
}
async function playTrainingVideo(id){
  closeTrainingPlayback();const generation=playbackGeneration,uid=currentUser?.id;
  $("#training-video-dialog").showModal();$("#video-playback-status").textContent="正在加载已保存的视频…";
  try{
    const {video}=await api(`/training-reports/${id}/video`);if(!video||video.state!=="ready")throw Error("本次训练没有已保存的视频");
    const blocks=[];for(let i=0;i<video.chunk_count;i++){
      if(generation!==playbackGeneration||currentUser?.id!==uid)return;
      const response=await videoRequest(`/training-reports/${id}/video/chunks/${i}`);blocks.push(await response.blob());
      if(generation!==playbackGeneration||currentUser?.id!==uid)return;
      $("#video-playback-status").textContent=`视频加载中 ${Math.round((i+1)/video.chunk_count*100)}%`;
    }
    playbackUrl=URL.createObjectURL(new Blob(blocks,{type:video.mime}));const player=$("#saved-training-video");player.src=playbackUrl;player.style.transform=video.preview_flipped?"scaleX(-1)":"none";
    $("#video-playback-status").textContent=`已加载，时长约 ${Math.round(video.duration_s)} 秒。点击播放查看。`;
  }catch(error){if(generation===playbackGeneration)$("#video-playback-status").textContent=error.message}
}
document.addEventListener("click",async event=>{
  const patient=event.target.closest("[data-patient-reports]");if(patient){reportPatientFilter={id:Number(patient.dataset.patientReports),name:patient.dataset.patientName};gotoPage("therapist-reports")}
  if(event.target.closest("#all-patient-reports")){reportPatientFilter=null;loadServerReports()}
  const video=event.target.closest("[data-play-training-video]");if(video)playTrainingVideo(Number(video.dataset.playTrainingVideo));
  const retry=event.target.closest("[data-retry-training-video]");if(retry){try{const row=await api(`/training-reports/${Number(retry.dataset.retryTrainingVideo)}`);await uploadTrainingVideo(row);await loadServerReports()}catch(e){showToast(e.message)}}
});
$("#close-training-video").addEventListener("click",closeTrainingPlayback);
$("#training-video-dialog").addEventListener("cancel",e=>{e.preventDefault();closeTrainingPlayback()});

$("#plan-patient").addEventListener("change",loadPlanEditor);
document.addEventListener("input",e=>{if(e.target.closest("#therapist-plans")){renderSelectedSummary();$("#save-state").textContent="有未保存更改"}});

function passwordCompliant(value){return Array.from(value).length>=5&&Array.from(value).length<=15&&/[A-Za-z]/.test(value)&&/[0-9]/.test(value)}
function openPasswordReset(account){
 $("#password-reset-form").reset();$("#reset-account").value=account;$("#password-reset-error").textContent="";$("#password-reset-dialog").showModal();
}
$("#cancel-password-reset").addEventListener("click",()=>{$("#password-reset-dialog").close();$("#password-reset-form").reset();$("#login-password").value=""});
$("#password-reset-form").addEventListener("submit",async event=>{
 event.preventDefault();const value=$("#reset-new").value;
 if(!passwordCompliant(value)){$("#password-reset-error").textContent="密码须为5–15位，且同时包含字母和数字。";return}
 if(value!==$("#reset-confirm").value){$("#password-reset-error").textContent="两次新密码不一致。";return}
 const button=$("#submit-password-reset");button.disabled=true;
 try{await api("/auth/change-password",{method:"POST",auth:false,body:{username:$("#reset-account").value,old_password:$("#reset-old").value,new_password:value}});
 $("#password-reset-dialog").close();$("#password-reset-form").reset();$("#login-password").value="";apiToken="";sessionStorage.removeItem("kangshifu_api_token");$("#login-error").textContent="密码已更新，请使用新密码登录。";
 }catch(e){$("#password-reset-error").textContent=e.message}finally{button.disabled=false}
});

function resetPatientExercises(){
 let doses={};try{doses=JSON.parse(localStorage.getItem(`kangji_doses:${currentUser.id}`)||'{}')}catch(e){}
 exercises.forEach(ex=>{ex.done=false;ex.planSelected=false;delete ex.targets;ex.recommendedGroups=['supine','squat','stand'].includes(ex.id)?1:2;ex.recommendedReps=['supine','squat','stand'].includes(ex.id)?3:10;
 ex.groups=Math.max(1,Math.min(20,Number(doses[ex.id]?.groups)||ex.recommendedGroups));ex.reps=Math.max(1,Math.min(100,Number(doses[ex.id]?.reps)||ex.recommendedReps));ex.dose=`${ex.groups} 组 × ${ex.reps} 次`;});
}
async function syncSelfSelection(uid){
 const {selection}=await api('/me/training-selection');if(currentUser?.id!==uid)return;
 const signature=JSON.stringify([uid,selection?.condition,selection?.exercise_ids]);
 if(!visualPlan&&signature===selfSelectionSignature)return;
 visualPlan=null;visualPlanUser=null;selfSelectionSignature=signature;selfTrainingSelection=selection;resetPatientExercises();
 const demo=['p.zhang','p.wu','p.zhaomin','p.linyuqing','p.zhouqiming'].includes(currentUser.username);
 const ids=selection?selection.exercise_ids:demo?exercises.map(ex=>ex.id):[];
 patientTrainingSource=selection?.condition?'self':!selection&&demo?'demo':'empty';
 exercises.forEach(ex=>ex.planSelected=ids.includes(ex.id));renderExercises();
 $(".plan-stamp strong").textContent=patientTrainingSource==='self'?'膝骨关节炎 · 自主选择':patientTrainingSource==='demo'?'膝骨关节炎 · 演示项目':'尚未添加病症与动作';
 $(".plan-stamp small").textContent=patientTrainingSource==='demo'?'虚构演示内容，不代表康复师已发布方案':'待康复师确认，不代表诊断或处方';
}
function openTrainingSelection(){
 if(currentUser?.role!=='patient'||visualPlan)return;
 $("#selection-actions").innerHTML=exercises.map(ex=>`<label style="display:block;margin:14px 0"><input type="checkbox" value="${ex.id}" ${selfTrainingSelection?.exercise_ids.includes(ex.id)?'checked':''}> ${ex.name}</label>`).join('');
 $("#selection-error").textContent='';$("#training-selection-dialog").showModal();
}
async function saveTrainingSelection(clear=false){
 const ids=clear?[]:$$('#selection-actions input:checked').map(x=>x.value);
 if(!clear&&!ids.length){$("#selection-error").textContent='请至少选择一个动作';return}
 const uid=currentUser.id;$("#save-training-selection").disabled=true;
 try{await api('/me/training-selection',{method:'PUT',body:{condition:ids.length?'knee_osteoarthritis':null,exercise_ids:ids}});if(currentUser?.id!==uid)return;
 selfSelectionSignature=null;await syncVisualPlan();$("#training-selection-dialog").close();showToast(clear?'已清空自主选择':'已保存自主选择，待康复师确认');
 }catch(e){$("#selection-error").textContent=e.message}finally{$("#save-training-selection").disabled=false}
}
document.addEventListener('click',e=>{if(e.target.closest('[data-add-selection]'))openTrainingSelection()});
$("#save-training-selection").addEventListener('click',()=>saveTrainingSelection());
$("#clear-training-selection").addEventListener('click',()=>saveTrainingSelection(true));
$("#cancel-training-selection").addEventListener('click',()=>$("#training-selection-dialog").close());

function showBrowserLockStatus(){
  if(!browserSubject||browserSubject.status==="locked")return;
  $("#live-cue").textContent=browserSubject.status==="select_subject"?"请点击画面中的患者框，确认训练者":browserSubject.status==="subject_lost_reconfirm"?"训练者已丢失，请重新点击患者框确认":"患者被遮挡或身份不确定，暂停计数，等待恢复";
}
async function selectBrowserSubject(x,y){
  if(browserSelectionBusy)return;
  browserSelectionBusy=true;browserLockEpoch++;LANDMARK_QUEUE.length=0;
  const generation=cameraRequestGeneration,id=visionSessionId;
  try{
    // Drain the previous identity's in-flight batch before resetting server baselines.
    while(uploadBusy){await new Promise(r=>setTimeout(r,30));if(generation!==cameraRequestGeneration)return}
    await visionApi(`/${id}/subject`,{reset:true});
    if(generation!==cameraRequestGeneration)return;
    if(x===null)browserLock.reset();
    else if(!browserLock.select(x,y,(performance.now()-captureStart)/1000))showToast("请点击单独的患者框，重叠时先分开再选");
  }finally{browserSelectionBusy=false}
}

// Remote RTMPose: same JPEG preprocessing and original server process, paired display.
const RTM_REFERENCE="9021e54053d4348b872712f2899593d565f54242c503a92ca0cc5b50ed0dedbe";
let remoteFrames=null,remoteCapturing=false,remoteTimer=null,remoteFrameSeq=0,remoteWatchdog=null;
function startRemoteFrames(){
  remoteCapturing=true;const generation=cameraRequestGeneration,id=visionSessionId;
  let interval=100,lastDisplayedAt=performance.now();
  const cameraCanvas=document.createElement("canvas");
  function showDelayed(){
    const overlay=$("#pose-overlay");overlay.getContext("2d").clearRect(0,0,overlay.width,overlay.height);lastVisionResult=null;
    $(".camera-state").textContent="实时预览 · 识别结果延迟";
    $("#live-cue").textContent="网络或服务器较慢，请暂停动作";
    $("#live-cue-detail").textContent="当前显示实时摄像头，旧角度已隐藏；恢复后请回到起始姿势。";
    $("#phase-name").textContent="等待及时的识别结果";
    $("#live-metrics").querySelectorAll("b").forEach(node=>node.textContent="--");
  }
  function watch(){
    if(!remoteCapturing||generation!==cameraRequestGeneration||!trainingRunning)return;
    if(performance.now()-lastDisplayedAt>1500)showDelayed();
    remoteWatchdog=setTimeout(watch,250);
  }
  clearTimeout(remoteWatchdog);watch();
  remoteFrames=new FrameQueue(async batch=>{
    const started=performance.now();
    const response=await fetch(`${VISION_BASE}/${id}/frames`,{method:"POST",headers:visionHeaders({"Content-Type":"application/json"}),body:JSON.stringify({frames:batch}),signal:AbortSignal.timeout(5000)});
    const result=await response.json();if(!response.ok)throw Error(result.error||"服务器识别失败");
    const elapsed=performance.now()-started;
    interval=Math.max(100,Math.min(200,elapsed/batch.length*1.1));
    const samples=window.__remotePerformance ||= [];samples.push({request_ms:elapsed,batch_frames:batch.length,last_frame_processing_ms:result.processing_ms,queued:remoteFrames.queue.length,skipped:remoteFrames.dropped});if(samples.length>120)samples.shift();
    return result;
  },async(result,batch)=>{
    if(generation!==cameraRequestGeneration||!trainingRunning)return;
    const frame=batch.find(f=>f.frame_id===result.frame_id);
    if(!frame||Math.abs(frame.timestamp_s-result.timestamp_s)>.001)throw Error("识别结果与画面编号不一致，已停止采集");
    if(result.training_progress?.status==="completed")setTimeout(()=>stopLiveTraining(),0);
    if((performance.now()-captureStart)/1000-frame.timestamp_s>1.5){showDelayed();return}
    const img=new Image();await new Promise((resolve,reject)=>{img.onload=resolve;img.onerror=()=>reject(Error("识别画面解码失败"));img.src="data:image/jpeg;base64,"+frame.image});
    if(generation!==cameraRequestGeneration||!trainingRunning)return;
    if((performance.now()-captureStart)/1000-frame.timestamp_s>1.5){showDelayed();return}
    lastDisplayedAt=captureStart+frame.timestamp_s*1000;
    if(captureCanvas.width!==img.naturalWidth)captureCanvas.width=img.naturalWidth;if(captureCanvas.height!==img.naturalHeight)captureCanvas.height=img.naturalHeight;captureCanvas.getContext("2d").drawImage(img,0,0);
    updateLiveResult(result);
    const age=Math.max(0,(performance.now()-captureStart)/1000-frame.timestamp_s);
    $(".camera-state").innerHTML=`<i></i>正在识别 · 延迟 ${age.toFixed(1)} 秒`;
    if(remoteFrames.dropped)$("#live-cue-detail").textContent+=" · 已跳过拥塞画面，次数仅含已识别部分";
  },error=>{
    if(generation!==cameraRequestGeneration||!trainingRunning)return;
    remoteCapturing=false;clearTimeout(remoteTimer);clearTimeout(remoteWatchdog);showDelayed();
    showToast(error.message);$("#live-cue").textContent="网络或服务器中断，正在保存已识别结果";
    setTimeout(()=>stopLiveTraining(),0);
  },{live:true,now:()=>(performance.now()-captureStart)/1000});
  async function capture(){
    if(!remoteCapturing||generation!==cameraRequestGeneration||!trainingRunning)return;
    try{
      const video=$("#training-video");
      if(video.readyState>=2&&!remoteFrames.paused){
        const timestamp_s=(performance.now()-captureStart)/1000;
        const canvas=cameraCanvas,scale=Math.min(1,960/video.videoWidth,960/video.videoHeight);
        const width=Math.round(video.videoWidth*scale),height=Math.round(video.videoHeight*scale);if(canvas.width!==width)canvas.width=width;if(canvas.height!==height)canvas.height=height;canvas.getContext("2d").drawImage(video,0,0,canvas.width,canvas.height);
        const url=canvas.toDataURL("image/jpeg",.85),image=url.slice(url.indexOf(",")+1);
        if(image.length>280000)throw Error("摄像头画面数据过大，请降低摄像头分辨率后重试");
        remoteFrames.add({image,timestamp_s,frame_id:++remoteFrameSeq});
      }
    }catch(e){remoteFrames.fail(e)}
    if(remoteCapturing&&generation===cameraRequestGeneration)remoteTimer=setTimeout(capture,interval);
  }
  capture();
}
