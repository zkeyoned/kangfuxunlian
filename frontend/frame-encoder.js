(function(root){
class FrameEncoder{
  constructor(){this.worker=null;this.pending=null;this.seq=0;this.disabled=false;this.busy=false}
  fallback(canvas){return new Promise((resolve,reject)=>canvas.toBlob(b=>b?resolve(b):reject(Error('画面编码失败')),'image/jpeg',.85))}
  async encode(canvas){
    if(this.busy)throw Error('Frame encoder already busy');
    this.busy=true;
    try{
      if(this.disabled||!root.Worker||!root.createImageBitmap||!root.OffscreenCanvas)return await this.fallback(canvas);
      if(!this.worker){
        try{this.worker=new root.Worker('frame-encoder-worker.js?v=1')}catch(e){this.disabled=true;return await this.fallback(canvas)}
        this.worker.onmessage=({data})=>{
          const p=this.pending;if(!p||p.id!==data.id)return;
          clearTimeout(p.timer);this.pending=null;
          if(data.error){this.fail(Error(data.error));p.reject(Error(data.error))}else p.resolve(data.blob);
        };
        this.worker.onerror=()=>this.fail(Error('后台画面编码失败'));
      }
      const bitmap=await root.createImageBitmap(canvas),id=++this.seq;
      if(!this.worker){bitmap.close();return await this.fallback(canvas)}
      return await new Promise((resolve,reject)=>{
        this.pending={id,resolve,reject,timer:setTimeout(()=>this.fail(Error('画面编码超时')),3000)};
        try{this.worker.postMessage({id,bitmap},[bitmap])}catch(e){bitmap.close();this.fail(e)}
      });
    }finally{this.busy=false}
  }
  fail(error){
    const p=this.pending;this.pending=null;if(p){clearTimeout(p.timer);p.reject(error)}
    this.worker?.terminate();this.worker=null;this.disabled=true;
  }
}
root.FrameEncoder=FrameEncoder;
if(typeof module!=='undefined')module.exports=FrameEncoder;
})(globalThis);
