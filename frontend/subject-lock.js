/* Identity is session-local. No images or appearance descriptors leave the browser. */
(function(root){
class BrowserSubjectLock {
  constructor(){this.reset()}
  reset(){this.target=null;this.candidates=[];this.status='select_subject';this.lastSeen=null;this.recovery=0}
  candidate(p){
    const lm=p.landmarks;
    if(!Array.isArray(lm)||lm.length!==33)return null;
    const torso=[11,12,23,24].map(i=>lm[i]);
    if(torso.some(p=>!p||!Number.isFinite(p.x)||!Number.isFinite(p.y)||(p.visibility||0)<.65))return null;
    const cx=torso.reduce((s,p)=>s+p.x,0)/4,cy=torso.reduce((s,p)=>s+p.y,0)/4;
    const size=Math.hypot((torso[0].x+torso[1].x-torso[2].x-torso[3].x)/2,(torso[0].y+torso[1].y-torso[2].y-torso[3].y)/2);
    if(size<.035)return null;
    const visible=lm.filter(p=>p.visibility>=.5);
    return {...p,cx,cy,size,box:[Math.min(...visible.map(p=>p.x))-.02,Math.min(...visible.map(p=>p.y))-.02,Math.max(...visible.map(p=>p.x))+.02,Math.max(...visible.map(p=>p.y))+.02]};
  }
  select(x,y,t){
    const matches=this.candidates.filter(c=>x>=c.box[0]&&x<=c.box[2]&&y>=c.box[1]&&y<=c.box[3]);
    if(matches.length!==1)return false;
    this.target={...matches[0],anchor:matches[0].appearance};this.lastSeen=t;this.status='locked';this.recovery=0;return true;
  }
  update(poses,t){
    this.candidates=poses.map(p=>this.candidate(p)).filter(Boolean);
    if(!this.target)return this.result(null);
    if(t-this.lastSeen>2){this.status='subject_lost_reconfirm';return this.result(null)}
    if(this.status==='subject_lost_reconfirm')return this.result(null);
    const ranked=this.candidates.map(c=>{
      const distance=Math.hypot(c.cx-this.target.cx,c.cy-this.target.cy)/this.target.size;
      const ratio=c.size/this.target.size;
      const a=this.target.anchor,b=c.appearance;
      const color=a&&b?a.reduce((s,v,i)=>s+Math.abs(v-b[i]),0)/2:null;
      const valid=distance<.65&&ratio>.65&&ratio<1.55&&(color===null?distance<.22:color<.32);
      return {c,valid,score:distance+(color??.3)*2};
    }).filter(r=>r.valid).sort((a,b)=>a.score-b.score);
    const best=ranked[0];
    // Similar/overlapping bodies are ambiguous even if one happens to rank first.
    const overlap=best&&this.candidates.some(c=>c!==best.c&&Math.hypot(c.cx-best.c.cx,c.cy-best.c.cy)<Math.min(c.size,best.c.size)*.5);
    if(!best||overlap||(ranked[1]&&ranked[1].score-best.score<.25)){
      this.status='subject_temporarily_lost';this.recovery=0;return this.result(null);
    }
    if(this.status!=='locked'&&++this.recovery<3)return this.result(null);
    this.target={...best.c,anchor:this.target.anchor};this.lastSeen=t;this.status='locked';this.recovery=0;
    return this.result(best.c.landmarks);
  }
  result(landmarks){return {landmarks,pose_status:landmarks?'single_person':this.status,subject:{status:this.status,boxes:this.candidates.map(c=>c.box)}}}
}
root.BrowserSubjectLock=BrowserSubjectLock;
if(typeof module!=='undefined')module.exports=BrowserSubjectLock;
})(globalThis);
