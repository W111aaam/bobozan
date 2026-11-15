'use strict';
const $ = id => document.getElementById(id);
const dirs = {up:[0,-1],right:[1,0],down:[0,1],left:[-1,0]};
const arrows = {up:'↑',right:'→',down:'↓',left:'←'};
let state=null, busy=true, aim=null, displayedResult=null, fxTimer, pendingFall=null;
let aimDetails=null, inspecting=false, aimingItem=null, lureHover=null, lureSelection=null, plantingSeed=null;
const CAMERA_SCALES=[0.8,1,1.25,1.5];
let zoomIndex=1;
function changeZoom(index){
 const next=Math.max(0,Math.min(CAMERA_SCALES.length-1,index));
 if(!state||next===zoomIndex)return;
 zoomIndex=next;
 renderBoard();
}
const esc = value => String(value).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const pos = entity => [entity.x,entity.y];
const same = (a,b) => !!a&&!!b&&a[0]===b[0]&&a[1]===b[1];
function toast(text,error=false){$('message').textContent=text;$('message').classList.toggle('error',error)}
async function api(path,data){if(window.bobozanLocalApi)return window.bobozanLocalApi(path,data);const controller=new AbortController();const timer=setTimeout(()=>controller.abort(),8000);try{const res=await fetch('/api/'+path,{signal:controller.signal,...(data===undefined?{}:{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)})});const body=await res.json();if(!res.ok)throw Error(body.error||'请求失败');return body}finally{clearTimeout(timer)}}
function safeToFill(){
 return canAct()&&!state.pursuing&&!state.returning.length&&!state.poisoned&&
  !state.fireCells?.some(cell=>same(cell,pos(state.player)))&&
  !state.enemies.some(e=>!e.disguised&&!e.dormant)&&state.player.energy<state.energyCap;
}
function canAct(){return state&&!busy&&!state.result&&!state.choices.length&&!state.talentChoice}
function closeDialogs(){document.querySelectorAll('dialog[open]').forEach(d=>d.close())}
function renderControls(){
 document.querySelectorAll('[data-action]').forEach(b=>{const a=b.dataset.action;b.disabled=!canAct()||(a==='charge'&&state.player.energy>=state.energyCap)||(['wave','heavy','reflect'].includes(a)&&state.player.energy<(a==='heavy'?state.waveStats.heavyCost:a==='wave'?(state.waveStats.waveCost??1):1))||(a==='guard'&&state?.mode==='armor'&&state.player.energy<1);b.classList.toggle('selected',aim===a)});
 document.querySelectorAll('[data-quick-use]').forEach(button=>{
  button.disabled=!canAct()||!state.inventory.some(item=>item.id===QUICK_ITEMS.find(slot=>slot.key===button.dataset.quickUse).id&&!item.passive);
 });
 $('heavy').hidden=!state?.upgrades.some(u=>u.id==='heavy');
 document.querySelectorAll('[data-direction]').forEach(b=>b.disabled=!canAct());
 $('exit').hidden=!state||!same(pos(state.player),state.exit);
 $('exit').disabled=!canAct()||!state.exitUnlocked||!same(pos(state.player),state.exit);
 if(state){
  $('exit').textContent=state.floorKind==='relic'?'触碰祭坛 ↗':'下楼 ↗';
  $('skip-talents').disabled=busy;
  $('confirm-talents').disabled=busy||!state.talentChoice||
   document.querySelectorAll('#talent-options input:checked').length!==state.talentChoice.limit;
  document.querySelectorAll('[data-growth]').forEach(button=>{
   button.disabled=!canAct()||!state.growth.safe||button.dataset.available!=='true';
  });
  document.querySelectorAll('[data-recipe]').forEach(button=>{
   button.disabled=!canAct()||button.dataset.available!=='true';
  });
  document.querySelectorAll('#ground-items [data-pickup]').forEach(b=>b.disabled=!canAct()||!state.packableItems.includes(b.dataset.groundItem));
 $('ground-pick-all').disabled=!canAct()||!state.groundItems?.some(f=>f.items.some(item=>state.packableItems.includes(item.id)));
  document.querySelectorAll('#tactics button, #loadout button, #bag-item-detail button').forEach(b=>b.disabled=!canAct()||b.getAttribute('aria-pressed')==='true');
 }
 $('restart').disabled=busy||!state;
 $('cancel-aim').hidden=!aim&&!aimingItem;
 $('throw-lure').hidden=!aimingItem||!lureSelection;
 $('throw-lure').disabled=!canAct();
 $('throw-lure').textContent=aimingItem==='plant'?'播种 · 1 拍':'投掷 · 1 拍';
 $('fill-energy').textContent=fillingEnergy?'停止攒能':'攒满';
 $('drink-dew').disabled=!canAct()||!state.dew||state.player.hp>=(state.maxHp??6);
 $('fill-energy').disabled=!fillingEnergy&&!safeToFill();
 $('resume-travel').disabled=!canAct()||!!aim||!!aimingItem||!!state?.movementLocked;
 $('resume-travel').textContent=state&&travelNeedsCaution()?'继续一步':'继续前往';
 $('inspect-cell').disabled=!state||busy;
 $('inspect-cell').setAttribute('aria-pressed',String(inspecting));
 $('map-toast').textContent=inspecting?'点击地格查看 · 不消耗行动':aimingItem==='plant'?'选择播种位置 · 四格内空地':aimingItem?(lureSelection?(aimingItem==='frost_smoke'?'蓝圈标记可能受冻的敌人 · 范围内浅水结冰':'确认投掷，或点选其他落点'):'选择投掷落点 · 四格内空地'):aim?'选择发射方向 · 箭头键 / 点击射线':'';
 $('map-toast').classList.toggle('visible',inspecting||!!aim||!!aimingItem);
 $('skip-reward').disabled=busy;
 document.querySelectorAll('#rewards button').forEach(b=>b.disabled=busy||b.dataset.blocked==='true');
 document.querySelectorAll('#retry,#new-seed,#confirm-restart').forEach(b=>b.disabled=busy);
}
function ray(direction){
 if(aim==='reflect')return aimDetails?.[direction]?.cells??[];
 return aimDetails?.[direction]?.cells??state.aimPaths?.[direction]??[];
}
const FEATURE_NAMES={chest:'遗物宝箱',materials:'空补给箱',supply_choice:'战术补给箱',shrine:'疗愈泉水',dry_spring:'干涸泉水',key:'钥匙',kit:'药剂',cache:'战术补给',
 lure_cache:'诱饵',smoke:'烟雾弹',wonder:'镜间奇遇',dew:'露珠',grass_seed:'响草种子',sun_seed:'阳草种子',chart:'测绘卷轴',recall:'回程卷轴',ankh:'护命符',terror:'惊退卷轴',
 echo_smoke:'响雾弹',stolen_energy:'被偷走的能量',rune_shard:'刻印碎片'};
function featureName(f){return f.itemName||FEATURE_NAMES[f.kind]}
function unopenedSupplyAt(cell){
 return state.features.some(f=>f.kind==='supply_choice'&&!f.used&&same(pos(f),cell));
}
function countFeatures(features){return features.reduce((count,f)=>count+Math.max(1,f.itemCount??1),0)}
function featuresByCell(){
 const cells=new Map();
 for(const feature of state.features){
  const key=pos(feature).join(',');
  if(!cells.has(key))cells.set(key,[]);
  cells.get(key).push(feature);
 }
 return cells;
}
const LOCK_STYLES={
 store:{name:'战术库房',detail:'门上刻有补给箱，里面可能有战术道具。',glyph:'◆',color:'#e4ba70'},
 garden:{name:'封闭花圃',detail:'门上刻有藤叶，里面有可恢复生命的阳草。',glyph:'✦',color:'#b7db83'},
 alarm_store:{name:'警戒库房',detail:'门上刻有警铃。入口有警报，附近有守卫。',glyph:'!',color:'#eea27f'},
 dart_vault:{name:'刺针库房',detail:'一排刺针挡住去路，里面有刻印碎片。可站在近侧用波或诱饵先触发一格，再从那格过。',glyph:'×',color:'#f0a483'}
};
const RUNE_DETAILS={shatter:'破甲（无视普通防御）',echo:'回音（下拍沿原路返回）',frost:'凝滞（受伤后限制移动一拍）'};
function lockStyle(){return LOCK_STYLES[state.lockStyle]}
function renderLandmarks(){
 const destinations=[];
 if(state.exit)destinations.push({cell:state.exit,name:state.floorKind==='relic'?'终点祭坛':'下层阶梯',
  hint:state.exitLockReason??'',icon:'↘'});
 for(const room of state.roomStates){
  if(room.blocksExit&&room.anchor)destinations.push({cell:room.anchor,name:'阶梯守卫',hint:'清理战斗区后解锁',icon:'⚔'});
 }
 if(state.lock)destinations.push({cell:state.lock,name:lockStyle()?.name??'库房锁门',
  hint:[state.keys?'有钥匙':'需要钥匙',state.lockStyle==='dart_vault'?'刻印碎片':''].filter(Boolean).join(' · '),icon:lockStyle()?.glyph??'◆'});
 for(const cell of state.secretClues??[])destinations.push({cell,name:'墙上的刻痕',hint:'靠近后按 X 搜查',icon:'⌕'});
 for(const statue of state.statueLandmarks??[]){
  const weapon=state.weapons.find(w=>w.id===statue.emitter)?.name;
  destinations.push({cell:pos(statue),name:'武器石像',hint:[weapon,RUNE_DETAILS[statue.inscription],'掉落刻印碎片'].filter(Boolean).join(' · '),icon:'◇'});
 }
 const healthy=state.player.hp>=state.maxHp;
 for(const tile of state.terrain){
  if(tile.kind==='sun_plant')destinations.push({cell:pos(tile),name:'阳草',hint:healthy?'生命已满':'恢复 2 生命',icon:'✦'});
 }
 for(const features of featuresByCell().values()){
  const marked=features.filter(f=>!f.used&&!['dry_spring','materials','stolen_energy'].includes(f.kind));
  if(!marked.length)continue;
  const [f]=marked;
  const stack=marked.length>1;
  const tile=state.terrain.find(t=>same(pos(t),pos(f)));
  const rubble=tile?.kind==='rubble';
  const full=f.kind==='supply_choice'
   ?!state.supplyOptions.some(item=>state.packableItems.includes(item.id))
   :marked.every(feature=>state.fullBagLandmarks.includes(feature.id));
  const hint=rubble?'脆墙后':full?'背包已满':
   stack?marked.map(featureName).join(' / '):
   f.kind==='supply_choice'?(state.supplyOptions??[]).map(item=>item.name).join(' / '):
   f.kind==='shrine'&&healthy?'生命已满':f.kind==='dew'&&healthy&&state.dew>=state.dewCapacity?'露珠已满':'';
  destinations.push({cell:pos(f),name:stack?`${countFeatures(marked)} 项地面物品`:featureName(f),hint,blocked:rubble,icon:f.kind==='shrine'?'✦':'◇'});
 }
 $('landmark-count').textContent=destinations.length?'· '+destinations.length:'';
 const rows=destinations.map(({cell,name,hint,icon,blocked})=>
  `<button type="button" data-landmark="${cell.join(',')}" ${blocked?'disabled':''}
   aria-label="${blocked?'':'前往'}${esc(name)}${hint?'，'+esc(hint):''}"><span aria-hidden="true">${icon}</span>
  ${esc(name)}${hint?`<small>${esc(hint)}</small>`:''}</button>`).join('')||'<p class="muted">还没有发现路标。</p>';
 for(const list of [$('landmarks'),$('journal-landmark-list')])list.innerHTML=rows;
}
function terrainName(tile){
 if(!tile)return '';
 if(tile.kind==='mirror')return (tile.rotating?'旋转镜面':'固定镜面')+' '+tile.slash;
 if(tile.kind==='high_grass')return '高草 · 遮挡视线，可踩倒或打碎';
 if(tile.kind==='grass')return '短草';
 if(tile.kind==='web')return '蛛网 · 波可切断，无法以飞雷神进出';
 if(tile.kind==='sun_plant')return '阳草 · 受伤时踩上回复 2 生命';
 if(tile.kind==='root_plant')return '缠根 · 敌人踩上后下一拍无法移动';
 if(tile.kind==='trap'){
  if(!tile.armed)return '已触发的陷阱';
  return {alarm:'警报陷阱 · 会吸引附近敌人',dart:'刺针陷阱 · 踩中受伤',grip:'夹足陷阱 · 下拍无法移动'}[tile.mechanism];
 }
 if(tile.kind==='ice')return '薄冰 · 本拍限制移动';
 if(tile.kind==='water')return tile.ice_until?`冰封浅水 · ${Math.max(0,tile.ice_until-state.turn)} 拍后解冻 · 暂停导电`:'浅水 · 熄灭灼烧，相连水格可导电';
 if(tile.kind==='rubble')return '脆墙 · 需要破城震波拆除';
 return ['脆弱地板 · 首次踩入开裂','开裂地板 · 再次踩入必死','深渊 · 踩入必死'][tile.stage];
}
let perspectiveBoard=false;
try{perspectiveBoard=localStorage.getItem('bobozan-view')==='3d'}catch{}

function raisedWall(x,y,color,low){
 const left=x*60,right=left+60,back=y*60,front=back+60;
 // Inverse ground projection of the vertical lift, so edges rise on screen.
 const height=low?10:35;
 const dx=-height*.36,dy=-height;
 return `<g pointer-events="none">
  <path d="M${left} ${front}h60l${dx} ${dy}h-60z" fill="#263037"/>
  <path d="M${right} ${back}v60l${dx} ${dy}v-60z" fill="#34434a"/>
  <rect x="${left+dx}" y="${back+dy}" width="60" height="60" fill="${color}" stroke="#85918b"/>
 </g>`;
}

function renderBoard(showEffects=false){
 if(!state)return;
 const palettes={
  '下水道':['#39484a','#66706b'], '监狱':['#3d4154','#696b89'], '洞穴':['#493c37','#766353'],
  '矮人都市':['#494535','#7c7551'], '恶魔大厅':['#512f3c','#865361'], '终点':['#3d435b','#686d8c']
 };
 const [floorColor,wallColor]=palettes[state.region]||palettes['下水道'];
 const compact=matchMedia('(max-width: 680px)').matches;
 const zoom=CAMERA_SCALES[zoomIndex];
 const width=Math.min(state.width,2*Math.round(((compact?11:15)/zoom-1)/2)+1);
 const height=Math.min(state.height,2*Math.round(((compact?11:13)/zoom-1)/2)+1);
 $('zoom-out').disabled=zoomIndex===0;
 $('zoom-in').disabled=zoomIndex===CAMERA_SCALES.length-1;
 $('zoom-reset').textContent=zoom+'×';
 const ox=Math.max(0,Math.min(state.width-width,state.player.x-Math.floor(width/2)));
 const oy=Math.max(0,Math.min(state.height-height,state.player.y-Math.floor(height/2)));
 const w=width*60,h=height*60;
 $('board').setAttribute('viewBox',perspectiveBoard
  ? `${-h*.36-8} -52 ${w+h*.36+16} ${w*.16+h*.66+64}`
  : `0 0 ${w} ${h}`);
 $('board').classList.toggle('oblique',perspectiveBoard);
 $('view-toggle').setAttribute('aria-pressed',String(perspectiveBoard));
 $('view-toggle').textContent=perspectiveBoard?'斜俯视':'平面';
 const mapped=state.mapped??[];
 const charted=[...state.explored,...mapped];
 const mappedKeys=new Set(mapped.map(c=>c.join(',')));
 $('charted-key').hidden=!mapped.length;
 const known=new Set(charted.map(c=>c.join(','))),seen=new Set(state.visible.map(c=>c.join(','))),walls=new Set(state.walls.map(c=>c.join(',')));
 const doors=new Set(state.doors.map(c=>c.join(',')));
 const openDoors=new Set((state.openDoors??[]).map(c=>c.join(',')));
 const verticalDoors=new Set((state.verticalDoors??[]).map(c=>c.join(',')));
 const lock=state.lock?.join(',');
 const isFloor=(x,y,fromX,fromY)=>{
  const key=x+','+y;
  if(!known.has(key)||walls.has(key))return false;
  if(doors.has(key)||key===lock)return (x===fromX)===verticalDoors.has(key);
  return true;
 };
 const secretClues=new Set((state.secretClues??state.searchHints??[]).map(c=>c.join(',')));
 const warnings=state.enemies.flatMap(e=>e.intent.warning??[]);
 const lureCells=new Set(aimingItem?throwTargets().map(c=>c.join(',')):[]);
 const previewKey=lureHover??lureSelection?.join(',');
 const lurePreview=['lure','grass_seed','echo_smoke'].includes(aimingItem)&&state.lurePreviews?.[previewKey];
 const smokePreview=new Set((state.smokeItems?.includes(aimingItem)?state.smokePreviews?.[previewKey]??[]:[]).map(c=>c.join(',')));
 const smokeCells=new Set((state.smokeCells??[]).map(c=>pos(c).join(',')));
 const soundCells=new Set((lurePreview?.cells??[]).map(c=>c.join(',')));
 const listeners=new Set(lurePreview?.listeners??[]);
 const chilled=new Set(aimingItem==="frost_smoke"?state.frostPreviews?.[previewKey]??[]:[]);

 const chargedWater=new Set(state.enemies.flatMap(e=>(e.intent.water??[]).map(cell=>cell.join(','))));
 const fireCells=new Set((state.fireCells??[]).map(cell=>cell.join(',')));
 const danger=[...(state.dangerCells??state.enemies.flatMap(e=>e.intent.cells)),...state.returning.filter(w=>w.owner==='enemy').flatMap(w=>w.cells)],aimed=aim?Object.keys(dirs).flatMap(d=>ray(d)):[];
 const projection=perspectiveBoard?'matrix(1 .16 -.36 .66 0 0) ':'';
 let solids='';
 const floorFeatures=featuresByCell();
 let svg=`<g transform="${projection}translate(${-ox*60},${-oy*60})">`;
 for(let y=oy;y<oy+height;y++)for(let x=ox;x<ox+width;x++){
  const key=x+','+y,visible=seen.has(key);
  if(!known.has(key)){svg+=`<rect x="${x*60}" y="${y*60}" width="60" height="60" fill="#141522"/>`;continue}
  if(mappedKeys.has(key)){
   const wall=walls.has(key);
   const label=wall?'测绘 · 石墙':same([x,y],state.exit)?'测绘 · 阶梯':doors.has(key)?'测绘 · 石门':'测绘 · 通道';
   svg+=`<g ${!wall||inspecting?`data-cell="${key}" role="button" aria-label="${label}"`:''}>
    <rect x="${x*60}" y="${y*60}" width="60" height="60" fill="${wall?'#202431':'#303948'}"/>
    ${wall?'':`<rect x="${x*60+3}" y="${y*60+3}" width="54" height="54" fill="none" stroke="#546177" stroke-dasharray="5 4"/>`}
    ${same([x,y],state.exit)?art.prop('stairs',x,y,true):''}</g>`;
   continue;
  }
  const wall=walls.has(key),enemy=state.enemies.find(e=>e.x===x&&e.y===y),hero=state.player.x===x&&state.player.y===y;
  const doorway=doors.has(key),openDoor=openDoors.has(key);
  const tile=state.terrain.find(t=>t.x===x&&t.y===y);
  const features=floorFeatures.get(key)??[];
  const available=features.filter(f=>!f.used);
  const feature=available[0]??features[0];
  const count=countFeatures(available);
  const supplies=count>1?`${count} 项地面物品`:feature?(feature.used?'已使用的':'')+featureName(feature):'';
  const doorLabel=doorway?(openDoor?'打开的门':'关闭的门 · 踏入开启'):'';
  const onFire=fireCells.has(key);
  const groundLabel=[doorLabel,onFire?'地火 · 下一拍 1 伤':'',supplies].filter(Boolean).join('，')||(tile?terrainName(tile):`地面 ${x},${y}`);
  const box=available.some(f=>f.kind==='supply_choice');
  const label=same([x,y],state.lock)?((lockStyle()?.name??'库房')+'锁门，点击使用钥匙'):same([x,y],state.exit)?(hero?(state.floorKind==='relic'?'终点祭坛，点击完成试炼':(state.exitUnlocked?'阶梯，点击下楼':'阶梯已封锁')):'阶梯'):enemy?enemy.name+'，'+enemy.intent.label+'，点击查看信息':box?(hero?'战术补给箱，点击打开':'战术补给箱，点击前往并打开'):hero?(supplies?'你的位置，'+supplies:'你的位置'):groundLabel;
  svg+=`<g ${wall?'':`data-cell="${key}" role="button" tabindex="-1" aria-label="${esc(label)}"`} opacity="${visible?1:.38}">`;
  if(wall){
   if(inspecting||secretClues.has(key))svg+=`<rect data-cell="${key}" x="${x*60}" y="${y*60}" width="60" height="60" fill="transparent" role="button" aria-label="${secretClues.has(key)?'墙上的刻痕':'石墙'}"/>`;
   if(perspectiveBoard&&visible){
    const nearFloor=[[x-1,y],[x+1,y],[x,y+1],[x,y-1]].some(([a,b])=>{
     const adjacent=a+','+b;
     return known.has(adjacent)&&!walls.has(adjacent);
    });
    solids+=raisedWall(x,y,wallColor,nearFloor);
   }
   svg+=art.stoneWall(x,y,wallColor,{north:isFloor(x,y-1,x,y),east:isFloor(x+1,y,x,y),
    south:isFloor(x,y+1,x,y),west:isFloor(x-1,y,x,y)});
   if(secretClues.has(key))svg+=`<path d="M${x*60+25} ${y*60+11}h3v4h4v-4h3" stroke="#e1c27d" stroke-width="2" fill="none" pointer-events="none"/>`;
   svg+='</g>';
   continue;
  }
  svg+=art.ground(x,y,floorColor,{north:walls.has(x+','+(y-1)),
   west:walls.has((x-1)+','+y),east:walls.has((x+1)+','+y)});
  const locked=key===lock;
  if(doorway||locked)svg+=art.doorway(x,y,wallColor,verticalDoors.has(key),openDoor&&!locked,locked,isFloor(x,y+1,x,y));
  const marking=locked&&lockStyle();
  if(marking)svg+=`<circle cx="${x*60+45}" cy="${y*60+15}" r="9" fill="#1e1920" stroke="${marking.color}" pointer-events="none"/>
   <text x="${x*60+45}" y="${y*60+19}" text-anchor="middle" fill="${marking.color}" font-size="13" pointer-events="none">${marking.glyph}</text>`;
  if(tile){
   if(['high_grass','grass'].includes(tile.kind))svg+=art.prop(tile.kind,x,y);
   else if(tile.kind==='water')svg+=`<path d="M${x*60+2} ${y*60+2}h56v56h-56z" fill="${tile.ice_until?'#7fc7e7a0':'#387c9b77'}"/>
   <path d="M${x*60+8} ${y*60+36}${tile.ice_until?'l13-9 9 5 13-11':'q8-8 16 0t16 0'}" fill="none" stroke="${tile.ice_until?'#d7f5ff':'#90cde0'}" stroke-width="2"/>`;
   else if(tile.kind==='web')svg+=`<path d="M${x*60+9} ${y*60+9}l42 42m0-42L${x*60+9} ${y*60+51}m0-21h42m-21-21v42" stroke="#dec9ea" stroke-width="2" opacity=".75"/>`;
   else if(tile.kind==='sun_plant')svg+=`<circle cx="${x*60+30}" cy="${y*60+30}" r="12" fill="#efd483" stroke="#765537" pointer-events="none"/>`;
   else if(tile.kind==='root_plant')svg+=`<path d="M${x*60+30} ${y*60+38}v-18m0 14l-12-9m12 5l12-10m-12 18l-15 6m15-6l13 6" fill="none" stroke="#b6cc78" stroke-width="4" pointer-events="none"/>`;
   else if(tile.kind==='trap')svg+=`<rect x="${x*60+16}" y="${y*60+16}" width="28" height="28" rx="3" fill="#24222d" stroke="${tile.armed?'#dea674':'#727278'}" stroke-width="3"/><text x="${x*60+30}" y="${y*60+36}" text-anchor="middle" fill="${tile.armed?'#ffd298':'#98949c'}" font-size="16">${tile.armed?(({alarm:'!',dart:'×',grip:'⟐'}[tile.mechanism]??'×')):'·'}</text>`;
   else if(tile.kind==='ice')svg+=`<rect x="${x*60+4}" y="${y*60+4}" width="52" height="52" fill="#81d8f26b" stroke="#c0f1ff"/>`;
   else if(tile.kind==='mirror')svg+=`<path d="M${x*60+12} ${y*60+(tile.slash==='/'?48:12)}L${x*60+48} ${y*60+(tile.slash==='/'?12:48)}" stroke="${tile.rotating?'#efc46a':'#92dce7'}" stroke-width="7"/><text x="${x*60+30}" y="${y*60+57}" text-anchor="middle" fill="#efc46a" font-size="11">${tile.rotating?'↻ 击中旋转':''}</text>`;
   else if(tile.kind==='rubble')svg+=`<rect x="${x*60+6}" y="${y*60+6}" width="48" height="48" fill="#725c51"/><path d="M${x*60+28} ${y*60+7}l-6 17 15 8-8 20" fill="none" stroke="#e0b78b" stroke-width="3"/>`;
   else if(tile.stage===2)svg+=`<ellipse cx="${x*60+30}" cy="${y*60+32}" rx="27" ry="23" fill="#05080d" stroke="#b1766c"/>`;
   else svg+=`<path d="M${x*60+10} ${y*60+12}l20 13-9 12 24 11m-15-23 18-12" fill="none" stroke="${tile.stage?'#fb8b70':'#b7ad8b'}" stroke-width="${tile.stage?4:2}"/><text x="${x*60+30}" y="${y*60+56}" text-anchor="middle" fill="#ffd3b5" font-size="10">${tile.stage?'再踩即死':'脆弱'}</text>`;
  }
  if(smokeCells.has(key)||smokePreview.has(key))svg+=`<path d="M${x*60+4} ${y*60+4}h52v52h-52z"
   fill="${aimingItem==='frost_smoke'&&smokePreview.has(key)?'#9cecff':'#b3c2de'}" fill-opacity="${smokeCells.has(key)?'.32':'.18'}" stroke="#b3c2de"
   stroke-dasharray="4 5" pointer-events="none"/>`;
  if(soundCells.has(key))svg+=`<rect x="${x*60+4}" y="${y*60+4}" width="52" height="52" fill="#dac88936" pointer-events="none"/>`;
  if(lureCells.has(key))svg+=`<circle cx="${x*60+30}" cy="${y*60+30}" r="15" fill="${same(lureSelection,[x,y])?'#ebd89090':'#d8d78430'}" stroke="#ebd890" stroke-dasharray="3 4" pointer-events="none"/>`;
  if(warnings.some(c=>same(c,[x,y])))svg+=`<rect x="${x*60+7}" y="${y*60+7}" width="46" height="46" fill="#d8a45524" stroke="#edba71" stroke-width="2" stroke-dasharray="5 4" pointer-events="none"/>`;
  if(danger.some(c=>same(c,[x,y])))svg+=`<rect x="${x*60+4}" y="${y*60+4}" width="52" height="52" fill="#b45b4855" stroke="#e9a082"/><text x="${x*60+30}" y="${y*60+52}" text-anchor="middle" fill="#edaa8d" font-size="12">!</text>`;
  if(onFire)svg+=`<path data-ground-fire d="M${x*60+20} ${y*60+37}q-5-8 4-17 0 7 4 7 4-5 2-12 11 8 10 19-3 10-12 9-6 0-8-6z" fill="#ed804b" stroke="#ffd384" stroke-width="2" pointer-events="none"/>`;
  if(aimingItem==='frost_smoke'&&smokePreview.has(key)&&tile?.kind==='water')
   svg+=`<text data-freeze-water x="${x*60+30}" y="${y*60+39}" text-anchor="middle" fill="#d7f5ff" font-size="24">❄</text>`;
  if(chargedWater.has(key))svg+=`<path data-electric-water d="M${x*60+31} ${y*60+13}l-9 17h12l-6 15 15-20H32l6-12z" fill="#b2eaff" pointer-events="none"/>`;
  if(aimed.some(c=>same(c,[x,y])))svg+=`<rect x="${x*60+5}" y="${y*60+5}" width="50" height="50" fill="#c7e7a822" stroke="#c7e7a8" stroke-dasharray="4 4"/>`;
  if(feature&&tile?.kind!=='rubble'){
   svg+=art.prop(feature.kind,x,y,feature.used);
   if(count>1){
    const cx=x*60+47,cy=y*60+12;
    svg+=`<g pointer-events="none"><circle cx="${cx}" cy="${cy}" r="9" fill="#25252e" stroke="#ddbd7c"/><text x="${cx}" y="${cy+4}" text-anchor="middle" fill="#ffe7af" font-size="11">${count}</text></g>`;
   }
  }
  if(aim&&Object.values(aimDetails||{}).some(result=>same(result.landing,[x,y])))svg+=`<circle cx="${x*60+30}" cy="${y*60+30}" r="14" fill="none" stroke="#8bd9e1" stroke-width="3" pointer-events="none"/>`;
  if(same([x,y],state.exit))svg+=art.prop(state.floorKind==='relic'?'wonder':'stairs',x,y,!state.exitUnlocked);
  svg+='</g>';
 }
 svg+=solids;
 if(travelPath.length){
  let [x,y]=pos(state.player);
  for(const step of travelPath){
   const [dx,dy]=dirs[step];x+=dx;y+=dy;
   svg+=`<circle cx="${x*60+30}" cy="${y*60+30}" r="4" fill="#e3c581" pointer-events="none"/>`;
  }
 }
 if(travelTarget||pausedTravel){
  const [x,y]=travelTarget||pausedTravel;
  svg+=`<circle cx="${x*60+30}" cy="${y*60+30}" r="12" fill="none" stroke="#e3c581" stroke-width="2" stroke-dasharray="${travelTarget?'none':'4 3'}" pointer-events="none"/>`;
 }
 for(const e of state.enemies){if(e.intent.action==='move'&&e.intent.target)svg+=`<path d="M${e.x*60+30} ${e.y*60+30}L${e.intent.target[0]*60+30} ${e.intent.target[1]*60+30}" stroke="${e.intent.mob_jump||e.kind==='slipsnake'?'#85e3d8':'#ddbd7c'}" stroke-width="3" stroke-dasharray="4 4" pointer-events="none"/>`;if(chilled.has(e.id))svg+=`<circle data-frost-preview="${e.id}" cx="${e.x*60+30}" cy="${e.y*60+30}" r="24" fill="none" stroke="#9cecff" stroke-width="3" stroke-dasharray="4 3" pointer-events="none"/>`;if(listeners.has(e.id))svg+=`<circle cx="${e.x*60+30}" cy="${e.y*60+30}" r="24" fill="none" stroke="#ffdf91" stroke-width="3" pointer-events="none"/>`;svg+=art.actor(e.x,e.y,e.kind,e.id,state.heroColor,e);if(e.intent.action==='guard')svg+=`<circle cx="${e.x*60+30}" cy="${e.y*60+30}" r="25" stroke="#bdb0dc" fill="none" pointer-events="none"/>`}
 if(!state.falls.some(f=>f.id==='hero'))svg+=art.actor(state.player.x,state.player.y,'hero',0,state.heroColor);
 for(const wave of state.returning)for(const cell of wave.cells)svg+=`<circle cx="${cell[0]*60+30}" cy="${cell[1]*60+30}" r="21" fill="none" stroke="${wave.owner==='hero'?'#9edbd4':'#eb978a'}" stroke-dasharray="4 6" pointer-events="none"/>`;
 if(showEffects)for(const fall of state.falls)svg+=`<g class="falling" style="transform-origin:${fall.cell[0]*60+30}px ${fall.cell[1]*60+30}px">${art.actor(...fall.cell,fall.kind,fall.id==='hero'?0:fall.id,state.heroColor)}</g>`;
 if(showEffects)for(const fx of state.effects.filter(f=>f.kind!=='fall'))svg+=art.effects(fx,state.heroColor);
 $('board').innerHTML=svg+'</g>';
 let mini='';
 for(const [x,y] of charted){const key=x+','+y;mini+=`<rect ${walls.has(key)&&!inspecting?'':`data-cell="${key}"`} x="${x*8}" y="${y*8}" width="8" height="8" fill="${mappedKeys.has(key)?(walls.has(key)?'#282d3a':'#505e78'):walls.has(key)?'#41534c':seen.has(key)?'#98b48d':'#576f66'}"/>`}
 for(const tile of state.terrain)mini+=`<rect data-cell="${tile.x},${tile.y}" x="${tile.x*8}" y="${tile.y*8}" width="8" height="8" fill="${tile.ice_until?'#abdef0':({fragile:'#d38a73',high_grass:'#88a662',grass:'#667854',root_plant:'#b6cc78',sun_plant:'#efd483'}[tile.kind]||(tile.kind==='trap'?(tile.armed?'#dfaa77':'#727278'):'#b7d3de'))}"/>`;
 for(const features of floorFeatures.values()){
  const [f]=features;
  mini+=`<rect data-cell="${f.x},${f.y}" x="${f.x*8+1}" y="${f.y*8+1}" width="6" height="6" fill="${features.every(item=>item.used)?'#6a7772':'#ddbd7c'}"/>`;
 }
 if(state.exit)mini+=`<rect data-cell="${state.exit.join(',')}" x="${state.exit[0]*8}" y="${state.exit[1]*8}" width="8" height="8" fill="#ddd6a4"/>`;
 for(const e of state.enemies)mini+=`<rect data-cell="${e.x},${e.y}" x="${e.x*8+1}" y="${e.y*8+1}" width="6" height="6" fill="#e09a7b"/>`;
 mini+=`<rect x="${state.player.x*8}" y="${state.player.y*8}" width="8" height="8" fill="#edffc4" stroke="#172128" pointer-events="none"/>`;
 if(state.lock)mini+=`<rect data-cell="${state.lock.join(',')}" x="${state.lock[0]*8}" y="${state.lock[1]*8}" width="8" height="8" fill="#aa754c"/>`;
 for(const cell of state.secretClues??[])mini+=`<rect data-cell="${cell.join(',')}" x="${cell[0]*8+1}" y="${cell[1]*8+1}" width="6" height="6" fill="#e1c27d"/>`;

 if(travelPath.length){
  let [x,y]=pos(state.player);
  let line=`M${x*8+4} ${y*8+4}`;
  for(const step of travelPath){
   const [dx,dy]=dirs[step];x+=dx;y+=dy;
   line+=`L${x*8+4} ${y*8+4}`;
  }
  mini+=`<path d="${line}" fill="none" stroke="#edcd8b" stroke-width="1.4"
   stroke-dasharray="2 2" pointer-events="none"/>`;
 }
 if(travelTarget||pausedTravel){
  const [x,y]=travelTarget||pausedTravel;
  mini+=`<circle cx="${x*8+4}" cy="${y*8+4}" r="5" fill="none" stroke="#edcd8b" stroke-width="2" stroke-dasharray="${travelTarget?'none':'2 2'}" pointer-events="none"/>`;
 }
 $('minimap').setAttribute('viewBox', `0 0 ${state.width*8} ${state.height*8}`);
 $('minimap').innerHTML=mini;
}
function renderGrowth(){
 const g=state.growth, stats=state.waveStats;
 const weapon=state.weapons.find(w=>w.id===state.weapon);
 const hero=state.classes.find(c=>c.id===state.heroClass);
 $('loadout-title').textContent=`${hero?.name||'自由发射器'} · ${weapon.name} +${g.level}`;
 const option=(key,item,selected)=>`<button data-${key}="${item.id}" aria-pressed="${selected}"><b>${esc(item.name)}</b><small>${esc(item.description)}</small></button>`;
 $('loadout').innerHTML=(hero?'':state.weapons.map(w=>option('equip',w,w.id===state.weapon)).join(''))
  +state.modes.map(m=>option('tune',m,m.id===state.mode)).join('');
 const growthButton=(action,key,available,title,description)=>`<button data-growth="${action}" data-key="${key}" data-available="${available}"><b>${esc(title)}</b><small>${esc(description)}</small></button>`;
 const next=['波伤害 +1','基础射程 +1','波伤害再 +1'][g.level];
 $('growth-weapon').innerHTML=`<p class="weapon-stats">波 ${stats.damage} 伤 · 射程 ${stats.range} · ${stats.pierce===99?'扇面命中':'至多命中 '+stats.pierce+' 个'}</p>
 <h3>锻造 <small>${g.cores} 核心</small></h3>
 ${growthButton('forge','',g.cores>0&&g.level<3,next?'强化至 +'+(g.level+1):'已达 +3',next||'已完成武器锻造')}
 <h3>刻印 <small>${g.shards} 碎片</small></h3>
 <div class="growth-grid">${g.runes.map(r=>growthButton('etch',r.id,g.shards>0&&r.compatible&&r.id!==g.rune,
  r.name+(r.id===g.rune?' · 已装备':''),r.compatible?r.description:'当前波形无法使用')).join('')}</div>`;
 $('character-avatar').innerHTML=art.portrait(state.heroColor);
 $('hud-avatar').innerHTML=art.portrait(state.heroColor);
 $('character-vitals').textContent=`生命 ${state.player.hp}/${state.maxHp??6} · 能量 ${state.player.energy}/${state.energyCap}`;
 const learned=g.talents.filter(t=>t.learned);
 $('talent-list').innerHTML=learned.length?learned.map(t=>`<div class="upgrade"><b>${esc(t.name)}</b><p>${esc(t.description)}</p></div>`).join(''):'<p class="empty">尚未学习天赋。</p>';
 $('growth-status').textContent=g.safe?'锻造和刻印作用于当前发射器。更换改装消耗一拍。':'安全时可锻造或刻印。';
}

const ITEM_GLYPHS={heal:'✚',smoke:'≋',echo_smoke:'≋',frost_smoke:'❄',lure:'◇',grass_seed:'✧',sun_seed:'✹',chart:'▤',recall:'↶',ankh:'✦',terror:'⇠'};
const QUICK_ITEMS=[
 {key:'q',storage:'bobozan-quick-item',id:'heal'},
 {key:'e',storage:'bobozan-quick-item-e',id:'smoke'}
];
for(const slot of QUICK_ITEMS){
 try{slot.id=localStorage.getItem(slot.storage)??slot.id}catch{}
}
function renderQuickItems(){
 const available=new Map(state.inventory.filter(item=>!item.passive).map(item=>[item.id,item]));
 $('quick-items').innerHTML=QUICK_ITEMS.map(({key,id})=>{
  const item=available.get(id);
  const select=document.querySelector(`[data-quick-bind="${key}"]`);
  select.innerHTML='<option value="">不设置</option>'+[...available.values()].map(({id,name})=>
   `<option value="${esc(id)}">${esc(name)}</option>`).join('');
  if(id&&!item)select.add(new Option('已绑定 · 当前未携带',id));
  select.value=id;
  if(!id)return '';
  const count=state.inventory.filter(entry=>entry.id===id).length;
  return `<button type="button" data-quick-use="${key}" title="使用快捷道具 · ${key.toUpperCase()}" ${item?'':'disabled'}>
   ${item?`${ITEM_GLYPHS[id]??'•'} ${esc(item.name)} ×${count}`:'空'} <kbd>${key.toUpperCase()}</kbd></button>`;
 }).join('');
}
function throwTargets(item=aimingItem){
 return (item==='plant'?state.plantTargets:state.lureTargets)??[];
}
function useItem(item){
 if(item!=='plant'&&!state.thrownItems?.includes(item))return send('item',null,item);
 if(!throwTargets(item).length){toast(item==='plant'?'附近没有可播种的空地。':'附近没有可投掷的空地。',true);return}
 closeDialogs();
 cancelTravel();
 aim=null;
 aimingItem=item;
 lureHover=null;
 lureSelection=null;
 refreshPreview();
 renderControls();
 renderBoard();
}
function useQuickItem(key){
 const slot=QUICK_ITEMS.find(slot=>slot.key===key);
 const item=state?.inventory.find(entry=>entry.id===slot?.id&&!entry.passive);
 if(!canAct()||!item)return;
 setInspecting(false);
 cancelTravel();
 useItem(item.id);
}

let selectedBagItem=null;
function renderBagItem(){
 const item=state.inventory.find(entry=>entry.id===selectedBagItem);
 $('bag-item-detail').hidden=!item;
 if(!item)return;
 $('bag-use-item').hidden=!!item.passive;
 $('bag-plant-item').hidden=!item.plantable;
 $('bag-item-name').textContent=item.name;
 $('bag-drop-item').textContent=item.plantable?'放下一颗 · 1 拍':'放下 · 1 拍';
 $('bag-item-description').textContent=item.description;
}
function renderBag(){
 renderQuickItems();
 $('drink-dew').textContent=`饮用露珠 ${state.dew??0}/${state.dewCapacity??3} · 1 拍`;
 $('bag-count').textContent=`${state.bagSlots.length} / ${state.bagCapacity} 槽 · 钥匙 ${state.keys}`;
 $('bag-slots').innerHTML=Array.from({length:state.bagCapacity},(_,i)=>{
  const slot=state.bagSlots[i];
  if(!slot)return `<div class="bag-slot empty-slot" aria-label="第 ${i+1} 槽，空"></div>`;
  const item=state.inventory.find(entry=>entry.id===slot.id);
  const glyph=ITEM_GLYPHS[item.id]||'•';
  return `<button class="bag-slot" data-item="${esc(item.id)}" aria-pressed="${item.id===selectedBagItem}">
   <span aria-hidden="true">${glyph}</span><b>${esc(item.name)}${slot.count>1?' ×'+slot.count:''}</b></button>`;
 }).join('');
 renderBagItem();
 $('recipes').innerHTML=(state.recipes??[]).map(recipe=>{
  const costs=recipe.ingredients.map(i=>({name:i.name,owned:i.owned,count:i.count}));
  if(recipe.dew)costs.push({name:'露珠',owned:state.dew,count:recipe.dew});
  return `<div class="recipe">
   <b>${esc(recipe.name)}</b><ul class="recipe-costs" aria-label="材料持有和所需数量">
    ${costs.map(({name,owned,count})=>`<li>${esc(name)} ${owned}/${count}
     ${owned<count?`<span>缺 ${count-owned}</span>`:''}</li>`).join('')}</ul>
   <small>${esc(recipe.description)}</small>
   <button type="button" data-recipe="${esc(recipe.id)}" data-available="${!recipe.reason}" ${!canAct()||recipe.reason?'disabled':''}>制作 · 1 拍</button>
   <small>${recipe.batches?`材料够做 ${recipe.batches} 份`:''}
    ${recipe.reason?esc(recipe.reason):''}</small>
  </div>`;
 }).join('');
 $('bag-relics').textContent=state.bagRelics.length
  ?state.bagRelics.map(relic=>`${relic.name} · ${relic.description}`).join('　')
  :'获得扩容遗物后可增加槽位。';
}

function renderTalentChoice(){
 const dialog=$('talent-dialog'), offer=state.talentChoice;
 if(!offer){if(dialog.open)dialog.close();return}
 if(dialog.open)return;
 $('talent-title').textContent=`第 ${offer.depth} 层 · 天赋`;
 $('talent-instruction').textContent=`选 ${offer.limit} 项。本层的选择机会只出现一次。`;
 $('talent-options').innerHTML='<legend>本层天赋</legend>'+offer.options.map(t=>
  `<label class="talent-option"><input type="checkbox" value="${esc(t.id)}"><span><b>${esc(t.name)}</b><small>${esc(t.description)}</small></span></label>`).join('');
 $('confirm-talents').disabled=true;
 $('talent-feedback').textContent='';
 closeDialogs();
 dialog.showModal();
}

function activeConditions(){
 const conditions=[];
 if(state.trapClues)conditions.push(['trap-clues','⌕','机关痕迹','这个房间可能藏有机关。按 X 搜查周围两格内可见的地板，消耗一拍。']);
 if(state.counter)conditions.push(['counter','✦','反击 +'+state.waveStats.counterBonus,'成功挡伤后获得。移动或攒能不会消耗它，下一发波或重波会使用这次加成。']);
 if(state.poisoned)conditions.push(['poison','☣','中毒 · 1 伤','下一拍会受到 1 点毒伤。可在结算前使用疗愈药剂，也可用普通防抵挡。']);
 if(state.snared)conditions.push(['snared','⟐','夹足 · 1 拍','本拍不能移动或用飞雷神。其他行动仍可使用。']);
 else if(state.movementLocked)conditions.push(['frost','❄','霜冻 · 1 拍','本拍不能移动，也无法用飞雷神。可以攒、出波或防来度过这一拍。']);
 const cloud=state.smokeCells?.find(c=>same(pos(c),pos(state.player)));
 if(cloud)conditions.push(['cloud','≋','身处烟雾 · '+cloud.turns+' 拍','远处敌人无法隔着烟雾发现你。相邻敌人仍可攻击，能量波仍可穿过。']);
 if(state.smokeRemaining)conditions.push(['smoke','≋','烟雾 · '+state.smokeRemaining+' 拍','烟雾会遮蔽敌人的视线，但不会取消已经锁定的攻击。']);
 if(state.returning.some(w=>w.owner==='enemy'))conditions.push(['return','↶','敌方回波','下拍沿原路径返回，红色虚线圈标出经过的可见地格。离开路径或防御。']);
 return conditions;
}
function renderGroundItems(){
 const items=state.groundItems??[];
 if(!items.length&&$('ground-dialog').open)$('ground-dialog').close();
 const full=items.some(feature=>feature.items.some(item=>!state.packableItems.includes(item.id)));
 $('ground-items').innerHTML=items.flatMap(feature=>feature.items.map(item=>
  `<button type="button" data-pickup="${esc(feature.id)}" data-ground-item="${esc(item.id)}"
    ${state.packableItems.includes(item.id)?'':'disabled'}>${esc(item.name)}</button>`)).join('');
 $('ground-pick-all').hidden=items.reduce((count,feature)=>count+feature.items.length,0)<2;
 $('ground-bag').hidden=!full;
}
function showGroundItems(){
 renderGroundItems();
 openPanel('ground-dialog');
}
function renderConditions(){
 $('condition-strip').innerHTML=activeConditions().map(([id,icon,label])=>
  `<button type="button" data-condition="${id}" aria-haspopup="dialog"><span aria-hidden="true">${icon}</span> ${esc(label)}</button>`).join('');
}

function renderHistory(){
 const records=state.history??[];
 $('run-history').innerHTML=records.length?records.map((record,index)=>{
  const hero=state.classes.find(c=>c.id===record.heroClass)?.name??'自由发射器';
  const won=record.result==='victory';
  const stats=record.stats;
  return `<details class="run-record">
   <summary><b>${won?'通关':'倒下'} · 第 ${record.depth} 层</b><span>${esc(hero)} · ${record.turns} 拍</span></summary>
   <p>种子 ${record.seed}${record.cause?' · '+esc(record.cause):''}</p>
   <p>击败 ${stats.defeated} · 暗门 ${stats.secrets} · 陷阱 ${stats.traps} · 遗物 ${record.relics}</p>
   <button type="button" data-retry-record="${index}">重试此种子与职业</button>
  </details>`;
 }).join(''):'<p class="muted">完成一次冒险后会出现在这里。</p>';
}
function render(showEffects=false){
 $('room-name').textContent=state.roomName;
 const theme={water:'积水',grass:'草木茂盛'}[state.floorTheme];
 $('floor-theme').hidden=!theme;
 $('floor-theme').textContent=theme?' · '+theme:'';
 $('floor-label').textContent=state.region+' · '+state.depth+'/'+state.lastFloor+' 层';
 renderGrowth();renderBag();
 $('tactics').innerHTML=
  (state.lock&&Math.abs(state.lock[0]-state.player.x)+Math.abs(state.lock[1]-state.player.y)===1?'<button data-unlock>打开锁门</button>':'')+
  (unopenedSupplyAt(pos(state.player))?'<button data-open-supply>打开补给箱</button>':'')+
  (state.groundItems?.length?'<button data-ground>脚下物品</button>':'');
 $('turn').textContent=String(state.turn).padStart(2,'0');$('seed').textContent='SEED '+state.seed;
 $('room-status').textContent=state.result?(state.result==='victory'?'试炼完成':'冒险结束'):state.choices.length?'选择旅途馈赠':state.returning.length?'回旋波即将返回':state.pursuing?(state.enemies.find(e=>e.intent.action==='notice')?'敌人刚发现你':'敌人警觉'):'探索中';
 $('route').textContent=`${state.roomStates.filter(room=>room.discovered).length}/${state.roomStates.length} 区域`;
 renderConditions();
 document.querySelector('[data-action="wave"] small').textContent=`消耗 ${state.waveStats.waveCost??1} · 伤害 ${state.waveStats.damage}`;
 document.querySelector('[data-action="heavy"] small').textContent=`消耗 ${state.waveStats.heavyCost} · 伤害 ${state.waveStats.heavyDamage}`;
 document.querySelector('[data-action="guard"] small').textContent=`${state.mode==='armor'?'消耗 1 · ':''}挡 ${state.waveStats.guardLimit} 伤`;
 $('hp').textContent=state.player.hp+' / '+(state.maxHp??6);$('energy').textContent=state.player.energy+' / '+state.energyCap;
 $('hp-bar').innerHTML=Array.from({length:state.maxHp??6},(_,i)=>`<i class="pip ${i<state.player.hp?'on':''}"></i>`).join('');
 $('energy-bar').innerHTML=Array.from({length:state.energyCap},(_,i)=>`<i class="pip ${i<state.player.energy?'on':''}"></i>`).join('');
 $('enemies').innerHTML=state.enemies.map(e=>`<div class="enemy"><div class="enemy-line"><span class="enemy-name"><span class="enemy-badge">${e.id+1}</span>${esc(e.name)}</span><span class="enemy-hp">${e.disguised?'状态未知':`${e.hp} 血 · ${e.energy} 能量`}${e.burning?' · 灼烧 '+e.burning:''}${e.frost_stacks?' · 霜 '+e.frost_stacks:''}${e.frozen?' · 冻结':''}</span></div><div class="enemy-intent">${esc(e.intent.label)} ${e.intent.direction?arrows[e.intent.direction]:''}</div></div>`).join('')||'<p class="empty">当前视野内没有敌人。<br>雾后的动静仍然未知。</p>';
 const owned=new Map(state.upgrades.map(u=>[u.id,u.name]));
 const names={heart:'护心',refund:'余势',echo:'回响',bag:'蓄能袋',pierce:'穿透',heavy:'重波'};
 $('upgrade-count').textContent=state.upgrades.length+' / '+(state.upgradeCount??6);
 $('upgrades').innerHTML=state.upgrades.map(u=>`<div class="upgrade">✦ ${esc(u.name)}<p>${esc(u.description)}</p></div>`).join('')||'<p class="empty">区域遗物宝箱和守关者会提供遗物。</p>';
 $('upgrades').innerHTML+=state.builds.map(b=>`<div class="upgrade">${esc(b.name)} · ${b.active?'已激活':b.requires.map(k=>names[k]).join(' + ')}<p>${esc(b.effect)}</p></div>`).join('');
 if(owned.has('echo')) $('upgrades').innerHTML+=`<p>回响已累计 ${state.echoProgress} 次攒</p>`;
 if(owned.has('heart')) $('upgrades').innerHTML+=`<p>护心本区域剩余 ${state.heartLeft} 次</p>`;
 renderHistory();
 $('log').innerHTML=state.log.map(t=>`<li>${esc(t)}</li>`).join('');
 renderBoard(showEffects);if($('ground-dialog').open)renderGroundItems();renderLandmarks();renderControls();renderTalentChoice();
 if(state.talentChoice)return;
 if(state.choices.length){$('rewards').innerHTML=state.choices.map(c=>`<button data-choice="${c.id}" data-blocked="${!!c.blocked}" ${c.blocked?'disabled':''}><b>${esc(c.name)} ↗</b><small>${esc(c.description)}${c.blocked?' · 背包已满':''}</small></button>`).join('');const supply=state.choices[0].supply;$('reward-title').textContent=supply?'选择一件战术补给':'选择一件遗物';$('reward-description').textContent=supply?'选中的道具放入背包，另一件留在箱中封存。':'选择一项，本次冒险持续生效。';$('skip-reward').textContent=supply?'稍后再选':'跳过本次奖励';if(!$('reward-dialog').open){closeDialogs();$('reward-dialog').showModal()}}
 else if($('reward-dialog').open)$('reward-dialog').close();
 if(state.result&&showEffects&&state.falls.length){setTimeout(()=>render(),800);return}
 if(state.result&&displayedResult!==state.result){
  displayedResult=state.result;
  closeDialogs();
  const won=state.result==='victory', stats=state.runStats??{};
  $('result-title').textContent=won?'光，从地牢尽头照来。':'这次，先到这里。';
  $('result-description').textContent=`${won?'完成了试炼。':'止步于「'+state.roomName+'」。'} ${!won&&state.defeatCause?'倒下原因：'+state.defeatCause+'。 ':''}种子 ${state.seed}。`;
  const totals=[['抵达楼层',state.depth],['行动拍数',state.turn],['击败敌人',stats.defeated??0],
   ['发现暗门',stats.secrets??0],['触发陷阱',stats.traps??0],['获得遗物',state.upgrades.length]];
  $('result-stats').innerHTML=totals.map(([label,value])=>`<div><dt>${label}</dt><dd>${value}</dd></div>`).join('');
  $('result-dialog').showModal();
 }

}
async function send(action,direction=null,choice=null){if(busy||!state)return false;let success=false;busy=true;aim=null;aimingItem=null;refreshPreview();renderControls();$('saved').textContent='保存中…';try{const depth=state.depth;state=await api('action',{action,direction,choice,version:state.version});if(state.result||state.depth!==depth)forgetTravel();else if(same(pos(state.player),pausedTravel))setPausedTravel(null);toast(state.log[0]||'继续探索。');render(true);clearTimeout(fxTimer);fxTimer=setTimeout(()=>renderBoard(),state.falls.length?780:540);$('saved').textContent='● 进度已保存';success=true}catch(e){toast(e.name==='AbortError'?'连接超时，正在恢复已保存局面。':e.message,true);try{state=await api('state');render();$('saved').textContent='● 已恢复存档'}catch{$('saved').textContent='连接断开 · 刷新重试'}}finally{busy=false;renderControls()}return success}
let previewRequest=0;
async function refreshPreview(){
 const request=++previewRequest;
 const panel=$('shot-preview');
 aimDetails=null;
 if(!aim){panel.hidden=true;return}
 const action=aim, version=state.version;
 panel.hidden=false;
 panel.textContent='计算伤害…';
 try{
  const previews=await Promise.all(Object.keys(dirs).map(async direction=>[
   direction,await api('preview',{action,direction,version})
  ]));
  if(request===previewRequest&&aim===action&&state.version===version){
   aimDetails=Object.fromEntries(previews);
   panel.innerHTML=previews.map(([direction,result])=>{
    const hits=result.hits.map(h=>h.name+' '+h.damage+'伤').join('、')||'无可见命中';
    const received=result.received??[];
    const damage=received.reduce((total,hit)=>total+hit.damage,0);
    const risk=damage?`<strong class="shot-risk">预计受伤 ${damage}</strong>
      <small>${esc(received.map(hit=>hit.name).join('、'))}</small>`:'';
    const reflected=result.reflected?`<small>预计反弹 ${result.reflected} 伤</small>`:'';
    const events=result.events?.length?`<small>${esc(result.events.join('、'))}</small>`:'';
    return `<button type="button" class="shot-direction" data-preview-direction="${direction}">
     <b>${arrows[direction]}</b><span>${esc(hits)}</span>${risk}${reflected}${events}</button>`;
   }).join('');
   renderBoard();
  }
 }catch{
  if(request===previewRequest&&aim===action&&state.version===version)panel.textContent='局面变化，请重新瞄准。';
 }
}
$('shot-preview').addEventListener('click',event=>{
 const button=event.target.closest('[data-preview-direction]');
 if(button&&aim&&canAct())direction(button.dataset.previewDirection);
});
function chooseAction(action){aimingItem=null;setInspecting(false);cancelTravel();if(!canAct())return;const b=document.querySelector(`[data-action="${action}"]`);if(b?.disabled)return;if(['wave','heavy','reflect'].includes(action)){aim=aim===action?null:action;toast(aim==='reflect'?'选择反射方向，确认后消耗 1 能量。':aim?'按方向键或点击射线空格出波；点击敌人查看信息。':'已取消瞄准。');refreshPreview();renderBoard();renderControls()}else send(action)}
function direction(d){
 if(aimingItem){aimingItem=null;renderControls();renderBoard()}
 setInspecting(false);
 cancelTravel();if(!canAct())return;
 const cell=[state.player.x+dirs[d][0],state.player.y+dirs[d][1]];
 const tile=state.terrain.find(t=>same(pos(t),cell));
 const occupied=state.enemies.some(enemy=>same(pos(enemy),cell));
 if(!aim&&!occupied&&!state.movementLocked&&tile){
  const warning=tile.kind==='fragile'&&tile.stage>=1
   ?['这一步会坠落。','目标格已开裂或塌陷，踩入会立即死亡。防御与护心无法抵挡坠落。']
   :tile.kind==='trap'&&tile.armed
    ?[terrainName(tile), '可以在远处用波先触发。'+({alarm:'直接踩踏会招来附近敌人。',dart:'直接踩踏会受到 1 点伤害。',grip:'直接踩踏会让下一拍无法移动或用飞雷神。'}[tile.mechanism]??'')]
    :null;
  if(warning){
   pendingFall={direction:d,version:state.version};
   $('danger-title').textContent=warning[0];
   $('danger-description').textContent=warning[1];
   $('danger-dialog').showModal();
   return;
  }
 }
 send(aim||'move',d);
}
$('confirm-fall').addEventListener('click',()=>{
 const pending=pendingFall;pendingFall=null;$('danger-dialog').close();
 if(pending&&pending.version===state.version&&canAct())send('move',pending.direction);
});
$('loadout').addEventListener('click',event=>{
 const button=event.target.closest('button');if(!button||!canAct())return;
 cancelTravel();send(button.dataset.equip?'equip':'tune',null,button.dataset.equip||button.dataset.tune);
});
async function reset(seed,heroClass){aimingItem=null;setInspecting(false);forgetTravel();if(busy)return;busy=true;renderControls();try{state=await api('reset',{version:state.version,heroClass,...(seed===undefined?{}:{seed})});aim=null;refreshPreview();displayedResult=null;closeDialogs();toast('新的冒险。先观察敌人，再行动。');render();$('saved').textContent='● 进度已保存'}catch(e){toast(e.message,true);try{state=await api('state');render()}catch{}}finally{busy=false;renderControls()}}
const enemyProfiles = {
 charger: {maxHp:2,attack:'1',description:'无能量时先攒；有能量且与你处于无遮挡的同一直线时出波，射程 4 格。否则会接近你。侧移或利用墙壁可避开已锁定的波。'},
 ram: {maxHp:2,attack:'1',description:'远处时向你接近，相邻时冲撞提前锁定的格子。冲撞不会追踪你移动后的位置，可以侧移躲开。'},
 shield: {maxHp:3,attack:'1',description:'举盾 → 卸盾空档 → 接近或冲撞，循环行动。举盾只抵挡 1 点伤害，卸盾时防御为 0；重波可以打穿盾。'},
 boss: {maxHp:6,attack:'1 / 2',description:'直线波造成 1 伤。震荡蓄力时以虚线标出范围，下一拍攻击原位置。半血后改为伤害更高的十字震荡，看到预警就开始撤离。震荡后会休整一拍。'}
};
function inspectEnemy(enemy){
 const profile=enemyProfiles[enemy.kind]||{maxHp:enemy.maxHp,attack:enemy.attack??(enemy.kind==='breaker'?2:enemy.intent.damage||1),description:enemy.description};
 $('enemy-name').textContent=enemy.name;
 $('enemy-hp').textContent=enemy.disguised?'未知':`${enemy.hp} / ${enemy.maxHp??profile.maxHp}`;
 $('enemy-attack').textContent=enemy.disguised?'未知':(enemy.intent.damage??enemy.attack??profile.attack);
 $('enemy-defense').textContent=enemy.disguised?'未知':enemy.defense?'1（护甲 / 举盾）':'0';
 const weapon=state.weapons.find(w=>w.id===enemy.emitter)?.name;
 const rune=RUNE_DETAILS[enemy.inscription];
 $('enemy-method').textContent=profile.description+(weapon?` 持有：${weapon} · ${rune}。`:'');
 $('enemy-current').textContent=`已锁定意图：${enemy.intent.label}。当前能量：${enemy.energy}。`+(enemy.stolen?' 携带偷来的能量。':'');
 $('enemy-loot').hidden=!enemy.lootHint;
 $('enemy-loot').textContent=enemy.lootHint??'';
 $('enemy-dialog').showModal();
}
let travelId=0, travelMove=null, travelPath=[], travelTarget=null, pausedTravel=null;
let fillingEnergy=false;
async function fillEnergy(){
 setInspecting(false);
 if(fillingEnergy){cancelTravel();return}
 if(!safeToFill())return;
 cancelTravel();
 const id=travelId;
 fillingEnergy=true;
 renderControls();
 try{
  while(id===travelId&&safeToFill()){
   const hp=state.player.hp;
   const charge=send('charge');
   travelMove=charge;
   const charged=await charge;
   if(travelMove===charge)travelMove=null;
   if(id!==travelId||!charged||state.player.hp<hp||state.effects.some(f=>f.kind==='revive'))break;
   if(safeToFill())await new Promise(resolve=>setTimeout(resolve,90));
  }
  if(id===travelId&&state.player.energy===state.energyCap)toast('能量已攒满。');
 }finally{
  if(id===travelId){fillingEnergy=false;renderControls()}
 }
}
function setPausedTravel(target){
 pausedTravel=target;
 $('resume-travel').hidden=!target;
 $('stop-travel').hidden=!target&&!travelTarget;
 renderControls();
}
function forgetTravel(){
 const hadPause=!!pausedTravel;
 setPausedTravel(null);
 cancelTravel();
 if(hadPause)renderBoard();
}
function setTravelTarget(target, label=''){
 travelTarget=target;
 $('stop-travel').hidden=!target&&!pausedTravel;
 $('travel-steps').textContent=label;
 renderBoard();
}
function cancelTravel(){
 if(fillingEnergy){fillingEnergy=false;renderControls()}
 const wasTraveling=!!travelTarget;
 travelId++;
 travelPath=[];
 if(wasTraveling)setTravelTarget(null);
}
function unsafeTravelStep(cell){
 return state.walls.some(wall=>same(wall,cell))||same(state.lock,cell)||
  state.dangerCells?.some(danger=>same(danger,cell))||
  state.returning.some(wave=>wave.owner==='enemy'&&wave.cells.some(danger=>same(danger,cell)))||
  state.enemies.some(enemy=>same(pos(enemy),cell)||same(enemy.intent.target,cell)&&enemy.intent.action==='move')||
  state.terrain.some(tile=>same(pos(tile),cell)&&
   (['fragile','mirror','rubble'].includes(tile.kind)||(tile.kind==='trap'&&tile.armed)));
}
function travelNeedsCaution(){
 return state.pursuing||state.returning.length||state.enemies.some(e=>!e.dormant)||state.fireCells?.length;
}
async function travelTo(target,id,previous){
 let replan=false;
 try{
  do{
   const response=await api('path',{target,version:state.version});
   if(id!==travelId)return;
   if(response.version!==state.version)throw Error('局面已变化，请重新选择目的地。');
   if(!response.path.length){
    toast(state.searchHints?.some(cell=>same(cell,target))?'已到刻痕旁 · 可以搜查。':
     same(pos(state.player),target)?'已到达目的地。':'已到达目标附近。');
    return;
   }
   travelPath=response.path;
   renderBoard();
   let movedOnPath=false;
   replan=false;
   while(travelPath.length&&id===travelId&&canAct()){
    const previousEnemies=new Set(state.enemies.map(e=>e.id));
    const hp=state.player.hp, step=travelPath[0];
    const [dx,dy]=dirs[step];
    const next=[state.player.x+dx,state.player.y+dy];
    if(unsafeTravelStep(next)){
     if(!movedOnPath)throw Error('前方没有可自动通过的地格。');
     replan=true;
     $('travel-steps').textContent='重新寻路…';
     break;
    }
    $('travel-steps').textContent=travelPath.length+' 步';
    travelPath=travelPath.slice(1);
    const move=send('move',step);
    travelMove=move;
    const moved=await move;
    if(travelMove===move)travelMove=null;
    if(id!==travelId)break;
    if(!moved){
     if(!same(pos(state.player),target))setPausedTravel(target);
     break;
    }
    const triggeredTrap=state.effects.some(f=>f.kind==='trap'&&f.cells.length);
    const interrupted=state.effects.some(f=>f.kind==='revive')||state.player.hp<hp||state.choices.length||state.talentChoice||state.result||
     state.movementLocked||triggeredTrap||
     state.enemies.some(e=>!e.dormant&&!previousEnemies.has(e.id))||state.pursuing||state.returning.length;
    if(interrupted){
     if(!same(pos(state.player),target)&&!state.result){
      setPausedTravel(target);
      if(!state.choices.length&&!state.talentChoice)
       toast(triggeredTrap?'机关已触发 · 自动行走已停步':'已停步 · 请观察敌人和危险格');
     }
     break;
    }
    if(same(pos(state.player),target)&&unopenedSupplyAt(target)){
     await send('open_supply');
     break;
    }
    // A contested move or forced displacement invalidates the cached directions.
    if(!same(pos(state.player),next)){
     setPausedTravel(target);
     toast('站位发生变化 · 可继续前往以重新规划');
     break;
    }
    const atLockedDoor=same(target,state.lock)&&Math.abs(state.player.x-target[0])+Math.abs(state.player.y-target[1])===1;
    const atClue=state.searchHints?.some(cell=>same(cell,target));
    const atStatue=state.statueLandmarks?.some(statue=>same(pos(statue),target))&&Math.abs(state.player.x-target[0])+Math.abs(state.player.y-target[1])===1;
    if(!travelPath.length&&!same(pos(state.player),target)&&!atLockedDoor&&!atClue&&!atStatue){
     setPausedTravel(target);
     toast('已走一步 · 可继续前往原目标');
    }else if(!travelPath.length&&atClue)toast('已到刻痕旁 · 可以搜查。');
    else if(!travelPath.length&&atStatue)toast('已到石像旁 · 点击石像查看武器。');
    movedOnPath=true;
    if(travelPath.length)await new Promise(resolve=>setTimeout(resolve,65));
   }
  }while(replan&&id===travelId&&canAct());
 }catch(e){
  if(id===travelId){
   if(replan||previous)setPausedTravel(replan?target:previous);
   toast(replan?'前方有障碍，找不到已知的安全绕路。':e.message,true);
  }
 }finally{if(id===travelId)cancelTravel()}
}
function requestTravel(target){
 const previous=pausedTravel;
 setPausedTravel(null);
 travelPath=[];
 const id=++travelId;
 setTravelTarget(target,'寻路中…');
 return travelTo(target,id,previous);
}
function setInspecting(active){
 if(inspecting===active)return;
 inspecting=active;
 renderControls();
 renderBoard();
}
function toggleInspection(){
 if(!state||busy)return;
 if(!inspecting){cancelTravel();aim=null;aimingItem=null;refreshPreview()}
 setInspecting(!inspecting);
}
function examineCell(target){
 const enemy=state.enemies.find(e=>same(pos(e),target));
 setInspecting(false);
 if(enemy){inspectEnemy(enemy);return}
 const terrain=state.terrain.find(t=>same(pos(t),target));
 const door=state.doors.some(p=>same(p,target));
 const title=state.walls.some(p=>same(p,target))?'石墙':
  same(target,state.lock)?(lockStyle()?.name??'库房锁门'):door?'石门':
  same(target,state.exit)?(state.floorKind==='relic'?'终点祭坛':'下层阶梯'):
  terrain?terrainName(terrain):'地面';
 const lines=[];
 const smoke=state.smokeCells?.find(c=>same(pos(c),target));
 if(smoke)lines.push('烟雾还会持续 '+smoke.turns+' 拍，遮蔽敌人的视线。');
 if(state.fireCells?.some(cell=>same(cell,target)))lines.push('地火会在下一拍造成 1 点伤害，并可能蔓延到相邻高草。凝霜雾弹可以扑灭火焰。');
 if(title==='石墙')lines.push((state.secretClues??state.searchHints??[]).some(p=>same(p,target))
  ?'墙上有一道金色刻痕。站在旁边搜查可揭开暗门。':'阻挡移动、视线和能量波。');
 if(door)lines.push(state.openDoors.some(p=>same(p,target))
  ?'门现在开着。':'踏入即可打开；关着时挡住视线和能量波。');
 if(same(target,state.lock)){
  if(lockStyle())lines.push(lockStyle().detail);
  lines.push(state.keys?'有钥匙，站在门边点击即可开锁。':'需要钥匙才能打开。');
 }
 if(same(target,state.exit)&&state.exitLockReason)lines.push(state.exitLockReason+'后解锁。');
 if((state.mapped??[]).some(p=>same(p,target)))lines.push('来自卷轴测绘，尚未亲眼确认。');
 for(const feature of state.features.filter(f=>same(pos(f),target))){
  lines.push((['dry_spring','materials'].includes(feature.kind)?'':feature.used?'已使用：':'可拾取或使用：')+featureName(feature));
  if(feature.kind==='supply_choice'&&!feature.used){
   lines.push('点击箱子走过去并打开。已站在箱上时，可点脚下或「打开补给箱」。');
   for(const item of state.supplyOptions??[])lines.push(item.name+' · '+item.description);
  }
 }
 if((state.dangerCells??[]).some(p=>same(p,target))||state.returning.some(w=>w.owner==='enemy'&&w.cells.some(p=>same(p,target))))
  lines.push('此格在下一拍攻击范围内。');
 $('cell-title').textContent=title;
 $('cell-details').innerHTML=lines.map(line=>`<li>${esc(line)}</li>`).join('');
 $('cell-details').hidden=!lines.length;
 openPanel('cell-dialog');
}
async function mapClick(target, landmark=false){
 if(!state)return;
 if(inspecting&&!landmark){examineCell(target);return}
 if(aimingItem&&!landmark){
  if(!throwTargets().some(p=>same(p,target))){toast('请选择四格内高亮的空地。',true);return}
  lureSelection=target;
  lureHover=null;
  renderControls();
  renderBoard();
  return;
 }
 const [x,y]=target;
 const rerouting=!!(travelTarget||travelMove);
 const pendingMove=travelMove;
 const clickFloor=state.depth;
 const stoodAtExit=same(pos(state.player),state.exit);
 if(fillingEnergy)cancelTravel();
 const selection=++travelId;
 travelPath=[];
 if(rerouting)setTravelTarget(target,'改道中…');
 if(pendingMove)await pendingMove;
 if(selection!==travelId)return;
 if(!state||busy||state.depth!==clickFloor){cancelTravel();return}
 const enemy=state.enemies.find(e=>e.x===x&&e.y===y);
 if(enemy&&!landmark){cancelTravel();inspectEnemy(enemy);return}
 if(!canAct()){cancelTravel();return}
 const tile=state.terrain.find(t=>t.x===x&&t.y===y);
 if(!aim&&tile&&['mirror','rubble'].includes(tile.kind)){cancelTravel();toast(terrainName(tile)+(tile.rotating?' · 用波击中可旋转':''));return}
 if(!landmark&&stoodAtExit&&!state.exitUnlocked&&same(target,state.exit)){
  cancelTravel();toast(state.exitLockReason??'阶梯仍被封锁。',true);return;
 }
 if(!landmark&&stoodAtExit&&state.exitUnlocked&&same(target,state.exit)&&same(pos(state.player),state.exit)){cancelTravel();send('exit');return}
 if(!aim&&unopenedSupplyAt(target)){
  if(same(target,pos(state.player))){
   cancelTravel();
   await send('open_supply');
  }else requestTravel(target);
  return;
 }
 if(!aim&&!landmark&&same(target,pos(state.player))){
  if(state.groundItems?.length){
   showGroundItems();
   return;
  }
 }
 const dx=x-state.player.x,dy=y-state.player.y;let d;
 if(!landmark&&!aim&&same(target,state.lock)&&Math.abs(dx)+Math.abs(dy)===1){cancelTravel();send('unlock');return}
 if(aim){
  const matching=Object.keys(dirs).filter(heading=>ray(heading).some(cell=>same(cell,target)));
  if(matching.length===1)d=matching[0];
  else if(matching.length>1)return toast('多条波经过这里，请在预览中选择发射方向。');
  else if(dx===0&&dy!==0)d=dy<0?'up':'down';
  else if(dy===0&&dx!==0)d=dx<0?'left':'right';
  else return toast('请选择一条已标出的射线，或使用方向按钮。',true);
 }else{
  if(landmark||rerouting||state.secretClues?.some(cell=>same(cell,target))||Math.abs(dx)+Math.abs(dy)!==1){requestTravel(target);return}
  d=dx===1?'right':dx===-1?'left':dy===1?'down':'up';
 }
 direction(d);
}
$('tactics').addEventListener('click',event=>{
 const button=event.target.closest('button');
 if(!button||!canAct())return;
 cancelTravel();
 if(button.hasAttribute('data-ground')){showGroundItems();return}
 send(button.hasAttribute('data-open-supply')?'open_supply':'unlock');
});
// A step redraws the SVG and moves the camera. Keep the cell selected on press
// even if the original SVG node has been replaced by the time the tap ends.
for(const map of [$('board'),$('minimap')]){
 let press=null;
 const targetAt=event=>event.target.closest('[data-cell]')?.dataset.cell.split(',').map(Number);
 map.addEventListener('pointerdown',event=>{
  if(!event.isPrimary||event.button!==0)return;
  const target=targetAt(event);
  press=target?{id:event.pointerId,target,x:event.clientX,y:event.clientY}:null;
  if(press)map.setPointerCapture(event.pointerId);
 });
 const clearPress=event=>{if(press?.id===event.pointerId)press=null};
 map.addEventListener('pointercancel',clearPress);
 map.addEventListener('lostpointercapture',clearPress);
 map.addEventListener('pointerup',event=>{
  if(press?.id!==event.pointerId)return;
  const {target,x,y}=press;
  press=null;
  if(Math.hypot(event.clientX-x,event.clientY-y)<12)mapClick(target);
 });
 map.addEventListener('click',event=>{
  if(event.detail!==0)return;
  const target=targetAt(event);
  if(target)mapClick(target);
 });
}
for(const list of [$('landmarks'),$('journal-landmark-list')]){
 list.addEventListener('click',event=>{
  const button=event.target.closest('[data-landmark]');
  if(!button||button.disabled||!state||state.result||state.talentChoice||state.choices.length)return;
  if(aim||aimingItem){aim=null;aimingItem=null;refreshPreview();renderControls()}
  if(inspecting)setInspecting(false);
  const target=button.dataset.landmark.split(',').map(Number);
  $('journal-dialog').close();
  if(same(target,pos(state.player))&&!unopenedSupplyAt(target)&&state.groundItems?.length){
   showGroundItems();
   return;
  }
  mapClick(target,true);
 });
}
$('zoom-out').addEventListener('click',()=>changeZoom(zoomIndex-1));
$('zoom-reset').addEventListener('click',()=>changeZoom(1));
$('zoom-in').addEventListener('click',()=>changeZoom(zoomIndex+1));
$('view-toggle').addEventListener('click',()=>{
 perspectiveBoard=!perspectiveBoard;
 try{localStorage.setItem('bobozan-view',perspectiveBoard?'3d':'2d')}catch{}
 renderBoard();
});
$('board').addEventListener('wheel',event=>{
 if(!state||event.ctrlKey||Math.abs(event.deltaY)<5)return;
 event.preventDefault();
 changeZoom(zoomIndex-Math.sign(event.deltaY));
},{passive:false});
$('board').addEventListener('pointermove',event=>{
 if(!aimingItem||event.pointerType==='touch')return;
 const key=event.target.closest('[data-cell]')?.dataset.cell;
 const previews=state.smokeItems?.includes(aimingItem)?state.smokePreviews:state.lurePreviews;
 const next=previews?.[key]?key:null;
 if(next===lureHover)return;
 lureHover=next;
 renderBoard();
});
$('board').addEventListener('pointerleave',()=>{
 if(!lureHover)return;
 lureHover=null;
 if(aimingItem)renderBoard();
});
$('throw-lure').addEventListener('click',()=>{
 if(!aimingItem||!lureSelection||!canAct())return;
 if(aimingItem==='plant')send('plant',lureSelection,plantingSeed);
 else send('item',lureSelection,aimingItem);
});
$('inspect-cell').addEventListener('click',toggleInspection);
$('fill-energy').addEventListener('click',fillEnergy);
$('resume-travel').addEventListener('click',()=>{if(pausedTravel&&!$('resume-travel').disabled)requestTravel(pausedTravel)});
$('stop-travel').addEventListener('click',()=>{forgetTravel();toast('已停止自动行走。')});

document.querySelectorAll('[data-action]').forEach(b=>b.addEventListener('click',()=>chooseAction(b.dataset.action)));
document.querySelectorAll('[data-direction]').forEach(b=>b.addEventListener('click',()=>direction(b.dataset.direction)));
$('cancel-aim').addEventListener('click',()=>{aim=null;aimingItem=null;refreshPreview();renderBoard();renderControls();toast('已取消瞄准。')});
$('exit').addEventListener('click',()=>send('exit'));
function openPanel(id){
 cancelTravel();closeDialogs();$(id).showModal();
}
$('open-pack').addEventListener('click',()=>{
 if(!state)return;
 selectedBagItem=null;
 renderBag();
 $('bag-feedback').textContent='';
 openPanel('pack-dialog');
});
$('talent-dialog').addEventListener('cancel',event=>event.preventDefault());
$('talent-options').addEventListener('change',()=>{
 const limit=state.talentChoice.limit;
 const selected=document.querySelectorAll('#talent-options input:checked');
 document.querySelectorAll('#talent-options input').forEach(input=>{
  input.disabled=!input.checked&&selected.length>=limit;
 });
 renderControls();
});
async function submitTalents(keys){
 const ok=await send('choose_talents',null,keys);
 if(!ok)$('talent-feedback').textContent=$('message').textContent;
}
$('confirm-talents').addEventListener('click',()=>submitTalents(
 [...document.querySelectorAll('#talent-options input:checked')].map(input=>input.value)));
$('skip-talents').addEventListener('click',()=>submitTalents([]));
$('drink-dew').addEventListener('click',async()=>{
 if(!canAct())return;
 await send('drink_dew');
 $('bag-feedback').textContent=$('message').textContent;
});
$('quick-item-settings').addEventListener('change',event=>{
 const slot=QUICK_ITEMS.find(slot=>slot.key===event.target.dataset.quickBind);
 if(!slot)return;
 slot.id=event.target.value;
 try{localStorage.setItem(slot.storage,slot.id)}catch{}
 renderQuickItems();
 renderControls();
});
$('quick-items').addEventListener('click',event=>{
 const key=event.target.closest('[data-quick-use]')?.dataset.quickUse;
 if(key)useQuickItem(key);
});
$('pack-dialog').addEventListener('click',async event=>{
 const tab=event.target.closest('[data-pack-tab]');
 if(tab){
  document.querySelectorAll('[data-pack-tab]').forEach(b=>b.setAttribute('aria-pressed',String(b===tab)));
  document.querySelectorAll('[data-pack-panel]').forEach(p=>p.hidden=p.dataset.packPanel!==tab.dataset.packTab);
  return;
 }
 const item=event.target.closest('#bag-slots [data-item]');
 if(item){
  selectedBagItem=item.dataset.item;
  document.querySelectorAll('#bag-slots [data-item]').forEach(slot=>
   slot.setAttribute('aria-pressed',String(slot.dataset.item===selectedBagItem)));
  renderBagItem();
  return;
 }
 const recipe=event.target.closest('[data-recipe]');
 if(recipe){
  if(!recipe.disabled&&canAct()){
   await send('craft',null,recipe.dataset.recipe);
   $('bag-feedback').textContent=$('message').textContent;
  }
  return;
 }
 if(event.target.id==='bag-plant-item'&&canAct()&&state.inventory.some(item=>item.id===selectedBagItem&&item.plantable)){
  plantingSeed=selectedBagItem;
  useItem('plant');
  return;
 }
 const action=event.target.id==='bag-use-item'?'item':event.target.id==='bag-drop-item'?'drop':null;
 if(action&&canAct()&&state.inventory.some(entry=>entry.id===selectedBagItem)){
  if(action==='item')await useItem(selectedBagItem);
  else await send(action,null,selectedBagItem);
  $('bag-feedback').textContent=$('message').textContent;
  return;
 }
 const button=event.target.closest('[data-growth]');
 if(!button||button.disabled)return;
 const ok=await send(button.dataset.growth,null,button.dataset.key||null);
 $('growth-status').textContent=ok?state.log[0]:$('message').textContent;
});
$('ground-bag').addEventListener('click',()=>$('open-pack').click());
$('ground-pick-all').addEventListener('click',()=>{if(canAct())send('pickup',null,{all:true})});
$('ground-items').addEventListener('click',event=>{
 const button=event.target.closest('[data-pickup]');
 if(button&&!button.disabled&&canAct())send('pickup',null,{feature:button.dataset.pickup,item:button.dataset.groundItem});
});
$('condition-strip').addEventListener('click',event=>{
 const key=event.target.closest('[data-condition]')?.dataset.condition;
 const condition=activeConditions().find(([id])=>id===key);
 if(!condition)return;
 $('condition-title').textContent=condition[2];
 $('condition-description').textContent=condition[3];
 openPanel('condition-dialog');
});
$('run-history').addEventListener('click',event=>{
 const button=event.target.closest('[data-retry-record]');
 if(!button||!state||busy)return;
 const record=state.history[Number(button.dataset.retryRecord)];
 if(!record)return;
 if(!state.result&&state.turn>0&&!window.confirm('重试这条记录会替换当前冒险进度。继续吗？'))return;
 reset(record.seed,record.heroClass);
});
$('open-journal').addEventListener('click',()=>openPanel('journal-dialog'));
$('toggle-map').addEventListener('click',()=>{
 const expanded=$('map-rail').classList.toggle('expanded');
 $('toggle-map').setAttribute('aria-expanded',String(expanded));
});
$('help').addEventListener('click',()=>openPanel('help-dialog'));
document.querySelectorAll('.close-dialog').forEach(b=>b.addEventListener('click',()=>b.closest('dialog').close()));
$('reward-dialog').addEventListener('cancel',e=>e.preventDefault());
$('skip-reward').addEventListener('click',()=>send('skip_reward'));
$('rewards').addEventListener('click',e=>{const b=e.target.closest('[data-choice]');if(b)send('choose',null,b.dataset.choice)});
let startingFirstRun=false;
function chooseClass(firstRun=false){
 if(!state)return;
 startingFirstRun=firstRun;
 $('restart-dialog').querySelector('.close-dialog').hidden=firstRun;
 $('class-note').textContent=firstRun?'职业决定本次冒险的波形。':'开始后会替换当前冒险进度。';
 $('class-options').innerHTML='<legend>初始职业</legend>'+state.classes.map(c=>`<label class="class-option">
 <input type="radio" name="hero-class" value="${c.id}" ${(state.heroClass||'straight')===c.id?'checked':''}>
 <span class="class-avatar" aria-hidden="true">${art.portrait(c.color)}</span>
 <span><b>${esc(c.name)}</b><small>${esc(c.description)}</small></span></label>`).join('');
 openPanel('restart-dialog');
}
$('restart').addEventListener('click',()=>chooseClass());
$('restart-dialog').addEventListener('cancel',event=>{if(startingFirstRun)event.preventDefault()});
$('confirm-restart').addEventListener('click',()=>{
 const selected=document.querySelector('[name="hero-class"]:checked');
 if(selected)reset(startingFirstRun?state.seed:undefined,selected.value);
});
$('retry').addEventListener('click',()=>reset(state.seed,state.heroClass));
$('new-seed').addEventListener('click',()=>chooseClass());
document.addEventListener('keydown',e=>{if(e.repeat||e.ctrlKey||e.metaKey||e.altKey||e.isComposing||document.querySelector('dialog[open]'))return;const key=e.key.toLowerCase();if(key==='escape'){setInspecting(false);forgetTravel()}const d={arrowup:'up',w:'up',arrowright:'right',d:'right',arrowdown:'down',s:'down',arrowleft:'left',a:'left'}[key];if(d){e.preventDefault();direction(d)}else if(key==='i'){e.preventDefault();toggleInspection()}else if(QUICK_ITEMS.some(slot=>slot.key===key)){e.preventDefault();useQuickItem(key)}else if(key==='x'){e.preventDefault();chooseAction('search')}else if(['1','2','3','4','5'].includes(key)){e.preventDefault();chooseAction({'1':'charge','2':'wave','3':'guard','4':'heavy','5':'reflect'}[key])}else if(key==='escape'){$('cancel-aim').click()}else if(key==='?'){$('help').click()}});
matchMedia('(max-width: 680px)').addEventListener('change',()=>renderBoard());
api('state').then(s=>{if(!s.floorVersion||!s.depth||!s.mechanicsVersion||!s.lastFloor||s.growthVersion!==2)throw Error('服务仍为旧版，请重启 Python 服务。');state=s;busy=false;render();$('saved').textContent='● 进度已保存';if(!state.result&&!state.choices.length&&!state.talentChoice&&state.turn===0&&!state.heroClass){chooseClass(true);return}if(!state.result&&!state.choices.length&&!state.talentChoice&&state.turn===0){try{if(!localStorage.getItem('bobozan-floor-guide-v1')){$('help-dialog').showModal();localStorage.setItem('bobozan-floor-guide-v1','seen')}}catch{}}}).catch(e=>{toast(window.bobozanLocalApi||e.message==='服务仍为旧版，请重启 Python 服务。'?e.message:'无法连接地牢。请运行 python3 server.py 后刷新页面。',true);$('saved').textContent='连接失败';$('restart').disabled=true;document.querySelectorAll('[data-action],[data-direction],#exit').forEach(b=>b.disabled=true)});
