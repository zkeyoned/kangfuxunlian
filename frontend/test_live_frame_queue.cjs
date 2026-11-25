const assert=require('assert'),Queue=require('./frame-queue.js');
(async()=>{
 let now=0,release;const sent=[],results=[];
 const q=new Queue(async batch=>{sent.push(batch.map(f=>f.frame_id));if(sent.length===1)await new Promise(r=>release=r);return batch.at(-1)},r=>results.push(r),e=>{throw e},{live:true,now:()=>now});
 q.add({frame_id:0,timestamp_s:0});
 for(let i=1;i<=50;i++){now=i/10;q.add({frame_id:i,timestamp_s:now});assert(q.queue.length<=2)}
 assert.equal(q.dropped,48);release();await q.drain();await q.finish();assert.deepEqual(sent,[[0],[49,50]]);assert(!q.add({}));
 let resume;now=0;const stale=new Queue(()=>new Promise(r=>resume=r),()=>{},()=>{},{live:true,now:()=>now});stale.add({timestamp_s:0});stale.add({timestamp_s:.1});now=2;resume({});await stale.drain();await stale.finish();assert.equal(stale.dropped,1);assert.equal(stale.queue.length,0);
 let unblock;const end=new Queue(()=>new Promise(r=>unblock=r),()=>{},()=>{},{live:true,now:()=>0});end.add({timestamp_s:0});end.add({timestamp_s:.1});const done=end.finish();assert.equal(end.queue.length,0);assert.equal(end.dropped,1);unblock({});await done;
 console.log('PASS slow link: 50 arrivals keep only latest two; stale pending frames expire; no parallel sends or retry');
})().catch(e=>{console.error(e);process.exit(1)});
