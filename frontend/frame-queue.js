/* Bounded, ordered transport. Never discard an unprocessed frame silently. */
(function(root){
class FrameQueue {
  constructor(send,result,error){this.send=send;this.result=result;this.error=error;this.queue=[];this.running=null;this.failed=null;this.closed=false;this.paused=false}
  add(frame){
    if(this.closed||this.failed||this.paused)return false;
    if(this.queue.length>=16){this.fail(Error('网络或服务器处理过慢，本次采集已停止，请改善网络后重新训练'));return false}
    this.queue.push(frame);this.pump();return true;
  }
  fail(e){if(!this.failed){this.failed=e;this.error(e)}}
  pump(){
    if(this.running)return this.running;
    this.running=(async()=>{
      while(this.queue.length){
        const batch=this.queue.splice(0,8);
        try{const result=await this.send(batch);await this.result(result,batch)}
        catch(e){this.queue.length=0;this.fail(e);break}
      }
    })().finally(()=>{this.running=null});
    return this.running;
  }
  async drain(){if(this.running)await this.running;if(this.queue.length)await this.pump()}
  async finish(){this.closed=true;await this.drain()}
}
root.FrameQueue=FrameQueue;
if(typeof module!=='undefined')module.exports=FrameQueue;
})(globalThis);
