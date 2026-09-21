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
lock.update([a,person(.31)],3.4);assert(!lock.select(.31,.5,3.4),'overlapping selection rejected');
console.log('PASS browser subject identity: selection, reordered people, passerby, replacement, crossing, recovery, timeout, reset');
