/* Identity is session-local. No images or appearance descriptors leave the browser. */
(function(root){
// 躯干关键点可见度门槛。坐姿/侧坐时远侧肩、髋常低于 0.65，旧门槛会让正在训练的人频繁"丢失"。
const VIS=.5;
// 同一人被模型重复检出时，两个候选中心距离/躯干长度通常远小于此值，且颜色几乎相同。
const DUP_DIST=.15,DUP_COLOR=.15;
// 丢失后自动找回：画面里只剩一个人、且衣着颜色与锁定时接近，连续这么多帧才重新锁定。
const AUTO_RELOCK_FRAMES=5,AUTO_RELOCK_COLOR=.32;
const colorDistance=(a,b)=>a&&b?a.reduce((s,v,i)=>s+Math.abs(v-b[i]),0)/2:null;
class BrowserSubjectLock {
  constructor(){this.reset()}
  reset(){this.target=null;this.candidates=[];this.status='select_subject';this.lastSeen=null;this.recovery=0}
  candidate(p){
    const lm=p.landmarks;
    if(!Array.isArray(lm)||lm.length!==33)return null;
    const ok=q=>q&&Number.isFinite(q.x)&&Number.isFinite(q.y)&&(q.visibility||0)>=VIS;
    // 只要至少一个肩、一个髋看得清就算有效躯干（侧坐时只露一侧）。
    const shoulders=[lm[11],lm[12]].filter(ok),hips=[lm[23],lm[24]].filter(ok);
    if(!shoulders.length||!hips.length)return null;
    const mean=(ps,k)=>ps.reduce((s,q)=>s+q[k],0)/ps.length;
    const sx=mean(shoulders,'x'),sy=mean(shoulders,'y'),hx=mean(hips,'x'),hy=mean(hips,'y');
    const cx=(sx+hx)/2,cy=(sy+hy)/2,size=Math.hypot(sx-hx,sy-hy);
    if(size<.035)return null;
    const visible=lm.filter(q=>q.visibility>=.5);
    const vis=[11,12,23,24].reduce((s,i)=>s+(lm[i].visibility||0),0);
    return {...p,cx,cy,size,vis,box:[Math.min(...visible.map(q=>q.x))-.02,Math.min(...visible.map(q=>q.y))-.02,Math.max(...visible.map(q=>q.x))+.02,Math.max(...visible.map(q=>q.y))+.02]};
  }
  // 模型偶尔把同一个人检出两次（位置、大小、颜色几乎一样），旧逻辑会把它当成"重叠的两个人"而暂停。
  dedupe(cands){
    const kept=[];
    for(const c of [...cands].sort((a,b)=>b.vis-a.vis)){
      const dup=kept.some(k=>{
        const d=Math.hypot(c.cx-k.cx,c.cy-k.cy)/Math.min(c.size,k.size),ratio=c.size/k.size,color=colorDistance(c.appearance,k.appearance);
        return d<DUP_DIST&&ratio>.75&&ratio<1.33&&(color===null?d<.1:color<DUP_COLOR);
      });
      if(!dup)kept.push(c);
    }
    return kept;
  }
  select(x,y,t){
    const matches=this.candidates.filter(c=>x>=c.box[0]&&x<=c.box[2]&&y>=c.box[1]&&y<=c.box[3]);
    if(matches.length!==1)return false;
    this.target={...matches[0],anchor:matches[0].appearance};this.lastSeen=t;this.status='locked';this.recovery=0;return true;
  }
  update(poses,t){
    this.candidates=this.dedupe(poses.map(p=>this.candidate(p)).filter(Boolean));
    if(!this.target)return this.result(null);
    if(t-this.lastSeen>2&&this.status!=='subject_lost_reconfirm'){this.status='subject_lost_reconfirm';this.recovery=0}
    if(this.status==='subject_lost_reconfirm'){
      // 画面里只有一个人且衣着与锁定时一致：多半就是原训练者回来了，连续几帧确认后自动找回，不必再点。
      const only=this.candidates.length===1?this.candidates[0]:null;
      const color=only?colorDistance(this.target.anchor,only.appearance):null;
      if(only&&color!==null&&color<AUTO_RELOCK_COLOR){
        if(++this.recovery>=AUTO_RELOCK_FRAMES){
          this.target={...only,anchor:this.target.anchor};this.lastSeen=t;this.status='locked';this.recovery=0;
          return this.result(only.landmarks);
        }
      }else this.recovery=0;
      return this.result(null);
    }
    const ranked=this.candidates.map(c=>{
      const distance=Math.hypot(c.cx-this.target.cx,c.cy-this.target.cy)/this.target.size;
      const ratio=c.size/this.target.size;
      const color=colorDistance(this.target.anchor,c.appearance);
      const valid=distance<.65&&ratio>.6&&ratio<1.65&&(color===null?distance<.22:color<.4);
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
