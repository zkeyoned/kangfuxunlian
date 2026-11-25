/* Ordered single-flight transport; live mode explicitly counts skipped unsent frames. */
(function(root){
class FrameQueue {
  constructor(send,result,error,options={}){this.send=send;this.result=result;this.error=error;this.options=options;this.queue=[];this.running=null;this.failed=null;this.closed=false;this.paused=false;this.dropped=0}
  discard(n){if(n){this.queue.splice(0,n);this.dropped+=n;this.options.onDrop?.(this.dropped)}}
  trim(){
    if(!this.options.live)return;
    const now=this.options.now();
    let n=0;while(n<this.queue.length&&now-this.queue[n].timestamp_s>.6)n++;
    this.discard(n);
    this.discard(Math.max(0,this.queue.length-2));
  }
  add(frame){
    if(this.closed||this.failed||this.paused)return false;
    if(!this.options.live&&this.queue.length>=16){this.fail(Error('网络或服务器处理过慢，本次采集已停止，请改善网络后重新训练'));return false}
    this.queue.push(frame);this.trim();this.pump();return true;
  }
  fail(e){if(!this.failed){this.failed=e;this.error(e)}}
  pump(){
    if(this.running)return this.running;
    this.running=(async()=>{
      while(this.queue.length){
        this.trim();if(!this.queue.length)break;
        const batch=this.queue.splice(0,this.options.live?2:8);
        try{const result=await this.send(batch);await this.result(result,batch)}
        catch(e){this.queue.length=0;this.fail(e);break}
      }
    })().finally(()=>{this.running=null});
    return this.running;
  }
  async drain(){if(this.running)await this.running;if(this.queue.length)await this.pump()}
  async finish(){this.closed=true;if(this.options.live)this.discard(this.queue.length);await this.drain()}
}
root.FrameQueue=FrameQueue;
if(typeof module!=='undefined')module.exports=FrameQueue;
})(globalThis);
