import {loadPyodide} from 'https://cdn.jsdelivr.net/pyodide/v314.0.8/full/pyodide.mjs';

const sources=['dungeon','encounters','enemy_design','floor','growth','layout','mechanics','static_game'];
const dispatch=Promise.all([
 loadPyodide(),
 Promise.all(sources.map(async name=>{
  const response=await fetch(new URL(`engine/${name}.py`,self.location.href));
  if(!response.ok)throw new Error('游戏文件加载失败，请刷新重试。');
  return [name,await response.text()];
 }))
]).then(([python,files])=>{
 for(const [name,source] of files)python.FS.writeFile(`${name}.py`,source);
 return python.runPython('from static_game import dispatch\ndispatch');
});

self.onmessage=async({data:{id,path,data,save}})=>{
 try{
  const run=await dispatch;
  self.postMessage({id,...JSON.parse(run(path,JSON.stringify(data??null),save??''))});
 }catch(error){
  console.error(error);
  self.postMessage({id,error:'游戏引擎运行失败，请刷新重试。'});
 }
};
