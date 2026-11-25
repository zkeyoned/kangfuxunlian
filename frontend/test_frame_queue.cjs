const assert=require('assert'),Queue=require('./frame-queue.js');
(async()=>{
 let release,active=0,max=0,seen=[],results=[];
 const q=new Queue(async batch=>{active++;max=Math.max(max,active);if(!release)await new Promise(r=>release=r);seen.push(...batch);active--;return batch.at(-1)},async(r,b)=>results.push(r),e=>{throw e});
 q.add(0);for(let i=1;i<14;i++)q.add(i);
 release();await q.finish();assert.equal(max,1);assert.deepEqual(seen,Array.from({length:14},(_,i)=>i));assert.equal(results.at(-1),13);assert(!q.add(14));
 let failures=0,unlock;
 const busy=new Queue(()=>new Promise(r=>unlock=r),()=>{},()=>failures++);
 busy.add(0);for(let i=1;i<=16;i++)assert(busy.add(i));assert(!busy.add(17));assert.equal(failures,1);assert.equal(busy.queue.length,16,'overflow must not silently discard queued frames');
 // Network errors must not retry a possibly already-applied batch.
 let sends=0;const bad=new Queue(async()=>{sends++;throw Error('timeout')},()=>{},()=>{});
 bad.add(1);await bad.finish();assert.equal(sends,1);assert(bad.failed);
 console.log('PASS ordered frame batches, single flight, stop flush, explicit overflow and no ambiguous retries');
})().catch(e=>{console.error(e);process.exit(1)});
