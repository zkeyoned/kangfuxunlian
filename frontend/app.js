const exercises = [
  {
    id: "seated", name: "坐姿直腿抬高", short: "坐姿伸膝", image: "assets/seated-knee-extension-v2.jpg", duration: "约 4 分钟", dose: "2 组 × 10 次", done: true,
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
    rules: [["次数",10,"次"],["伸膝角度",175,"° 以上"],["顶点保持",3,"秒"],["下放时间",2,"秒"]]
  },
  {
    id: "supine", name: "卧姿直腿抬高", short: "仰卧抬腿", image: "assets/supine-leg-raise-v2.jpg", duration: "约 4 分钟", dose: "2 组 × 8 次", done: false,
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
    id: "squat", name: "扶椅子膝盖微蹲", short: "扶椅微蹲", image: "assets/chair-mini-squat-v2.jpg", duration: "约 5 分钟", dose: "2 组 × 10 次", done: false,
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
    id: "stand", name: "坐站训练", short: "坐站训练", image: "assets/sit-to-stand-v2.jpg", duration: "约 5 分钟", dose: "2 组 × 8 次", done: false,
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

const $ = selector => document.querySelector(selector);
const $$ = selector => [...document.querySelectorAll(selector)];
const demoUsers = [
  {key:"patient",name:"林雨晴",account:"linyuqing",phone:"13800138001",email:"linyuqing@example.com",password:"123456",role:"patient",avatar:"林",meta:"患者 · 右膝康复中"},
  {key:"therapist",name:"陈晓雯",account:"chenxiaowen",phone:"13800138002",email:"chenxiaowen@example.com",password:"123456",role:"therapist",avatar:"陈",meta:"康复治疗师 · 24位患者"}
];
let registeredUsers=[];
try{registeredUsers=JSON.parse(localStorage.getItem("kangshifu_registered_users")||"[]")}catch(error){registeredUsers=[]}
let savedDoses={};
try{savedDoses=JSON.parse(localStorage.getItem("kangshifu_patient_doses")||"{}")}catch(error){savedDoses={}}
exercises.forEach(ex=>{const values=ex.dose.match(/(\d+)\D+(\d+)/);ex.recommendedGroups=Number(values?.[1]||2);ex.recommendedReps=Number(values?.[2]||10);ex.groups=savedDoses[ex.id]?.groups||ex.recommendedGroups;ex.reps=savedDoses[ex.id]?.reps||ex.recommendedReps});
let currentUser = null;
let activeExercise = exercises[0];
let trainingTimer;
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
  try{localStorage.setItem("kangshifu_patient_doses",JSON.stringify(doses))}catch(error){}
}

function renderExercises(){
  $("#exercise-list").innerHTML = exercises.map((ex,i) => `<article class="exercise-row ${ex.done ? "done" : ""}"><span class="exercise-index">0${i+1}</span><div class="exercise-thumb"><img src="${ex.image}" alt="${ex.name}示范"></div><div class="exercise-info"><h4>${ex.name}</h4><p>${ex.flow}</p><div class="exercise-meta"><span>当前 ${ex.groups} 组 × ${ex.reps} 次</span><span>${ex.duration}</span></div></div><div class="exercise-config"><div class="dose-editor"><b>自主训练量</b><label>组数<input type="number" min="1" max="20" step="1" value="${ex.groups}" data-dose-field="groups" data-exercise-id="${ex.id}" aria-label="${ex.name}训练组数"></label><label>每组次数<input type="number" min="1" max="100" step="1" value="${ex.reps}" data-dose-field="reps" data-exercise-id="${ex.id}" aria-label="${ex.name}每组次数"></label><small>康复师建议：${ex.dose}</small></div></div><div class="exercise-action"><button class="${ex.done ? "secondary-button" : "primary-button"}" data-train="${ex.id}">${ex.done ? "再次训练" : "开始训练"}</button>${ex.done ? "<small>今日已完成</small>" : ""}</div></article>`).join("");
  $("#patient-plan-rows").innerHTML = exercises.map((ex,i)=>`<div class="plain-row"><span>0${i+1}</span><b>${ex.name}</b><p>${ex.dose} · ${ex.duration}</p><p>${ex.focus.slice(0,3).join("、")}</p></div>`).join("");
}

function renderFeedback(index=0){
  const ex=exercises[index]; activeExercise=ex;
  $("#feedback-index").innerHTML=exercises.map((item,i)=>`<button class="${i===index?"active":""}" data-feedback="${i}"><span>0${i+1}</span><div><b>${item.short}</b><small>${item.hero[0]}</small></div></button>`).join("");
  $("#feedback-kicker").textContent=`动作 0${index+1}`; $("#feedback-title").textContent=ex.name;
  $("#feedback-hero").innerHTML=`<strong>${ex.hero[0]}</strong><p>${ex.hero[1]}</p>`;
  $("#feedback-metrics").innerHTML=ex.metrics.map(m=>`<div class="metric-row"><span>${m[0]}</span><b>${m[1]}</b><small>${m[2]}</small><span class="metric-result ${m[4]}">${m[3]}</span></div>`).join("");
  $("#therapist-note").textContent=ex.note;
}

function renderTherapist(){
  const patients=[["赵敏","膝骨关节炎 · 功能恢复期","2 / 4","训练后疼痛 6 分","需联系","danger"],["林雨晴","膝骨关节炎 · 功能恢复期","1 / 4","伸膝保持不足","需复核","warn"],["周启明","前交叉韧带术后 · 力量重建期","0 / 5","连续两日未训练","待提醒","neutral"],["郭莹","肩袖修复术后 · 活动度恢复期","3 / 3","外旋角度稳定改善","正常","neutral"],["宋泽","非特异性腰痛 · 回归活动期","4 / 4","动作控制稳定","正常","neutral"]];
  $("#patient-rows").innerHTML=patients.map(p=>`<div class="patient-row"><div class="patient-cell-name"><i>${p[0][0]}</i><b>${p[0]}</b></div><span>${p[1]}</span><b>${p[2]}</b><p>${p[3]}</p><span class="status ${p[5]}">${p[4]}</span><button class="text-button">→</button></div>`).join("");
  $("#action-picker").innerHTML=exercises.map(ex=>`<div class="picker-item selected" data-picker="${ex.id}"><img src="${ex.image}" alt=""><div><b>${ex.name}</b><small>${ex.focus.length} 项独立指标</small></div><button aria-label="选择${ex.name}">✓</button></div>`).join("");
  renderRules();
  $("#rule-library").innerHTML=exercises.map((ex,i)=>`<article class="library-row"><span class="exercise-index">0${i+1}</span><div><img src="${ex.image}" alt="${ex.name}"></div><div><h3>${ex.name}</h3><p>${ex.flow}</p></div><div class="library-tags">${ex.focus.map(x=>`<span>${x}</span>`).join("")}</div><small>${ex.rules.length} 条识别规则</small></article>`).join("");
  renderSelectedSummary();
}

function renderRules(){
  $("#rule-editor").innerHTML=exercises.map((ex,i)=>`<div class="rule-item ${i===0?"open":""}" data-rule="${ex.id}"><button class="rule-summary"><span>0${i+1}</span><b>${ex.name}</b><small>${ex.rules.length} 项规则</small><i>${i===0?"−":"+"}</i></button><div class="rule-fields">${ex.rules.map(r=>`<div class="rule-field"><label>${r[0]}</label><div><input type="number" value="${r[1]}"><span>${r[2]}</span></div></div>`).join("")}</div></div>`).join("");
}

function renderSelectedSummary(){
  const selected=$$(".picker-item.selected").map(x=>exercises.find(ex=>ex.id===x.dataset.picker)).filter(Boolean);
  $("#selected-count").textContent=`${selected.length} 项`;
  $("#selected-summary").innerHTML=selected.map((ex,i)=>`<span>0${i+1} · ${ex.name}</span>`).join("");
}

function timeGreeting(){
  const hour=new Date().getHours();
  if(hour<11)return "上午好";
  if(hour<14)return "中午好";
  if(hour<18)return "下午好";
  return "晚上好";
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
  const ex=exercises.find(item=>item.id===id);if(!ex)return;pendingTrainingId=id;
  $("#guide-title").textContent=ex.name;
  $("#guide-steps").innerHTML=ex.flow.split("→").map(step=>`<li>${step.trim()}</li>`).join("");
  $("#guide-note").textContent=ex.note;
  $("#guide-dose").textContent=`本次计划：${ex.groups} 组 × ${ex.reps} 次`;
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
  const names=[...new Set(["赵敏","林雨晴","周启明",...messages.map(message=>message.patient)])];
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
  currentUser=user;
  $("#login-screen").classList.add("hidden"); $("#register-screen").classList.add("hidden"); $("#app-shell").classList.remove("hidden");
  const therapist=user.role==="therapist";
  $("#patient-nav").classList.toggle("hidden",therapist); $("#therapist-nav").classList.toggle("hidden",!therapist);
  $("#profile-avatar").textContent=user.avatar; $("#profile-name").textContent=user.name; $("#profile-meta").textContent=user.meta;
  $("#patient-greeting").textContent=`${timeGreeting()}，${user.name.slice(-2)}`;
  $("#therapist-greeting").textContent=`${user.name[0]}老师，今天有 5 个动作需要复核`;
  $("#section-label").textContent=therapist?"康复师端":"患者端";
  gotoPage(therapist?"therapist-overview":"patient-home");
  updateMessageBadge();
}

function gotoPage(page){
  $$(".page").forEach(x=>x.classList.toggle("active-page",x.id===page));
  $$(".nav-item").forEach(x=>x.classList.toggle("active",x.dataset.page===page));
  const active=$(`.nav-item[data-page="${page}"]`); $("#page-label").textContent=active?active.textContent.trim().replace(/^\d+/,""):"康复方案";
  $(".sidebar").classList.remove("mobile-open"); window.scrollTo({top:0,behavior:"smooth"});
}

function openTraining(id){
  const ex=exercises.find(x=>x.id===id); if(!ex)return; activeExercise=ex;
  const i=exercises.indexOf(ex); $("#training-kicker").textContent=`动作 0${i+1}`; $("#training-title").textContent=ex.name; $("#training-image").src=ex.image;
  $("#phase-name").textContent="准备"; $("#live-cue").textContent="请调整位置并保持全身入镜"; $("#live-cue-detail").textContent=ex.flow;
  $("#live-metrics").innerHTML=ex.live.map(m=>`<div class="live-metric"><span>${m[0]}</span><b>--</b><small>${m[0]==="本组次数"?`/ ${ex.reps}`:m[2]}</small></div>`).join("");
  $("#cue-log").innerHTML=`<li><time>准备</time><p>${ex.note}</p></li>`; $("#start-training").textContent="开始识别"; $("#start-training").disabled=false; clearInterval(trainingTimer);
  $("#training-screen").classList.add("active"); $("#training-screen").setAttribute("aria-hidden","false"); document.body.classList.add("training-open");
}

function closeTraining(){clearInterval(trainingTimer);$("#training-screen").classList.remove("active");$("#training-screen").setAttribute("aria-hidden","true");document.body.classList.remove("training-open")}

function simulateTraining(){
  clearInterval(trainingTimer); let step=0; const button=$("#start-training"); button.textContent="识别中…"; button.disabled=true;
  const tick=()=>{const cue=activeExercise.cues[step%activeExercise.cues.length];$("#phase-name").textContent=cue[0];$("#live-cue").textContent=cue[1];$("#live-cue-detail").textContent=cue[2];$$('.live-metric b').forEach((node,i)=>node.textContent=activeExercise.live[i][1]);$("#cue-log").insertAdjacentHTML("afterbegin",`<li><time>${cue[0]}</time><p>${cue[1]}：${cue[2]}</p></li>`);step++;if(step>=activeExercise.cues.length){clearInterval(trainingTimer);button.disabled=false;button.textContent="再演示一组";activeExercise.done=true;renderExercises();$("#completed-count").textContent=exercises.filter(x=>x.done).length;$("#today-progress").style.width=`${exercises.filter(x=>x.done).length*25}%`;showToast(`${activeExercise.name}已完成，本组反馈已记录`)}};
  tick(); trainingTimer=setInterval(tick,1700);
}

function showToast(message){const toast=$("#toast");toast.textContent=message;toast.classList.add("show");setTimeout(()=>toast.classList.remove("show"),2600)}

renderExercises(); renderFeedback(); renderTherapist();

document.addEventListener("click",event=>{
  const demo=event.target.closest("[data-demo-account]"); if(demo){const user=demoUsers.find(item=>item.key===demo.dataset.demoAccount);if(user){setRole("login",user.role);$("#login-account").value=user.phone;$("#login-password").value=user.password;$("#login-error").textContent=""}}
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
  if(event.target.closest("[data-close-training]"))closeTraining();
  if(event.target.closest("#start-training"))simulateTraining();
  if(event.target.closest("#open-messages"))openMessages();
  if(event.target.closest("[data-close-messages]"))$("#message-dialog").close();
  const chat=event.target.closest("[data-chat-patient]");if(chat)openMessages(chat.dataset.chatPatient);
  const contact=event.target.closest("[data-message-contact]");if(contact)openMessages(contact.dataset.messageContact);
  const rule=event.target.closest(".rule-summary"); if(rule){const item=rule.parentElement;item.classList.toggle("open");rule.querySelector("i").textContent=item.classList.contains("open")?"−":"+"}
  const picker=event.target.closest(".picker-item"); if(picker){picker.classList.toggle("selected");picker.querySelector("button").textContent=picker.classList.contains("selected")?"✓":"+";renderSelectedSummary();$("#save-state").textContent="有未保存更改"}
  if(event.target.closest("#save-draft")){$("#save-state").textContent="草稿已保存";showToast("康复方案草稿已保存")}
  if(event.target.closest("#publish-plan")){$("#save-state").textContent="已发布";showToast("方案已发布给林雨晴，患者端将收到提醒")}
  if(event.target.closest("#logout")){closeTraining();if($("#message-dialog").open)$("#message-dialog").close();currentUser=null;$("#app-shell").classList.add("hidden");showAuthScreen("login");$("#login-form").reset();setRole("login","patient");$("#login-error").textContent=""}
  if(event.target.closest("#mobile-menu"))$(".sidebar").classList.toggle("mobile-open");
});

$("#login-form").addEventListener("submit",event=>{
  event.preventDefault();
  const account=$("#login-account").value.trim().toLowerCase();
  const password=$("#login-password").value;
  const user=[...demoUsers,...registeredUsers].find(item=>item.role===selectedLoginRole&&[item.account,item.phone,item.email,item.identifier].filter(Boolean).some(value=>value.toLowerCase()===account)&&item.password===password);
  if(!user){$("#login-error").textContent="当前身份下的账号或密码不匹配，请检查后重试。";return}
  $("#login-error").textContent="";enterApp(user);
});

$("#register-form").addEventListener("submit",event=>{
  event.preventDefault();
  const name=$("#register-name").value.trim();const identifier=$("#register-account").value.trim().toLowerCase();const password=$("#register-password").value;
  if(!name){$("#register-error").textContent="请填写用户名。";return}
  if(!(/^[1][3-9]\d{9}$/.test(identifier)||/^\S+@\S+\.\S+$/.test(identifier))){$("#register-error").textContent="请输入有效的手机号或邮箱。";return}
  if(password.length<6){$("#register-error").textContent="密码至少需要 6 位。";return}
  if([...demoUsers,...registeredUsers].some(user=>[user.phone,user.email,user.identifier].includes(identifier))){$("#register-error").textContent="该手机号或邮箱已注册。";return}
  const user={key:`registered-${Date.now()}`,name,identifier,password,role:selectedRegisterRole,avatar:name[0],meta:selectedRegisterRole==="therapist"?"康复治疗师 · 新账号":"患者 · 康复训练中"};
  registeredUsers.push(user);try{localStorage.setItem("kangshifu_registered_users",JSON.stringify(registeredUsers))}catch(error){}
  $("#register-error").textContent="";$("#register-form").reset();setRole("register","patient");setRole("login",user.role);showAuthScreen("login");$("#login-account").value=identifier;showToast("注册成功，请使用新账号登录");
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
  const summary=doseField.closest(".exercise-row")?.querySelector(".exercise-meta span");if(summary)summary.textContent=`当前 ${ex.groups} 组 × ${ex.reps} 次`;saveDosePreferences();
});
document.addEventListener("change",event=>{
  const doseField=event.target.closest("[data-dose-field]");
  if(doseField){const ex=exercises.find(item=>item.id===doseField.dataset.exerciseId);if(ex){const limit=doseField.dataset.doseField==="groups"?20:100;const value=Math.max(1,Math.min(limit,Math.round(Number(doseField.value)||1)));ex[doseField.dataset.doseField]=value;saveDosePreferences();renderExercises();showToast(`${ex.name}已调整为 ${ex.groups} 组，每组 ${ex.reps} 次`)}return}
  if(event.target.closest("#therapist-plans"))$("#save-state").textContent="有未保存更改";
});
