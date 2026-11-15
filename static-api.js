'use strict';
{
 const saveKey='bobozan-static-save:'+new URL('./',document.currentScript.src).pathname;
 const worker=new Worker(new URL('static-worker.js',document.currentScript.src),{type:'module'});
 const pending=new Map();
 let requestId=0;
 let failed=false;
 worker.onmessage=({data:{id,result,save,error}})=>{
  const request=pending.get(id);
  if(!request)return;
  pending.delete(id);
  if(error){request.reject(new Error(error));return}
  if(save){
   try{localStorage.setItem(saveKey,save)}
   catch{request.reject(new Error('浏览器无法保存进度。请检查站点存储权限。'));return}
  }
  request.resolve(result);
 };
 worker.onerror=()=>{
  failed=true;
  for(const {reject} of pending.values())reject(new Error('游戏引擎加载失败，请刷新重试。'));
  pending.clear();
 };
 window.bobozanLocalApi=(path,data)=>new Promise((resolve,reject)=>{
  if(failed){reject(new Error('游戏引擎加载失败，请刷新重试。'));return}
  const save=localStorage.getItem(saveKey);
  const id=++requestId;
  pending.set(id,{resolve,reject});
  worker.postMessage({id,path,data,save});
 });
}
