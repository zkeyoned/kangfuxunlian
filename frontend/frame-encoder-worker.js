// JPEG encoding does not compete with the page's rendering/recording callbacks.
let canvas;
self.onmessage=async({data:{id,bitmap}})=>{
  try{
    if(!canvas)canvas=new OffscreenCanvas(bitmap.width,bitmap.height);
    if(canvas.width!==bitmap.width)canvas.width=bitmap.width;
    if(canvas.height!==bitmap.height)canvas.height=bitmap.height;
    canvas.getContext('2d').drawImage(bitmap,0,0);
    bitmap.close();
    const blob=await canvas.convertToBlob({type:'image/jpeg',quality:.85});
    self.postMessage({id,blob});
  }catch(e){bitmap.close();self.postMessage({id,error:e.message})}
};
