const assert=require('assert');
const Lock=require('./subject-lock.js');
function person(x,color=0){
 const landmarks=Array.from({length:33},()=>({x,y:.45,visibility:.99}));
 for(const [i,dx,y] of [[11,-.04,.3],[12,.04,.3],[23,-.04,.6],[24,.04,.6],[25,-.04,.75],[26,.04,.75],[27,-.04,.9],[28,.04,.9]])landmarks[i]={x:x+dx,y,visibility:.99};
 const appearance=new Array(64).fill(0);appearance[color]=1;
 return {landmarks,appearance};
}
const a=person(.3),b=person(.7,4),lock=new Lock();
assert.equal(lock.update([a,b],0).pose_status,'select_subject');
assert(lock.select(.3,.5,0));
assert.equal(lock.update([b,a],.1).landmarks,a.landmarks,'output order must not determine identity');
assert.equal(lock.update([person(.6,4),person(.31)],.2).pose_status,'single_person','bystander must not interrupt');
assert.equal(lock.update([person(.32,4)],.3).landmarks,null,'replacement at same location must not be selected');
assert.equal(lock.update([a,b],.4).landmarks,null);
assert.equal(lock.update([a,b],.5).landmarks,null);
assert.equal(lock.update([a,b],.6).landmarks,a.landmarks,'stable original recovers');
assert.equal(lock.update([a,person(.32,4)],.7).landmarks,null,'crossing pauses');
assert.equal(lock.update([a],3).pose_status,'subject_lost_reconfirm');
assert.equal(lock.update([a],3.1).landmarks,null,'long absence requires explicit selection');
assert(lock.select(.3,.5,3.1));
assert.equal(lock.update([a],3.2).pose_status,'single_person');
lock.reset();assert.equal(lock.update([b],3.3).landmarks,null);
assert(!lock.select(.1,.1,3.3));
lock.update([a,person(.31,4)],3.4);assert(!lock.select(.31,.5,3.4),'overlapping selection rejected');
// 同一人被模型重复检出（位置、颜色几乎相同）应合并为一个候选，不能当成两人重叠。
{const L=new Lock(),dup=person(.3),dup2=person(.302);
 assert.equal(L.update([dup,dup2],0).subject.boxes.length,1,'duplicate detection merged');
 assert(L.select(.3,.5,0),'can select despite duplicate detection');
 assert.equal(L.update([dup,dup2],.1).pose_status,'single_person','duplicate does not pause counting');}
// 侧坐：只露出一侧肩和髋也算有效躯干。
{const L=new Lock(),side=person(.5);for(const i of [12,24])side.landmarks[i]={...side.landmarks[i],visibility:.2};
 for(const i of [11,23])side.landmarks[i]={...side.landmarks[i],visibility:.55};
 L.update([side],0);assert(L.select(.5,.5,0),'one-sided torso selectable');
 assert.equal(L.update([side],.1).pose_status,'single_person','one-sided torso stays locked');}
// 丢失后：画面只剩原训练者，连续 5 帧自动找回；换成别人不会自动锁。
{const L=new Lock(),p=person(.4);L.update([p],0);L.select(.4,.5,0);
 assert.equal(L.update([],2.5).pose_status,'subject_lost_reconfirm');
 for(let i=1;i<5;i++)assert.equal(L.update([person(.45)],2.5+i*.1).landmarks,null);
 assert.equal(L.update([person(.45)],3.0).pose_status,'single_person','original subject auto-relocked');
 const M=new Lock();M.update([p],0);M.select(.4,.5,0);M.update([],2.5);
 for(let i=1;i<=10;i++)assert.equal(M.update([person(.4,9)],2.5+i*.1).landmarks,null,'different person never auto-locked');
 const N=new Lock();N.update([p],0);N.select(.4,.5,0);N.update([],2.5);
 for(let i=1;i<=10;i++)assert.equal(N.update([person(.3),person(.7,4)],2.5+i*.1).landmarks,null,'two people still need a click');}
console.log('PASS browser subject identity: selection, reordered people, passerby, replacement, crossing, recovery, timeout, reset, duplicates, one-sided torso, auto relock');
