'use strict';
const $ = id => document.getElementById(id);
document.querySelectorAll('[data-ui-icon]').forEach(icon=>{
 const name=icon.dataset.uiIcon;
 icon.innerHTML=icon.classList.contains('action-glyph')?art.buttonIcon(name):art.uiIcon(name);
});
const dirs = {up:[0,-1],right:[1,0],down:[0,1],left:[-1,0]};
const moveDirs={...dirs,'up-left':[-1,-1],'up-right':[1,-1],'down-left':[-1,1],'down-right':[1,1]};
const arrows = {up:'↑',right:'→',down:'↓',left:'←'};
let state=null, busy=true, aim=null, displayedResult=null, fxTimer;
let aimDetails=null, inspecting=false, aimingItem=null, lureHover=null, lureSelection=null, plantingSeed=null;
const shotHighlight={hover:null,focus:null,touch:null};
let shotPress=null, suppressShotClick=false;
let tideHover=null;
let mapSelection=null;
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
function canAct(){return state&&!busy&&!state.result&&!state.choices.length&&!state.talentChoice}
function canForecastDefense(){
 const cell=pos(state.player);
 return state.poisoned||state.dangerCells?.some(target=>same(cell,target))||
  state.returning.some(wave=>wave.owner==='enemy'&&wave.cells.some(target=>same(cell,target)));
}
function closeDialogs(){document.querySelectorAll('dialog[open]').forEach(d=>d.close())}
function renderControls(){
 document.querySelectorAll('[data-action]').forEach(b=>{const a=b.dataset.action;b.disabled=!canAct()||(a==='charge'&&state.player.energy>=state.energyCap)||(['wave','heavy','reflect'].includes(a)&&state.player.energy<(a==='heavy'?state.waveStats.heavyCost:a==='wave'?(state.waveStats.waveCost??1):1))||(a==='guard'&&state?.mode==='armor'&&state.player.energy<1);b.classList.toggle('selected',aim===a)});
 document.querySelectorAll('[data-quick-use]').forEach(button=>{
  button.disabled=!canAct()||!state.inventory.some(item=>item.id===QUICK_ITEMS.find(slot=>slot.key===button.dataset.quickUse).id&&!item.passive);
 });
 const ability=state?.classAbility;
 const dodge=$('class-ability-button');
 $('class-ability-slot').hidden=!ability;
 dodge.hidden=!ability?.active;
 dodge.disabled=!canAct()||!Object.keys(state?.dodgeTargets??{}).length;
 dodge.title=ability?.description??'';
 dodge.setAttribute('aria-pressed',String(aim==='dodge'));
 $('class-ability-active-label').textContent=ability?.cooldown?`闪避 ${ability.cooldown} 拍`:'闪避 · R';
 $('class-ability-passive').hidden=!ability||ability.active;
 $('class-ability-passive').title=ability?.description??'';
 $('class-ability-passive-label').textContent=ability?.name??'';
 const reflect=document.querySelector('[data-action="reflect"]');
 reflect.hidden=!state?.canReflect;
 reflect.disabled ||= !state?.canReflect;
 $('exit').hidden=!state||!same(pos(state.player),state.exit);
 $('exit').disabled=!canAct()||!state.exitUnlocked||!same(pos(state.player),state.exit);
 $('ascend').hidden=!state||!same(pos(state.player),state.upStairs);
 $('ascend').disabled=!canAct()||$('ascend').hidden;
 if(state){
  $('exit').textContent=state.floorKind==='relic'?'触碰祭坛 ↗':'下楼 ↗';
  $('skip-talents').disabled=busy;
  $('confirm-talents').disabled=busy||!state.talentChoice||
   document.querySelectorAll('#talent-options input:checked').length!==state.talentChoice.limit;
  document.querySelectorAll('[data-growth]').forEach(button=>{
   button.disabled=busy;
  });
  const growth=state.growth;
  $('confirm-growth').disabled=!canAct()||!growth.safe||!!growth.forge.blocked;
  document.querySelectorAll('[data-recipe]').forEach(button=>{
   button.disabled=!canAct()||button.dataset.available!=='true';
  });
  document.querySelectorAll('#ground-items [data-pickup]').forEach(b=>b.disabled=!canAct()||!state.packableItems.includes(b.dataset.groundItem));
  document.querySelectorAll('[data-ground-rune]').forEach(b=>b.disabled=!canAct()||b.dataset.blocked==='true');
 $('ground-pick-all').disabled=!canAct()||!state.groundItems?.some(f=>f.items.some(item=>state.packableItems.includes(item.id)));
  document.querySelectorAll('#tactics button, #loadout button, #bag-item-detail button').forEach(b=>
   b.disabled=!canAct()||b.getAttribute('aria-pressed')==='true'||(b.hasAttribute('data-launcher')&&!growth.safe));
  const anchorButton=$('tactics').querySelector('[data-anchor-chain]');
  if(anchorButton)anchorButton.disabled=!canAct()||!state.anchorChain.charges||!Object.keys(state.anchorChain.targets).length;
  const storedChargeButton=$('tactics').querySelector('[data-stored-charge]');
  if(storedChargeButton){
   const full=state.player.energy>=state.energyCap;
   storedChargeButton.disabled=!canAct()||!state.storedCharge||full;
   storedChargeButton.title=!state.storedCharge?'下到新楼层补充充能':full?'能量已满，保留充能':'消耗一拍，补满能量';
  }
 }
 $('restart').disabled=busy||!state;
 $('toggle-map').disabled=busy||!state;
 $('map-route-go').disabled=!canAct()||!(mapSelection?.path?.length||mapSelection?.interaction)
  ||mapSelection.version!==state.version;
 $('cancel-aim').hidden=!aim&&!aimingItem;
 $('throw-lure').hidden=!aimingItem||!lureSelection;
 $('throw-lure').disabled=!canAct();
 const anchorTarget=aimingItem==='anchor_chain'&&state.anchorChain.targets[lureSelection?.join(',')];
 $('throw-lure').textContent=aimingItem==='plant'?'播种 · 1 拍':aimingItem==='anchor_chain'?(anchorTarget?.pullEnemy?'拉近敌人 · 1 拍':'拉向空地 · 1 拍'):'投掷 · 1 拍';
 $('drink-dew').disabled=!canAct()||!state.dew||state.player.hp>=(state.maxHp??6);
 $('resume-travel').disabled=!canAct()||!!aim||!!aimingItem||!!state?.movementLocked;
 $('resume-travel').textContent=state&&travelNeedsCaution()?'继续一步':'继续前往';
 $('inspect-cell').disabled=!state||busy;
 $('inspect-cell').setAttribute('aria-pressed',String(inspecting));
 $('map-toast').textContent=inspecting?'点击地格查看 · 不消耗行动':aimingItem==='anchor_chain'?(lureSelection?'确认拉动 · 方框为落点':'选择高亮的敌人或空地'):aimingItem==='plant'?'选择播种位置 · 四格内空地':aimingItem?(lureSelection?(aimingItem==='frost_smoke'?'蓝圈标记可能受冻的敌人 · 范围内浅水结冰':'确认投掷，或点选其他落点'):'选择四格内的高亮地格 · 障碍近侧落地'):aim?'左键点射线或敌人发射 · 右键查看':'';
 $('map-toast').classList.toggle('visible',inspecting||!!aim||!!aimingItem);
 $('skip-reward').disabled=busy;
 $('organize-for-supply').disabled=busy;
 $('rewards').disabled=busy;
 $('confirm-reward').disabled=busy||!$('rewards').querySelector('input:checked');
 $('return-to-supply').hidden=!state||!unopenedSupplyAt(pos(state.player));
 $('return-to-supply').disabled=!canAct();
 document.querySelectorAll('#retry,#new-seed,#confirm-restart').forEach(b=>b.disabled=busy);
}
function ray(direction){
 if(aim==='dodge')return state.dodgeTargets[direction]?[state.dodgeTargets[direction]]:[];
 if(aim==='reflect')return aimDetails?.[direction]?.cells??[];
 return aimDetails?.[direction]?.cells??state.aimPaths?.[direction]??[];
}
function radialWave(action){
 return state?.growth.closeFan&&['wave','heavy'].includes(action);
}
const LIGHT_INFO={
 light_wisp:{name:'微光',effect:'波与重波伤害 +1',glyph:'◈',color:'#9ce9ef'},
 light_soul:{name:'圣光',effect:'每次攒额外获得 1 能量',glyph:'✦',color:'#f9df91'},
 light_radiant:{name:'辉光',glyph:'☀',color:'#ffa7bc'}
};
const FEATURE_NAMES={chest:'遗物宝箱',materials:'空补给箱',supply_choice:'战术补给箱',shrine:'疗愈泉水',dry_spring:'干涸泉水',key:'钥匙',kit:'药剂',cache:'战术补给',
 lure_cache:'诱饵',smoke:'烟雾弹',wonder:'镜间奇遇',dew:'露珠',grass_seed:'响草种子',sun_seed:'阳草种子',chart:'测绘卷轴',recall:'回程卷轴',ankh:'护命符',terror:'惊退卷轴',
 echo_smoke:'响雾弹',stolen_energy:'被偷走的能量',rune:'刻印',forge_core:'锻造核心'};
function emptyChest(feature){
 return feature.kind==='materials'||(feature.used&&(
  ['chest','cache','supply_choice'].includes(feature.kind)
  // A partly looted supply box can be saved as a lure cache with remaining items.
  ||(feature.kind==='lure_cache'&&feature.remaining_items?.length)
 ));
}
function lightEffect(kind){
 return kind==='light_radiant'?`每实际走满 ${state.lightStepGoal} 步回复 ${state.lightHealAmount} 生命`:LIGHT_INFO[kind].effect;
}
function featureName(f){
 const light=LIGHT_INFO[f.kind];
 return light?`${light.name} · +${state.lightRecovery[f.kind]} 理智`:emptyChest(f)?'空箱子':f.kind==='shrine'&&f.used?'已耗尽的泉水':f.itemName||FEATURE_NAMES[f.kind];
}
function unopenedSupplyAt(cell){
 return state.features.some(f=>f.kind==='supply_choice'&&!f.used&&same(pos(f),cell));
}
function hasGroundItems(){
 return !!(state.groundItems?.length||state.groundRunes?.length);
}
function groundLootAt(cell){
 return state.features.some(f=>!f.used&&f.inspectItems?.length&&same(pos(f),cell));
}
function featureContents(feature){
 return feature.inspectItems?.length?feature.inspectItems.map(item=>item.name):[featureName(feature)];
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
 alarm_store:{name:'警戒库房',detail:'门上刻有警铃。入口的警报会通知整层敌人。',glyph:'!',color:'#eea27f'},
 dart_vault:{name:'刺针库房',detail:'一排刺针挡住通往库房奖励的路。可站在近侧用波或诱饵先触发一格，再从那格过。',glyph:'×',color:'#f0a483'}
};
const RUNE_DETAILS={shatter:'破甲（无视普通防御）',echo:'回音（下拍沿原路返回）',
 frost:'凝滞（受伤后限制移动一拍）'};
function lockStyle(){return LOCK_STYLES[state.lockStyle]}
function runeJournalWaypoint(rune){
 if(rune.depth===state.depth)return {cell:rune.cell,label:'本层 · 前往刻印'};
 const up=rune.depth<state.depth;
 const stair=up?'上楼阶梯':'下楼阶梯';
 const cell=up?state.upStairs:state.exit;
 if(!cell)return {label:`尚未发现${stair}`};
 if(!up&&!state.exitUnlocked)return {label:state.exitLockReason??'下楼阶梯尚未解锁'};
 return {cell, label:same(cell,pos(state.player))?`已到${stair} · 可手动换层`:`先去${stair}`};
}
function renderLandmarks(){
 const destinations=[];
 if(state.exit)destinations.push({cell:state.exit,name:state.floorKind==='relic'?'终点祭坛':'下层阶梯',
  hint:state.exitLockReason??'',icon:'↘'});
 if(state.entrance)destinations.push({cell:state.entrance,name:state.upStairs?'返回上一层':'本层入口',hint:'回程卷轴落点',icon:'↖'});
 for(const cell of state.openedShortcuts??[])destinations.push({cell,name:'隐蔽通路',hint:'已揭开的双向捷径',icon:'↔'});
 for(const room of state.roomStates){
  if(room.blocksExit&&room.anchor)destinations.push({cell:room.anchor,name:'阶梯守卫',hint:'清理战斗区后解锁',icon:'⚔'});
 }
 if(state.lock)destinations.push({cell:state.lock,name:lockStyle()?.name??'库房锁门',
  hint:[state.keys?'有钥匙':'需要钥匙',state.lockStyle==='dart_vault'?'库房奖励':''].filter(Boolean).join(' · '),icon:lockStyle()?.glyph??'◆'});
 for(const cell of state.secretClues??[])destinations.push({cell,name:'墙上的刻痕',hint:'靠近后按 X 搜查',icon:'⌕'});
 for(const statue of state.statueLandmarks??[]){
  const weapon=state.weapons.find(w=>w.id===statue.emitter)?.name;
  const loot=state.enemies.find(enemy=>same(pos(enemy),pos(statue)))?.lootHint;
  destinations.push({cell:pos(statue),name:'武器石像',hint:[weapon,RUNE_DETAILS[statue.inscription],loot].filter(Boolean).join(' · '),icon:'◇'});
 }
 const healthy=state.player.hp>=state.maxHp;
 for(const tile of state.terrain){
  if(tile.kind==='sun_plant')destinations.push({cell:pos(tile),name:'阳草',hint:healthy?'生命已满':'恢复 2 生命',icon:'✦'});
 }
 for(const features of featuresByCell().values()){
  const marked=features.filter(f=>!f.used&&!['dry_spring','materials','stolen_energy'].includes(f.kind));
  if(!marked.length)continue;
  const [f]=marked;
  const count=countFeatures(marked), stack=count>1;
  const tile=state.terrain.find(t=>same(pos(t),pos(f)));
  const rubble=tile?.kind==='rubble';
  const full=f.kind==='supply_choice'
   ?!state.supplyOptions.some(item=>item.equipment||state.packableItems.includes(item.id))
   :marked.every(feature=>state.fullBagLandmarks.includes(feature.id));
  const hint=rubble?'脆墙后':full?'背包已满':
   stack?marked.flatMap(featureContents).filter(Boolean).join(' / '):
   f.kind==='supply_choice'?(state.supplyOptions??[]).map(item=>item.name).join(' / '):
   f.kind==='shrine'&&healthy?'生命已满':f.kind==='dew'&&healthy&&state.dew>=state.dewCapacity?'露珠已满':'';
  destinations.push({cell:pos(f),name:stack?`${count} 项地面物品`:featureName(f),hint,blocked:rubble,
   icon:marked.some(feature=>feature.kind==='rune')?'◈':f.kind==='shrine'?'✦':'◇'});
 }
 $('landmark-count').textContent=destinations.length?'· '+destinations.length:'';
 const rows=destinations.map(({cell,name,hint,icon,blocked})=>
  `<button type="button" data-landmark="${cell.join(',')}" data-landmark-name="${esc(name)}" ${blocked?'disabled':''}
   aria-label="${blocked?'':'前往'}${esc(name)}${hint?'，'+esc(hint):''}"><span aria-hidden="true">${icon}</span>
  ${esc(name)}${hint?`<small>${esc(hint)}</small>`:''}</button>`).join('')||'<p class="muted">还没有发现路标。</p>';
 for(const list of [$('landmarks'),$('journal-landmark-list')])list.innerHTML=rows;
 const runes=state.runeJournal??[];
 $('journal-rune-count').textContent=runes.length?'· '+runes.length:'';
 $('journal-rune-list').innerHTML=runes.map((rune,index)=>{
  const name=esc(rune.name)+'刻印';
  const floor=`第 ${rune.depth} 层`;
  const waypoint=runeJournalWaypoint(rune);
  if(!waypoint.cell)return `<p class="journal-rune-location"><span>${name}</span><small>${floor} · ${esc(waypoint.label)}</small></p>`;
  return `<button type="button" data-rune-route="${index}">
   <span aria-hidden="true">◈</span> ${name}<small>${floor} · ${esc(waypoint.label)}</small></button>`;
 }).join('')||'<p class="muted">尚无已发现的未领取刻印。</p>';
}
function terrainName(tile){
 if(!tile)return '';
 if(tile.kind==='mirror')return (tile.rotating?'旋转镜面':'固定镜面')+' '+tile.slash;
 if(tile.kind==='high_grass')return '高草 · 遮挡视线，可踩倒或打碎';
 if(tile.kind==='grass')return '短草';
 if(tile.kind==='web')return '蛛网 · 波可切断，无法以飞雷神进出';
 if(tile.kind==='sun_plant')return '阳草 · 受伤时踩上最多回复 6 生命';
 if(tile.kind==='root_plant')return '缠根 · 敌人踩上后下一拍无法移动';
 if(tile.kind==='trap'){
  if(!tile.armed)return '已触发的陷阱';
  return {alarm:'警报陷阱 · 通知整层敌人',dart:'刺针陷阱 · 踩中受伤',grip:'夹足陷阱 · 下拍无法移动',fall:'坠落陷阱 · 跌向下一层并受伤'}[tile.mechanism];
 }
 if(tile.kind==='ice')return '薄冰 · 本拍限制移动';
 if(tile.kind==='water')return tile.ice_until?`冰封浅水 · ${Math.max(0,tile.ice_until-state.turn)} 拍后解冻 · 暂停导电`:'浅水 · 熄灭灼烧，相连水格可导电';
 if(tile.kind==='rubble')return '脆墙 · 需要破城震波拆除';
 if(tile.kind==='fragile')return tile.stage?'破洞 · 踏入会坠落并受伤':'脆弱地板 · 踩过后会留下破洞';
 return '地面';
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
  '下水道':['#384b53','#788382'], '监狱':['#414766','#787e9c'], '洞穴':['#51463e','#8b735e'],
  '矮人都市':['#4e503d','#8d835d'], '恶魔大厅':['#563641','#956171'], '终点':['#414b65','#7b86a3']
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
  : `-16 -16 ${w+32} ${h+32}`);
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
 const shortcuts=new Set((state.openedShortcuts??[]).map(c=>c.join(',')));
 const warnings=new Set(state.enemies.flatMap(e=>(e.intent.warning??[]).map(cell=>cell.join(','))));
 const lureCells=new Set(aimingItem?throwTargets().map(c=>c.join(',')):[]);
 const aimKey=lureHover??lureSelection?.join(',');
 const redirects=aimingItem&&aimingItem!=='plant'&&aimingItem!=='anchor_chain'?(state.throwRedirects??{}):{};
 const anchorPreview=aimingItem==='anchor_chain'?state.anchorChain?.targets[aimKey]:null;
 const anchorPath=new Set((anchorPreview?.path??[]).map(cell=>cell.join(',')));
 const redirected=redirects[aimKey];
 const previewKey=redirected?.join(',')??aimKey;
 const lurePreview=['lure','grass_seed','echo_smoke'].includes(aimingItem)&&state.lurePreviews?.[previewKey];
 const smokePreview=new Set((state.smokeItems?.includes(aimingItem)?state.smokePreviews?.[previewKey]??[]:[]).map(c=>c.join(',')));
 const smokeCells=new Set((state.smokeCells??[]).map(c=>pos(c).join(',')));
 const soundCells=new Set((lurePreview?.cells??[]).map(c=>c.join(',')));
 const listeners=new Set(lurePreview?.listeners??[]);
 const chilled=new Set(aimingItem==="frost_smoke"?state.frostPreviews?.[previewKey]??[]:[]);

 const chargedWater=new Set(state.enemies.flatMap(e=>(e.intent.water??[]).map(cell=>cell.join(','))));
 const fireCells=new Set((state.fireCells??[]).map(cell=>cell.join(',')));
 const danger=new Set([...(state.dangerCells??state.enemies.flatMap(e=>e.intent.cells)),...state.returning.filter(w=>w.owner==='enemy').flatMap(w=>w.cells)].map(cell=>cell.join(',')));
 const focusedShot=aimDetails?.[highlightedShotDirection()];
 const shownShots=aim?(focusedShot?[focusedShot]:Object.values(aimDetails??{})):[];
 const aimed=aim?(focusedShot?focusedShot.cells:Object.keys(aimDetails??dirs).flatMap(d=>ray(d))):[];
 const aimedCells=new Set(aimed.map(cell=>cell.join(',')));
 const conductionCells=new Set(shownShots.flatMap(result=>(result.conduction??[]).map(cell=>cell.join(','))));
 const knockbackCells=new Set(shownShots.flatMap(result=>(result.knockback??[]).map(cell=>cell.join(','))));
 const projection=perspectiveBoard?'matrix(1 .16 -.36 .66 0 0) ':'';
 let solids='';
 const floorFeatures=featuresByCell();
 let svg=`<defs><pattern id="board-fog" width="120" height="120" patternUnits="userSpaceOnUse" shape-rendering="crispEdges">
  <path d="M0 0h120v120H0z" fill="var(--dungeon-fog)"/>
  <path d="M12 27h8v3h-8zM74 62h9v3h-9zM42 92h5v4h-5zM103 14h3v3h-3z" fill="#2f3b4d" opacity=".42"/>
  <path d="M5 72h10v3H5zM80 101h7v2h-7zM48 41h6v2h-6z" fill="#10131c" opacity=".72"/>
 </pattern></defs><g transform="${projection}translate(${-ox*60},${-oy*60})">
  <rect data-fog-layer x="${ox*60}" y="${oy*60}" width="${w}" height="${h}" fill="url(#board-fog)" stroke="#4a4350" stroke-width="2" pointer-events="none"/>`;
 for(let y=oy;y<oy+height;y++)for(let x=ox;x<ox+width;x++){
  const key=x+','+y,visible=seen.has(key);
  if(!known.has(key))continue;
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
  const box=available.find(f=>f.kind==='supply_choice');
  const rune=available.find(f=>f.kind==='rune');
  const feature=box??rune??available[0]??features[0];
  const count=countFeatures(available);
  const supplies=count>1?`${count} 项地面物品 · ${available.flatMap(featureContents).filter(Boolean).join(' / ')}`:feature?(feature.used&&!emptyChest(feature)?'已使用的':'')+featureName(feature):'';
  const doorLabel=doorway?(openDoor?'打开的门':'关闭的门 · 踏入开启'):'';
  const onFire=fireCells.has(key);
  const routeLabel=same([x,y],state.upStairs)?'返回上一层的阶梯':same([x,y],state.entrance)?'本层入口':shortcuts.has(key)?'隐蔽通路':'';
  const groundLabel=[routeLabel,doorLabel,onFire?'地火 · 下一拍 1 伤':'',supplies].filter(Boolean).join('，')||(tile?terrainName(tile):`地面 ${x},${y}`);
  const label=same([x,y],state.lock)?((lockStyle()?.name??'库房')+'锁门，点击使用钥匙'):same([x,y],state.exit)?(hero?(state.floorKind==='relic'?'终点祭坛，点击完成试炼':(state.exitUnlocked?'阶梯，点击下楼':'阶梯已封锁')):'阶梯'):enemy?enemy.name+'，'+enemy.intent.label+'，右键查看信息':box?`${groundLabel}，${hero?'点击打开':'点击前往并打开'}`:hero?'你的位置，'+groundLabel:groundLabel;
  const risk=danger.has(key)?'，下一拍危险':warnings.has(key)?'，有敌方预告':'';
  svg+=`<g ${wall?'':`data-cell="${key}" role="button" tabindex="-1" aria-label="${esc(label+risk)}"`} opacity="${visible?1:.38}">`;
  if(wall){
   if(inspecting||secretClues.has(key)||redirects[key])svg+=`<rect data-cell="${key}" x="${x*60}" y="${y*60}" width="60" height="60" fill="transparent" role="button" aria-label="${redirects[key]?'石墙，投掷会落在近侧':secretClues.has(key)?'墙上的刻痕':'石墙'}"/>`;
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
   if(redirects[key])svg+=`<rect x="${x*60+5}" y="${y*60+5}" width="50" height="50" fill="none" stroke="#ebd890" stroke-dasharray="3 4" pointer-events="none"/>`;
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
   else if(tile.kind==='trap')svg+=`<rect x="${x*60+16}" y="${y*60+16}" width="28" height="28" rx="3" fill="#24222d" stroke="${tile.armed?'#dea674':'#727278'}" stroke-width="3"/><text x="${x*60+30}" y="${y*60+36}" text-anchor="middle" fill="${tile.armed?'#ffd298':'#98949c'}" font-size="16">${tile.armed?(({alarm:'!',dart:'×',grip:'⟐',fall:'↓'}[tile.mechanism]??'×')):'·'}</text>`;
   else if(tile.kind==='ice')svg+=`<rect x="${x*60+4}" y="${y*60+4}" width="52" height="52" fill="#81d8f26b" stroke="#c0f1ff"/>`;
   else if(tile.kind==='mirror')svg+=`<path d="M${x*60+12} ${y*60+(tile.slash==='/'?48:12)}L${x*60+48} ${y*60+(tile.slash==='/'?12:48)}" stroke="${tile.rotating?'#efc46a':'#92dce7'}" stroke-width="7"/><text x="${x*60+30}" y="${y*60+57}" text-anchor="middle" fill="#efc46a" font-size="11">${tile.rotating?'↻ 击中旋转':''}</text>`;
   else if(tile.kind==='rubble')svg+=`<rect x="${x*60+6}" y="${y*60+6}" width="48" height="48" fill="#725c51"/><path d="M${x*60+28} ${y*60+7}l-6 17 15 8-8 20" fill="none" stroke="#e0b78b" stroke-width="3"/>`;
   else if(tile.kind==='fragile')svg+=art.fragileFloor(x,y,tile.stage>0);
  }
  if(smokeCells.has(key)||smokePreview.has(key))svg+=`<path d="M${x*60+4} ${y*60+4}h52v52h-52z"
   fill="${aimingItem==='frost_smoke'&&smokePreview.has(key)?'#9cecff':'#b3c2de'}" fill-opacity="${smokeCells.has(key)?'.32':'.18'}" stroke="#b3c2de"
   stroke-dasharray="4 5" pointer-events="none"/>`;
  if(soundCells.has(key))svg+=`<rect x="${x*60+4}" y="${y*60+4}" width="52" height="52" fill="#dac88936" pointer-events="none"/>`;
  if(lureCells.has(key)||redirects[key])svg+=`<circle cx="${x*60+30}" cy="${y*60+30}" r="15" fill="${previewKey===key?'#ebd89090':'#d8d78430'}" stroke="#ebd890" stroke-dasharray="3 4" pointer-events="none"/>`;
  if(anchorPath.has(key))svg+=`<rect x="${x*60+8}" y="${y*60+8}" width="44" height="44" fill="#80dac326" pointer-events="none"/>`;
  if(anchorPreview&&same(anchorPreview.landing,[x,y]))svg+=`<rect data-anchor-landing x="${x*60+8}" y="${y*60+8}" width="44" height="44" fill="none" stroke="#9ef3d9" stroke-width="3" pointer-events="none"/>`;
  if(warnings.has(key))svg+=`<g pointer-events="none"><rect x="${x*60+7}" y="${y*60+7}" width="46" height="46" fill="#d8a45524" stroke="#edba71" stroke-width="2" stroke-dasharray="5 4"/><text x="${x*60+48}" y="${y*60+20}" text-anchor="middle" fill="#f4ce8e" font-size="14">⌛</text></g>`;
  if(danger.has(key))svg+=`<g pointer-events="none"><rect x="${x*60+4}" y="${y*60+4}" width="52" height="52" fill="#b45b4855" stroke="#e9a082"/><text x="${x*60+30}" y="${y*60+52}" text-anchor="middle" fill="#edaa8d" font-size="12">!</text></g>`;
  if(onFire)svg+=`<path data-ground-fire d="M${x*60+20} ${y*60+37}q-5-8 4-17 0 7 4 7 4-5 2-12 11 8 10 19-3 10-12 9-6 0-8-6z" fill="#ed804b" stroke="#ffd384" stroke-width="2" pointer-events="none"/>`;
  if(aimingItem==='frost_smoke'&&smokePreview.has(key)&&tile?.kind==='water')
   svg+=`<text data-freeze-water x="${x*60+30}" y="${y*60+39}" text-anchor="middle" fill="#d7f5ff" font-size="24">❄</text>`;
  if(chargedWater.has(key))svg+=`<path data-electric-water d="M${x*60+31} ${y*60+13}l-9 17h12l-6 15 15-20H32l6-12z" fill="#b2eaff" pointer-events="none"/>`;
  if(conductionCells.has(key))svg+=`<rect data-conduction-preview x="${x*60+7}" y="${y*60+7}" width="46" height="46" fill="#78eaf62c" stroke="#9befff" stroke-width="2" stroke-dasharray="4 3" pointer-events="none"/>`;
  if(aimedCells.has(key))svg+=`<rect data-aim-cell x="${x*60+5}" y="${y*60+5}" width="50" height="50"
   fill="${focusedShot?'#c7e7a84a':'#c7e7a822'}" stroke="#c7e7a8" stroke-dasharray="4 4" pointer-events="none"/>`;
  if(feature&&tile?.kind!=='rubble'){
   svg+=art.prop(emptyChest(feature)?'materials':feature.kind,x,y,feature.used,feature.item);
   if(count>1){
    const cx=x*60+47,cy=y*60+12;
    svg+=`<g data-loot-count="${count}" pointer-events="none"><circle cx="${cx}" cy="${cy}" r="9" fill="#25252e" stroke="#ddbd7c"/><text x="${cx}" y="${cy+4}" text-anchor="middle" fill="#ffe7af" font-size="11">${count}</text></g>`;
   }
  }
  if(shownShots.some(result=>same(result.landing,[x,y])))svg+=`<circle data-wave-landing cx="${x*60+30}" cy="${y*60+30}" r="14" fill="none" stroke="#8bd9e1" stroke-width="3" pointer-events="none"/>`;
  if(knockbackCells.has(key))svg+=`<path data-knockback-preview d="M${x*60+30} ${y*60+10}l20 20-20 20-20-20z"
   fill="#f0c48522" stroke="#f0c485" stroke-width="2" stroke-dasharray="5 3" pointer-events="none"/>`;
  if(same([x,y],state.exit))svg+=art.prop(state.floorKind==='relic'?'wonder':'stairs',x,y,!state.exitUnlocked);
  if(same([x,y],state.upStairs))svg+=art.prop('up_stairs',x,y);
  if(routeLabel)svg+=`<text x="${x*60+11}" y="${y*60+16}" fill="#a8dedb" font-size="15" font-weight="bold" text-anchor="middle" pointer-events="none">${shortcuts.has(key)?'↔':'↖'}</text>`;
  svg+='</g>';
 }
 svg+=solids;
 for(const result of shownShots){
  for(const segment of result.refraction??[])svg+=art.refraction(segment,true);
 }
 const intercepts=new Map(shownShots.flatMap(shot=>shot.interceptions??[]).map(hit=>[hit.cells.join('/'),hit.cells]));
 for(const [[tx,ty],[gx,gy]] of intercepts.values()){
  svg+=`<g data-interception-preview fill="none" stroke="#f2ce91" pointer-events="none">
   <path d="M${tx*60+30} ${ty*60+30}L${gx*60+30} ${gy*60+30}" stroke-width="3" stroke-dasharray="5 4"/>
   <path d="M-10-10H10V2L0 12-10 2Z" transform="translate(${gx*60+30} ${gy*60+30})" fill="#2c2732" stroke-width="2"/>
  </g>`;
 }
 if(travelPath.length){
  let [x,y]=pos(state.player);
  for(const step of travelPath){
   const [dx,dy]=moveDirs[step];x+=dx;y+=dy;
   svg+=`<circle cx="${x*60+30}" cy="${y*60+30}" r="4" fill="#e3c581" pointer-events="none"/>`;
  }
 }
 if(travelTarget||pausedTravel){
  const [x,y]=travelTarget||pausedTravel;
  svg+=`<circle cx="${x*60+30}" cy="${y*60+30}" r="12" fill="none" stroke="#e3c581" stroke-width="2" stroke-dasharray="${travelTarget?'none':'4 3'}" pointer-events="none"/>`;
 }
 for(const e of state.enemies){if(e.intent.action==='move'&&e.intent.target)svg+=`<path d="M${e.x*60+30} ${e.y*60+30}L${e.intent.target[0]*60+30} ${e.intent.target[1]*60+30}" stroke="${e.intent.mob_jump||e.kind==='slipsnake'?'#85e3d8':'#ddbd7c'}" stroke-width="3" stroke-dasharray="4 4" pointer-events="none"/>`;if(chilled.has(e.id))svg+=`<circle data-frost-preview="${e.id}" cx="${e.x*60+30}" cy="${e.y*60+30}" r="24" fill="none" stroke="#9cecff" stroke-width="3" stroke-dasharray="4 3" pointer-events="none"/>`;if(listeners.has(e.id))svg+=`<circle cx="${e.x*60+30}" cy="${e.y*60+30}" r="24" fill="none" stroke="#ffdf91" stroke-width="3" pointer-events="none"/>`;svg+=art.actor(e.x,e.y,e.kind,e.id,state.heroColor,e);if(e.intent.action==='guard'&&e.defense)svg+=`<circle cx="${e.x*60+30}" cy="${e.y*60+30}" r="25" stroke="#bdb0dc" fill="none" pointer-events="none"/>`}
 if(!state.falls.some(f=>f.id==='hero'))svg+=art.actor(state.player.x,state.player.y,'hero',0,state.heroColor);
 for(const wave of state.returning){
  const tide=wave.sidePaths;
  if(wave.orbCell){
   const [x,y]=wave.orbCell;
   svg+=`<circle data-return-orb cx="${x*60+30}" cy="${y*60+30}" r="9" fill="#c8b4ff" stroke="#ecdcff" stroke-width="2" pointer-events="none"/>`;
  }
  for(const [x,y] of (tide?.[tideHover]??wave.cells)){
   svg+=`<circle ${tide?'data-tide-return':''} cx="${x*60+30}" cy="${y*60+30}" r="21" fill="none" stroke="${tide?'#c8b4ff':wave.owner==='hero'?'#9edbd4':'#eb978a'}" stroke-dasharray="4 6" pointer-events="none"/>`;
  }
 }
 if(showEffects)for(const fall of state.falls)svg+=`<g class="falling" style="transform-origin:${fall.cell[0]*60+30}px ${fall.cell[1]*60+30}px">${art.actor(...fall.cell,fall.kind,fall.id==='hero'?0:fall.id,state.heroColor)}</g>`;
 if(showEffects){
  for(const fx of state.effects){
   if(!art.statusLabel(fx)||['revive','energy_gain','sanity_gain'].includes(fx.kind))svg+=art.effects(fx,state.heroColor);
  }
  svg+=art.statusEffects(state.effects,oy,ox,width,height);
 }
 $('board').innerHTML=svg+'</g>';
 let mini=`<rect width="${state.width*8}" height="${state.height*8}" fill="var(--dungeon-fog)" pointer-events="none"/>`;
 for(const [x,y] of charted){const key=x+','+y;mini+=`<rect ${walls.has(key)&&!inspecting?'':`data-cell="${key}"`} x="${x*8}" y="${y*8}" width="8" height="8" fill="${mappedKeys.has(key)?(walls.has(key)?'#282d3a':'#505e78'):walls.has(key)?'#41534c':seen.has(key)?'#98b48d':'#576f66'}"/>`}
 let hasPit=false;
 for(const tile of state.terrain){
  const pit=tile.kind==='fragile'&&tile.stage>0;
  hasPit||=pit;
  const fill=pit?'#030407':tile.ice_until?'#abdef0':({fragile:'#b58d6f',high_grass:'#88a662',grass:'#667854',root_plant:'#b6cc78',sun_plant:'#efd483'}[tile.kind]||(tile.kind==='trap'?(tile.armed?'#dfaa77':'#727278'):'#b7d3de'));
  mini+=`<rect data-cell="${tile.x},${tile.y}" x="${tile.x*8}" y="${tile.y*8}" width="8" height="8" fill="${fill}"${pit?' stroke="#99836e" stroke-width="1"':''}/>`;
 }
 $('map-pit-key').hidden=!hasPit;
 for(const features of floorFeatures.values()){
  const [f]=features;
  mini+=`<rect data-cell="${f.x},${f.y}" x="${f.x*8+1}" y="${f.y*8+1}" width="6" height="6" fill="${features.every(item=>item.used)?'#6a7772':LIGHT_INFO[f.kind]?.color??'#ddbd7c'}"/>`;
 }
 if(state.exit)mini+=`<rect data-cell="${state.exit.join(',')}" x="${state.exit[0]*8}" y="${state.exit[1]*8}" width="8" height="8" fill="#ddd6a4"/>`;
 for(const [x,y] of [state.entrance,...(state.openedShortcuts??[])].filter(Boolean)){
  mini+=`<rect data-cell="${x},${y}" x="${x*8+1}" y="${y*8+1}" width="6" height="6" fill="#87c7c5"/>`;
 }
 for(const e of state.enemies)mini+=`<rect data-cell="${e.x},${e.y}" x="${e.x*8+1}" y="${e.y*8+1}" width="6" height="6" fill="#e09a7b"/>`;
 mini+=`<rect x="${state.player.x*8}" y="${state.player.y*8}" width="8" height="8" fill="#edffc4" stroke="#172128" pointer-events="none"/>`;
 if(state.lock)mini+=`<rect data-cell="${state.lock.join(',')}" x="${state.lock[0]*8}" y="${state.lock[1]*8}" width="8" height="8" fill="#aa754c"/>`;
 for(const cell of state.secretClues??[])mini+=`<rect data-cell="${cell.join(',')}" x="${cell[0]*8+1}" y="${cell[1]*8+1}" width="6" height="6" fill="#e1c27d"/>`;

 const planned=$('map-dialog').open&&mapSelection?.version===state.version?mapSelection:null;
 const miniPath=planned?.path??travelPath;
 $('map-path-key').hidden=!miniPath.length;
 if(miniPath.length){
  let [x,y]=pos(state.player);
  let line=`M${x*8+4} ${y*8+4}`;
  for(const step of miniPath){
   const [dx,dy]=moveDirs[step];x+=dx;y+=dy;
   line+=`L${x*8+4} ${y*8+4}`;
  }
  mini+=`<path d="${line}" fill="none" stroke="#edcd8b" stroke-width="1.4"
   stroke-dasharray="2 2" pointer-events="none"/>`;
 }
 const miniTarget=planned?.target??travelTarget??pausedTravel;
 if(miniTarget){
  const [x,y]=miniTarget;
  mini+=`<circle cx="${x*8+4}" cy="${y*8+4}" r="5" fill="none" stroke="#edcd8b" stroke-width="2" stroke-dasharray="${travelTarget?'none':'2 2'}" pointer-events="none"/>`;
 }
 let viewBox=`-8 -8 ${state.width*8+16} ${state.height*8+16}`;
 if($('map-dialog').open&&charted.length){
  const xs=charted.map(([x])=>x), ys=charted.map(([,y])=>y);
  const left=Math.min(...xs)-1, top=Math.min(...ys)-1;
  viewBox=`${left*8} ${top*8} ${(Math.max(...xs)-left+2)*8} ${(Math.max(...ys)-top+2)*8}`;
 }
 $('minimap').setAttribute('viewBox',viewBox);
 $('minimap').innerHTML=mini;
}
function renderGrowth(){
 const g=state.growth, stats=state.waveStats;
 const weapon=state.weapons.find(w=>w.id===state.weapon);
 const hero=state.classes.find(c=>c.id===state.heroClass);
 $('loadout-title').textContent=`${hero?.name||'自由发射器'} · ${g.emitterName||weapon.name} +${g.level}`;
 const option=(key,item,selected)=>`<button data-${key}="${item.id}" aria-pressed="${selected}"><b>${esc(item.name)}</b><small>${esc(item.description)}</small></button>`;
 $('loadout').innerHTML=(hero?'':state.weapons.map(w=>option('equip',w,w.id===state.weapon)).join(''))
  +(g.launchers?.length?option('launcher',{...weapon,id:'standard'},!g.emitterName)
   +g.launchers.map(launcher=>option('launcher',launcher,launcher.active)).join(''):'')
  +state.modes.map(m=>option('tune',m,m.id===state.mode)).join('');
 const forge=g.forge;
 const forgeTitle=g.level===forge.level?'已达 +'+g.level:'+'+g.level+' → +'+forge.level;
 $('growth-weapon').innerHTML=`<p class="weapon-stats">波 ${stats.damage} 伤 · 射程 ${stats.range??'无限'} · ${stats.pierce===null?'贯穿全部敌人':stats.pierce===99?'范围命中':'至多命中 '+stats.pierce+' 个'}</p>
 ${g.emitterDescription?`<p>${esc(g.emitterDescription)}</p>`:''}
 <h3>锻造 <small>${g.cores} 核心</small></h3>
 <button type="button" data-growth="forge" aria-haspopup="dialog"><b>${esc(forgeTitle)}</b>
 <small>${esc(forge.blocked||forge.stats.map(stat=>stat.label).join('、'))}</small></button>
 <h3>当前刻印</h3>
 ${g.runeName?`<p><b>${esc(g.runeName)}</b> · ${esc(g.runeDescription)}</p>`:'<p class="empty">尚未装备刻印。</p>'}
 <p class="muted">到达刻印所在格后，在「脚下物品」中装备或替换。</p>`;
 $('character-avatar').innerHTML=art.portrait(state.heroColor);
 $('hud-avatar').innerHTML=art.portrait(state.heroColor);
 $('character-vitals').textContent=`生命 ${state.player.hp}/${state.maxHp??6} · 能量 ${state.player.energy}/${state.energyCap}`;
 const learned=g.talents.filter(t=>t.learned);
 $('talent-list').innerHTML=learned.length?learned.map(t=>`<div class="upgrade"><b>${esc(t.name)}</b><p>${esc(t.description)}</p></div>`).join(''):'<p class="empty">尚未学习天赋。</p>';
 $('growth-status').textContent=g.safe?'切换改装模式消耗一拍。':'请先脱战并等待回程波结算，再更换发射器或锻造。';
 if($('growth-dialog').open)renderGrowthPreview();
}

function renderGrowthPreview(){
 const g=state.growth, option=g.forge;
 const weapon=state.weapons.find(w=>w.id===state.weapon);
 $('growth-title').textContent=option.stats.length?`锻造至 +${option.level}`:'锻造';
 $('growth-cost').textContent=`${g.emitterName||weapon.name} · 消耗 1 枚锻造核心（持有 ${g.cores}）`;
 $('growth-preview').innerHTML=option.stats.map(({label,before,after,unit})=>
  `<p class="talent-change">${esc(label)} <b>${esc(before)} → ${esc(after)}${esc(unit)}</b></p>`).join('')
  +(option.note?`<p>${esc(option.note)}</p>`:'');
 $('growth-feedback').textContent=option.blocked||(!g.safe?'请先脱战并等待回程波结算。':'');
}

const QUICK_ITEMS=[
 {key:'q',storage:'bobozan-quick-item',id:'heal'},
 {key:'e',storage:'bobozan-quick-item-e',id:'smoke'}
];
for(const slot of QUICK_ITEMS){
 try{slot.id=localStorage.getItem(slot.storage)??slot.id}catch{}
}
function bindQuickItem(key,id){
 const slot=QUICK_ITEMS.find(entry=>entry.key===key);
 slot.id=id;
 try{localStorage.setItem(slot.storage,id)}catch{}
 renderBag();
 renderControls();
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
  const label=item?`${item.name} ×${count}`:'当前未携带已绑定道具';
  return `<button type="button" data-quick-use="${key}" aria-label="${esc(label)} · ${key.toUpperCase()}" title="${esc(label)}" ${item?'':'disabled'}>
   ${art.itemIcon(id)}<span class="quick-count">${count}</span><kbd>${key.toUpperCase()}</kbd></button>`;
 }).join('');
}
function throwTargets(item=aimingItem){
 if(item==='anchor_chain')return Object.keys(state.anchorChain?.targets??{}).map(key=>key.split(',').map(Number));
 return (item==='plant'?state.plantTargets:state.lureTargets)??[];
}
function useItem(item){
 if(item!=='plant'&&item!=='anchor_chain'&&!state.thrownItems?.includes(item))return send('item',null,item);
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

let selectedBagItem=null, selectedBagSlot=-1;
function renderBagItem(){
 const item=state.inventory.find(entry=>entry.id===selectedBagItem);
 $('bag-item-detail').hidden=!item;
 if(!item)return;
 $('bag-use-item').hidden=!!item.passive;
 $('bag-plant-item').hidden=!item.plantable;
 $('bag-item-name').textContent=item.name;
 $('bag-item-icon').innerHTML=art.itemIcon(item.id);
 for(const button of document.querySelectorAll('[data-bind-item]')){
  const bound=QUICK_ITEMS.some(slot=>slot.key===button.dataset.bindItem&&slot.id===item.id);
  button.hidden=!!item.passive;
  button.setAttribute('aria-pressed',String(bound));
 }
 $('bag-drop-item').textContent=item.plantable?'放下一颗 · 1 拍':'放下 · 1 拍';
 $('bag-item-description').textContent=item.description;
}
function renderBag(){
 renderQuickItems();
 $('drink-dew').textContent=`饮用露珠 ${state.dew??0}/${state.dewCapacity??3} · 1 拍`;
 $('bag-count').textContent=`${state.bagSlots.length} / ${state.bagCapacity} 槽 · 钥匙 ${state.keys}`;
 if(state.bagSlots[selectedBagSlot]?.id!==selectedBagItem){
  selectedBagSlot=state.bagSlots.findIndex(slot=>slot.id===selectedBagItem);
 }
 $('bag-slots').innerHTML=Array.from({length:state.bagCapacity},(_,i)=>{
  const slot=state.bagSlots[i];
  if(!slot)return `<div class="bag-slot empty-slot" aria-label="第 ${i+1} 槽，空"><span aria-hidden="true">空</span></div>`;
  const item=state.inventory.find(entry=>entry.id===slot.id);
  const keys=QUICK_ITEMS.filter(quick=>quick.id===item.id).map(quick=>quick.key.toUpperCase()).join(' ');
  return `<button class="bag-slot" data-item="${esc(item.id)}" data-bag-slot="${i}" aria-pressed="${i===selectedBagSlot}">
   ${art.itemIcon(item.id)}<b>${esc(item.name)}</b>${keys?`<kbd class="bag-binding">${keys}</kbd>`:''}
   ${slot.count>1?`<span class="bag-stack">×${slot.count}</span>`:''}</button>`;
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
 const type=offer.limit===1?'radio':'checkbox';
 $('talent-options').innerHTML='<legend>本层天赋</legend>'+offer.options.map(t=>{
  const preview=t.preview;
  const change=preview?.label?`<span class="talent-change">${esc(preview.label)}
   <b>${preview.before} → ${preview.after}</b></span>`:'';
  const note=preview?.note?`<small class="talent-note">${esc(preview.note)}</small>`:'';
  return `<label class="talent-option"><input type="${type}" name="talent-choice" value="${esc(t.id)}">
   <span><b>${esc(t.name)}</b><small>${esc(t.description)}</small>${change}${note}</span></label>`;
 }).join('');
 $('confirm-talents').disabled=true;
 $('talent-feedback').textContent='';
 closeDialogs();
 dialog.showModal();
}

function activeConditions(){
 const conditions=[];
 if(state.sanity<=state.sanityLow)conditions.push(['corrosion','◇',state.sanity?'理智偏低':'诅咒腐蚀',state.sanity?'未探索区域可能出现增援。击败敌人有机会掉落光点，拾取后恢复理智。':'诅咒会随行动持续扣除生命。击败敌人有机会掉落光点，拾取后恢复理智。']);
 for(const [kind,light] of Object.entries(LIGHT_INFO)){
  const turns=state.lightBlessings?.[kind];
  if(!turns)continue;
  const progress=kind==='light_radiant'?` · ${state.lightSteps}/${state.lightStepGoal} 步`:'';
  conditions.push([kind,light.glyph,`${light.name} ${turns} 拍${progress}`,lightEffect(kind)+'。']);
 }
 if(state.counter)conditions.push(['counter','✦','反击 +'+state.waveStats.counterBonus,'成功挡伤后获得。移动或攒能不会消耗它，下一发波或重波会使用这次加成。']);
 if(state.growth.strideReady)conditions.push(['stride','↗','踏步枪 · 射程 +1',state.growth.emitterDescription]);
 if(state.growth.barrierReady)conditions.push(['barrier-fan','⬟','屏障扇就绪',state.growth.emitterDescription]);
 if(state.gateShieldReady)conditions.push(['gate-shield','⬟','守门盾就绪','下一发波或重波的主束附带击退。发射后消耗，再次挡伤可重新触发。瞄准时用金色菱形标出可见的击退落点。']);
 if(state.poisoned)conditions.push(['poison','☣','中毒 · 1 伤','下一拍会受到 1 点毒伤。可在结算前使用疗愈药剂，也可用普通防抵挡。']);
 if(state.snared)conditions.push(['snared','⟐','夹足 · 1 拍','本拍不能移动或用飞雷神。其他行动仍可使用。']);
 else if(state.movementLocked)conditions.push(['frost','❄','霜冻 · 1 拍','本拍不能移动，也无法用飞雷神。可以攒、出波或防来度过这一拍。']);
 const cloud=state.smokeCells?.find(c=>same(pos(c),pos(state.player)));
 if(cloud)conditions.push(['cloud','≋','身处烟雾 · '+cloud.turns+' 拍','远处敌人无法隔着烟雾发现你。相邻敌人仍可攻击，能量波仍可穿过。']);
 if(state.smokeRemaining)conditions.push(['smoke','≋','烟雾 · '+state.smokeRemaining+' 拍','烟雾会遮蔽敌人的视线，但不会取消已经锁定的攻击。']);
 if(state.returning.some(w=>w.owner==='enemy'))conditions.push(['return','↶','敌方回波','下拍沿原路径返回，红色虚线圈标出经过的可见地格。离开路径或防御。']);
 if(state.returning.some(w=>w.sidePaths))conditions.push(['tide-return','↶',state.growth.orbWave?'回旋球待返回':'潮折回波','下一拍回波飞向行动后的位置。鼠标移到相邻地面可预览改线。']);
 return conditions;
}
function renderGroundItems(){
 const items=state.groundItems??[];
 if(!hasGroundItems()&&$('ground-dialog').open)$('ground-dialog').close();
 $('ground-items-hint').hidden=!items.length;
 const full=items.some(feature=>feature.items.some(item=>!state.packableItems.includes(item.id)));
 $('ground-items').innerHTML=items.flatMap(feature=>feature.items.map(item=>
  `<button type="button" data-pickup="${esc(feature.id)}" data-ground-item="${esc(item.id)}"
    ${state.packableItems.includes(item.id)?'':'disabled'}>${esc(item.name)}</button>`)).join('');
 $('ground-pick-all').hidden=items.reduce((count,feature)=>count+feature.items.length,0)<2;
 $('ground-bag').hidden=!full;
 const current=state.growth.runeName;
 $('ground-runes').innerHTML=(state.groundRunes??[]).map(rune=>{
  const blocked=rune.blocked||(!state.growth.safe?'请先脱战并等待回程波结算。':'');
  const label=current?`用「${rune.name}」替换「${current}」`:`拾取并装备「${rune.name}」`;
  return `<div class="upgrade"><p><b>${esc(rune.name)}刻印</b> · ${esc(rune.description)}</p>
   <button type="button" data-ground-rune="${esc(rune.id)}" data-blocked="${!!blocked}" ${blocked||!canAct()?'disabled':''}>${esc(label)}</button>
   ${blocked?`<small>${esc(blocked)}</small>`:''}</div>`;
 }).join('');
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
function renderCombatRecap(){
 const rows=state.effects.filter(fx=>fx.cells.length&&fx.target&&art.statusLabel(fx)).map(fx=>{
  const target=fx.targetId==null?fx.target:`${fx.target} #${fx.targetId+1}`;
  const label=art.statusLabel(fx);
  return `<li data-effect="${esc(fx.kind)}"><span>${esc(target)}</span><b>${esc(label)}</b>
   ${fx.source?`<small>${esc(fx.source)}</small>`:''}</li>`;
 }).join('');
 $('combat-recap').hidden=!rows;
 $('combat-recap').innerHTML=rows;
 $('journal-combat').hidden=!rows;
 $('journal-combat-title').textContent=`第 ${state.turn} 拍结算`;
 $('journal-combat-recap').innerHTML=rows;
}
function render(showEffects=false){
 $('room-name').textContent=state.roomName;
 const theme={water:'积水',grass:'草木茂盛'}[state.floorTheme];
 $('floor-theme').hidden=!theme;
 $('floor-theme').textContent=theme?' · '+theme:'';
 $('floor-label').textContent=state.region;
 $('floor-index').hidden=false;
 $('floor-index').textContent=`${state.depth}/${state.lastFloor} 层`;
 renderGrowth();renderBag();
 $('tactics').innerHTML=
  (state.anchorChain?`<button data-anchor-chain title="每下到新的一层补充一次充能">锚链 ${state.anchorChain.charges}/1</button>`:'')+
  (state.storedCharge!=null?`<button data-stored-charge>预藏 ${state.storedCharge}/1</button>`:'')+
  (state.lock&&Math.abs(state.lock[0]-state.player.x)+Math.abs(state.lock[1]-state.player.y)===1?'<button data-unlock>打开锁门</button>':'')+
  (unopenedSupplyAt(pos(state.player))?'<button data-open-supply>打开补给箱</button>':'')+
  (canForecastDefense()?'<button data-guard-forecast aria-haspopup="dialog">防御试算</button>':'')+
  (hasGroundItems()?'<button data-ground>脚下物品</button>':'');
 $('turn').textContent=String(state.turn).padStart(2,'0');$('seed').textContent='SEED '+state.seed;
 $('room-status').textContent=state.result?(state.result==='victory'?'试炼完成':'冒险结束'):state.choices.length?'选择旅途馈赠':state.returning.length?'回旋波即将返回':state.pursuing?(state.enemies.find(e=>e.intent.action==='notice')?'敌人刚发现你':'敌人警觉'):'探索中';
 $('route').textContent=`${state.roomStates.filter(room=>room.discovered).length}/${state.roomStates.length} 区域`;
 renderConditions();
 document.querySelector('[data-action="charge"] small').textContent=`能量 +${state.lightBlessings?.light_soul?2:1}`;
 document.querySelector('[data-action="wave"] small').textContent=`消耗 ${state.waveStats.waveCost??1} · 伤害 ${state.waveStats.damage}`;
 document.querySelector('[data-action="heavy"] small').textContent=`消耗 ${state.waveStats.heavyCost} · 伤害 ${state.waveStats.heavyDamage}`;
 document.querySelector('[data-action="guard"] small').textContent=`${state.mode==='armor'?'消耗 1 · ':''}挡 ${state.waveStats.guardLimit} 伤`;
 $('hp').textContent=state.player.hp+' / '+(state.maxHp??6);$('energy').textContent=state.player.energy+' / '+state.energyCap;
 $('sanity').textContent=`${state.sanity} / ${state.sanityMax}`;
 $('sanity-bar').max=state.sanityMax;
 $('sanity-bar').value=state.sanity;
 $('sanity-status').classList.toggle('low-sanity',state.sanity<=state.sanityLow);
 $('sanity-status').title=state.sanity>state.sanityLow?`每行动 ${state.sanityTurnsPerPoint} 拍消耗 1 点理智。拾取微光、圣光或辉光可回复。`:state.sanity?'理智偏低，未探索区域可能出现增援':'理智耗尽，诅咒腐蚀生命';
 $('hp-bar').max=state.maxHp;
 $('hp-bar').value=state.player.hp;
 $('energy-bar').innerHTML=Array.from({length:state.energyCap},(_,i)=>`<i class="pip ${i<state.player.energy?'on':''}"></i>`).join('');
 renderEnemyLists();
 const owned=new Map(state.upgrades.map(u=>[u.id,u.name]));
 const names={heart:'护心',refund:'余势',echo:'回响',bag:'蓄能袋',pierce:'穿透',reflect:'反弹'};
 $('upgrade-count').textContent=state.upgrades.length+' / '+(state.upgradeCount??6);
 $('upgrades').innerHTML=state.upgrades.map(u=>`<div class="upgrade">✦ ${esc(u.name)}<p>${esc(u.description)}</p></div>`).join('')||'<p class="empty">区域遗物宝箱和守关者会提供遗物。</p>';
 $('upgrades').innerHTML+=state.builds.map(b=>`<div class="upgrade">${esc(b.name)} · ${b.active?'已激活':b.requires.map(k=>names[k]).join(' + ')}<p>${esc(b.effect)}</p></div>`).join('');
 if(owned.has('echo')) $('upgrades').innerHTML+=`<p>回响已累计 ${state.echoProgress} 次攒</p>`;
 if(owned.has('heart')) $('upgrades').innerHTML+=`<p>护心本区域剩余 ${state.heartLeft} 次</p>`;
 if(owned.has('gate_shield')) $('upgrades').innerHTML+=`<p>守门盾 · ${state.gateShieldReady?'下一发主束附带击退':'等待有效格挡'}</p>`;
 renderHistory();
 renderCombatRecap();
 $('log').innerHTML=state.log.map(t=>`<li>${esc(t)}</li>`).join('');
 renderBoard(showEffects);if($('ground-dialog').open)renderGroundItems();renderLandmarks();renderControls();renderTalentChoice();
 if(state.talentChoice)return;
 if(state.choices.length){
  const supply=state.choices[0].supply;
  const selected=$('reward-dialog').open?$('rewards').querySelector('input:checked')?.value:null;
  $('rewards').innerHTML=state.choices.map(c=>{
   const id=esc(c.id), name=esc(c.name), description=esc(c.description);
   if(supply){
    const comparison=(c.comparison??[]).map(({label,before,after})=>`
     <span class="supply-compare-row"><span>${esc(label)}</span>
     <span>${before===after?esc(after):`${esc(before)} <span aria-label="换装后">→</span> <b>${esc(after)}</b>`}</span></span>
    `).join('');
    return `<button class="reward-option" type="button" data-supply="${id}" ${c.blocked?'disabled':''}>
     ${c.equipment?`<i class="item-icon">${art.uiIcon('wave')}</i>`:art.itemIcon(c.id)}<span class="supply-reward-info"><b>${name}</b>
     <small>${description}${c.blocked?' · 背包装不下':''}</small>${comparison?`<span class="supply-compare">${comparison}</span>`:''}</span>
    </button>`;
   }
   const stats=(c.preview?.stats??[]).map(({label,before,after})=>
    `<span class="talent-change">${esc(label)} <b>${before==null?'':esc(before)+' → '}${esc(after)}</b></span>`).join('');
   const combos=(c.preview?.combos??[]).map(({name,effect,missing})=>
    `<small class="reward-combo">${missing.length?'还需 '+esc(missing.join('、')):'立即激活'} · ${esc(name)}<br>${esc(effect)}</small>`).join('');
   return `<label class="reward-option">
    <input type="radio" name="relic" value="${id}" aria-labelledby="reward-name-${id}"
     aria-describedby="reward-detail-${id}" ${selected===c.id?'checked':''}>
    <span><b id="reward-name-${id}">${c.id==='impact'?'<i class="relic-impact-icon">'+art.uiIcon('impact')+'</i>':''}${name}</b><span id="reward-detail-${id}">
     <small>${description}</small>${stats}${combos}</span></span>
   </label>`;
  }).join('');
  $('reward-title').textContent=supply?'选择一件战术补给':'选择一件遗物';
  const currentLauncher=state.growth.emitterName||state.weapons.find(w=>w.id===state.weapon)?.name;
  $('reward-description').textContent=!supply?'领取后在本次冒险中持续生效。':state.choices.some(c=>c.equipment)
   ?`每箱可领取一项。当前装备 ${currentLauncher}，换装比较按当前状态、计算敌人防御前的数值。`
   :'可以带走一件。背包装不下时，可先整理再继续选择。';
  $('confirm-reward').hidden=!!supply;
  $('confirm-reward').disabled=busy||!selected;
  $('organize-for-supply').hidden=!supply||!state.choices.some(c=>c.blocked);
  $('skip-reward').textContent=supply?'稍后再选':'跳过本次奖励';
  if(!$('reward-dialog').open){closeDialogs();$('reward-dialog').showModal()}
 }
 else if($('reward-dialog').open)$('reward-dialog').close();
 if(state.result&&showEffects&&(state.falls.length||state.fallTransition)){setTimeout(()=>render(),800);return}
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
async function send(action,direction=null,choice=null){
 if(busy||!state)return false;
 busy=true;
 aim=null;
 aimingItem=null;
 tideHover=null;
 refreshPreview();
 renderControls();
 $('saved').textContent='保存中…';
 try{
  const {depth,turn,version}=state;
  state=await api('action',{action,direction,choice,version});
  if(state.result||state.depth!==depth)forgetTravel();
  else if(same(pos(state.player),pausedTravel))setPausedTravel(null);
  toast(state.log[0]||'继续探索。');
  const animate=state.turn!==turn;
  if(state.fallTransition){
   const wrap=$('board').parentElement;
   wrap.classList.remove('fall-arrival');
   void wrap.offsetWidth;
   wrap.classList.add('fall-arrival');
  }
  render(animate);
  clearTimeout(fxTimer);
  if(animate)fxTimer=setTimeout(()=>renderBoard(),state.falls.length?820:740);
  $('saved').textContent='● 进度已保存';
  return true;
 }catch(e){
  toast(e.name==='AbortError'?'连接超时，正在恢复已保存局面。':e.message,true);
  try{
   state=await api('state');
   render();
   $('saved').textContent='● 已恢复存档';
  }catch{
   $('saved').textContent='连接断开 · 刷新重试';
  }
  return false;
 }finally{
  busy=false;
  renderControls();
 }
}
let previewRequest=0;
async function refreshPreview(){
 const request=++previewRequest;
 const panel=$('shot-preview');
 aimDetails=null;
 shotHighlight.hover=shotHighlight.focus=shotHighlight.touch=null;
 endShotPress();
 if(!aim){panel.hidden=true;return}
 const action=aim, version=state.version;
 const radial=radialWave(action);
 const upgrades=new Set(state.upgrades.map(upgrade=>upgrade.id));
 const directions=action==='dodge'?Object.keys(state.dodgeTargets):radial&&!upgrades.has('parallel')&&!(upgrades.has('blink')&&upgrades.has('pierce'))
  ?['right']:Object.keys(dirs);
 panel.hidden=false;
 panel.textContent='计算伤害…';
 try{
  const previews=await Promise.all(directions.map(async direction=>[
   direction,await api('preview',{action,direction,version})
  ]));
  if(request===previewRequest&&aim===action&&state.version===version){
   aimDetails=Object.fromEntries(previews);
   panel.innerHTML='<p class="shot-touch-hint">长按看路线，轻点发射。</p>'+previews.map(([direction,result])=>{
    const formatHits=hits=>hits?.map(h=>h.name+' '+h.damage+' 伤').join('、')??'';
    const sources=result.hitSources;
    const primary=action==='reflect'?'reflection':'wave';
    const shotLabel=action==='dodge'?'闪避':action==='reflect'?'反射':'新波';
    const hits=formatHits(sources?sources[primary]:result.hits);
    const pending=[['return','回波'],['burn','灼烧'],['groundFire','地火']].map(([key,label])=>{
     const line=formatHits(sources?.[key]);
     return line?`<small class="shot-pending"><b>${label}</b> ${esc(line)}</small>`:'';
    }).join('');
    const received=result.received??[];
    const damage=received.reduce((total,hit)=>total+hit.damage,0);
    const risk=damage?`<strong class="shot-risk">预计受伤 ${damage}</strong>
      <small>${esc(received.map(hit=>hit.name).join('、'))}</small>`:'';
    const reflected=result.reflected?`<small>反弹抵消 ${result.reflected} 伤</small>`:'';
    const events=result.events?.length?`<small>${esc(result.events.join('、'))}</small>`:'';
    const interceptions=(result.interceptions??[]).map(hit=>
     `<small class="shot-interception">${esc(hit.guard)}替${esc(hit.target)}挡波${hit.damage===0?'，护甲挡下全部伤害':''}</small>`).join('');
    const actionText=action==='dodge'
     ?{moved:'闪避一步',blocked:'抢位·原地停留',fall:'坠落危险'}[result.stepOutcome]
     :`${pending||!hits?shotLabel+' ':''}${hits||'无可见命中'}`;
    return `<button type="button" class="shot-direction" data-preview-direction="${direction}">
     <b>${radial&&directions.length===1?'范围':arrows[direction]}</b><span>${esc(actionText)}</span>${interceptions}${pending}${risk}${reflected}${events}</button>`;
   }).join('');
   renderBoard();
  }
 }catch{
  if(request===previewRequest&&aim===action&&state.version===version)panel.textContent='局面变化，请重新瞄准。';
 }
}
function highlightedShotDirection(){return shotHighlight.hover??shotHighlight.focus??shotHighlight.touch}
function highlightShot(direction, source){
 const previous=highlightedShotDirection();
 if(source==='touch')shotHighlight.focus=shotHighlight.hover=null;
 shotHighlight[source]=direction;
 const active=highlightedShotDirection();
 if(previous===active||!aimDetails)return;
 $('shot-preview').querySelectorAll('[data-preview-direction]').forEach(button=>
  button.toggleAttribute('data-preview-active',button.dataset.previewDirection===active));
 renderBoard();
}
function endShotPress(){
 if(!shotPress)return;
 clearTimeout(shotPress.timer);
 shotPress=null;
}
$('shot-preview').addEventListener('pointerover',event=>{
 if(event.pointerType!=='touch')highlightShot(event.target.closest('[data-preview-direction]')?.dataset.previewDirection??null,'hover');
});
$('shot-preview').addEventListener('pointerleave',()=>highlightShot(null,'hover'));
$('shot-preview').addEventListener('focusin',event=>highlightShot(event.target.dataset.previewDirection??null,'focus'));
$('shot-preview').addEventListener('focusout',event=>{
 const next=event.relatedTarget;
 highlightShot($('shot-preview').contains(next)?next.dataset.previewDirection??null:null,'focus');
});
$('shot-preview').addEventListener('pointerdown',event=>{
 if(!event.isPrimary||event.button!==0)return;
 endShotPress();
 suppressShotClick=false;
 const button=event.target.closest('[data-preview-direction]');
 if(event.pointerType!=='touch'||!button||!aimDetails||!canAct())return;
 const direction=button.dataset.previewDirection;
 const press={id:event.pointerId,x:event.clientX,y:event.clientY,timer:null};
 shotPress=press;
 press.timer=setTimeout(()=>{
  if(shotPress!==press||!aimDetails||!canAct())return;
  suppressShotClick=true;
  highlightShot(direction,'touch');
 },380);
});
$('shot-preview').addEventListener('pointermove',event=>{
 if(shotPress?.id!==event.pointerId||Math.hypot(event.clientX-shotPress.x,event.clientY-shotPress.y)<12)return;
 suppressShotClick=true;
 endShotPress();
});
for(const type of ['pointerup','pointercancel','lostpointercapture']){
 $('shot-preview').addEventListener(type,event=>{
  if(shotPress?.id!==event.pointerId)return;
  if(type!=='pointerup')suppressShotClick=true;
  endShotPress();
 });
}
$('shot-preview').addEventListener('contextmenu',event=>{
 if((shotPress||suppressShotClick)&&event.target.closest('[data-preview-direction]'))event.preventDefault();
});
$('shot-preview').addEventListener('click',event=>{
 const button=event.target.closest('[data-preview-direction]');
 if(suppressShotClick&&(event.detail>0||event.pointerType==='touch'||event.sourceCapabilities?.firesTouchEvents)){
  suppressShotClick=false;
  event.preventDefault();
  return;
 }
 if(button&&aim&&canAct())direction(button.dataset.previewDirection);
});
function chooseAction(action){aimingItem=null;setInspecting(false);cancelTravel();if(!canAct())return;const b=document.querySelector(`[data-action="${action}"]`);if(b?.disabled||b?.hidden)return;if(['wave','heavy','reflect','dodge'].includes(action)){aim=aim===action?null:action;toast(aim==='dodge'?'选择相邻方向闪避。':aim==='reflect'?'选择反射方向，确认后消耗 1 能量。':radialWave(aim)?'点击身边的高亮地格，或在预览中确认出波。':aim?(state.growth.orbWave?'点击射线选定落点，或按方向键发到最远。':'按方向键，或左键点射线和敌人出波。右键查看。'):'已取消瞄准。');refreshPreview();renderBoard();renderControls()}else send(action)}
function direction(d, target=null){
 if(aimingItem){aimingItem=null;renderControls();renderBoard()}
 setInspecting(false);
 cancelTravel();if(!canAct())return;
 if(aim&&(!dirs[d]||(aim==='dodge'&&!state.dodgeTargets[d])))return;
 return send(aim||'move',d,state.growth.orbWave&&['wave','heavy'].includes(aim)?target:null);
}
$('loadout').addEventListener('click',event=>{
 const button=event.target.closest('button');if(!button||!canAct())return;
 cancelTravel();
 if(button.dataset.launcher)send('equip_launcher',null,button.dataset.launcher);
 else send(button.dataset.equip?'equip':'tune',null,button.dataset.equip||button.dataset.tune);
});
async function reset(seed,heroClass){aimingItem=null;setInspecting(false);forgetTravel();if(busy)return;busy=true;renderControls();try{state=await api('reset',{version:state.version,heroClass,...(seed===undefined?{}:{seed})});aim=null;refreshPreview();displayedResult=null;closeDialogs();toast('新的冒险。先观察敌人，再行动。');render();$('saved').textContent='● 进度已保存'}catch(e){toast(e.message,true);try{state=await api('state');render()}catch{}}finally{busy=false;renderControls()}}
const enemyProfiles = {
 charger: {maxHp:2,attack:'1',description:'无能量时先攒；有能量且与你处于无遮挡的同一直线时出波。否则会接近你。侧移或利用墙壁可避开已锁定的波。'},
 ram: {maxHp:2,attack:'1',description:'远处时向你接近，相邻时冲撞提前锁定的格子。冲撞不会追踪你移动后的位置，可以侧移躲开。'},
 shield: {maxHp:3,attack:'1',description:'举盾 → 卸盾空档 → 接近或冲撞，循环行动。举盾可抵挡 2 点伤害，卸盾时露出空档。'},
 boss: {maxHp:6,attack:'1 / 2',description:'会发射直线波，也会先预告震荡范围，再攻击原位置。半血后改为更强的十字震荡。震荡后会休整一拍。'}
};
function enemyEffects(enemy){
 if(enemy.disguised)return [];
 return [
  enemy.burning&&['灼烧 '+enemy.burning+' 拍','每拍受到 1 点伤害，浅水可熄灭。','burn'],
  enemy.frost_stacks&&['叠霜 '+enemy.frost_stacks+'/2 层','叠满后会冻结一次移动。','frost'],
  enemy.frozen&&['冻结','下一次尝试移动时停在原地。','frost'],
  enemy.defense_lost&&[`蚀盾 · 防御 −${enemy.defense_lost}`,'后续受击时，护甲与举盾的减伤降低。','defense_loss'],
  enemy.range_penalty&&[`中断 · 射程 −${enemy.range_penalty}`,'下次蓄力攻击仍会发出，射程缩短至最少 0 格。','range_loss'],
  enemy.guardedBy&&[`由${enemy.guardedBy}掩护`,'保持相邻时，护卫可替它承受能量波。','escort-cover'],
  enemy.stunned&&['击晕 · 1 拍','本拍跳过行动。','stun'],
  enemy.stun_marked&&['击晕进度 · 1/2','下一拍再次用主束命中即可击晕。','stun'],
  enemy.fear&&['惊退 '+enemy.fear+' 拍','接下来会尝试远离你。','fear']
 ].filter(Boolean);
}
function renderEnemyLists(){
 const priority=e=>e.intent.cells.length||e.intent.water?.length?2:e.intent.warning?.length?1:0;
 const enemies=[...state.enemies].sort((a,b)=>priority(b)-priority(a));
 const rows=enemies.map(enemy=>{
  const risk=['quiet','warning','danger'][priority(enemy)];
  const hp=enemy.disguised?'状态未知':`${enemy.hp}/${enemy.maxHp??enemy.hp} 生命`;
  const statuses=enemyEffects(enemy).map(([label])=>label);
  return `<button type="button" class="enemy-card" data-inspect-enemy="${enemy.id}" data-risk="${risk}">
   <span class="enemy-line"><b class="enemy-name">${esc(enemy.name)}</b><span class="enemy-hp">${hp}</span></span>
   <span class="enemy-intent">${esc(enemy.intent.label)}${enemy.intent.direction?' '+arrows[enemy.intent.direction]:''}</span>
   ${statuses.length?`<small>${esc(statuses.join(' · '))}</small>`:''}</button>`;
 }).join('');
 $('enemies').innerHTML=rows||'<p class="empty">当前视野内没有敌人。</p>';
 $('encounter-strip').innerHTML=rows;
 const boss=enemies.find(e=>['boss','breaker','mirrorboss'].includes(e.kind)&&!e.disguised);
 $('boss-banner').hidden=!boss;
 if(boss){
  $('boss-name').textContent=boss.name;
  $('boss-hp').textContent=`${boss.hp}/${boss.maxHp??boss.hp}`;
  $('boss-health').max=boss.maxHp??boss.hp;
  $('boss-health').value=boss.hp;
 }
}

function renderEnemyIntent(enemy){
 const {intent}=enemy;
 const area=[
  ...intent.cells.map(cell=>[cell,'attack']),
  ...(intent.water??[]).map(cell=>[cell,'water']),
  ...(intent.warning??[]).map(cell=>[cell,'warning']),
  ...(intent.target&&intent.action==='move'?[[intent.target,'move']]:[])
 ];
 const layer=new Map(area.map(([cell,kind])=>[cell.join(','),kind]));
 const hero=pos(state.player), origin=pos(enemy);
 const heroRisk=layer.get(hero.join(','));
 const risk=heroRisk==='attack'||heroRisk==='water'?' · 你脚下在攻击范围内'
  :heroRisk==='warning'?' · 你脚下在预告范围内':'';
 $('enemy-current').textContent=intent.label+risk;
 const map=$('enemy-intent-map');
 map.hidden=!area.length;
 if(map.hidden)return;
 const cells=[hero,origin,...area.map(([cell])=>cell)];
 const xs=cells.map(([x])=>x), ys=cells.map(([,y])=>y);
 const left=Math.min(...xs), top=Math.min(...ys);
 const width=Math.max(...xs)-left+1, height=Math.max(...ys)-top+1;
 const walls=new Set(state.walls.map(c=>c.join(',')));
 const tiles=state.visible.filter(([x,y])=>x>=left&&x<left+width&&y>=top&&y<top+height);
 const marks=tiles.map(([x,y])=>{
  const key=[x,y].join(','), kind=layer.get(key)??(walls.has(key)?'wall':'floor');
  return `<rect class="intent-${kind}" x="${x-left+.06}" y="${y-top+.06}" width=".88" height=".88"/>`;
 }).join('');
 const marker=([x,y],kind)=>`<circle class="intent-${kind}" cx="${x-left+.5}" cy="${y-top+.5}" r=".25"/>`;
 const legend={attack:'攻击',water:'导电',warning:'预告',move:'移动落点',hero:'你',source:'敌人'};
 const keys=[...new Set(layer.values()),'hero','source'];
 map.innerHTML=`<svg viewBox="0 0 ${width} ${height}" width="${width*22}" height="${height*22}" aria-hidden="true">
  ${marks}${marker(hero,'hero')}${marker(origin,'source')}</svg>
  <ul class="enemy-intent-key" aria-label="意图图例">${keys.map(key=>`<li><i class="intent-${key}"></i>${legend[key]}</li>`).join('')}</ul>`;
}

function inspectEnemy(enemy){
 const profile=enemyProfiles[enemy.kind]||{maxHp:enemy.maxHp,attack:enemy.attack??(enemy.kind==='breaker'?2:enemy.intent.damage||1),description:enemy.description};
 $('enemy-name').textContent=enemy.name;
 $('enemy-portrait').innerHTML=art.enemyPortrait(enemy);
 $('enemy-health').hidden=!!enemy.disguised;
 $('enemy-stats').hidden=!!enemy.disguised;
 $('enemy-intent-panel').hidden=!!enemy.disguised;
 const maxHp=enemy.maxHp??profile.maxHp??enemy.hp;
 $('enemy-hp').textContent=`生命 ${enemy.hp} / ${maxHp}`;
 $('enemy-hp-bar').max=maxHp;
 $('enemy-hp-bar').value=enemy.hp;
 $('enemy-attack').textContent=enemy.attack??profile.attack;
 $('enemy-defense').textContent=enemy.defense?`${enemy.defense} · ${enemy.kind==='escort'?'护甲':'举盾'}`:'0';
 $('enemy-energy').textContent=enemy.energy;
 if(!enemy.disguised)renderEnemyIntent(enemy);
 const effects=enemyEffects(enemy);
 $('enemy-effects-panel').hidden=!effects.length;
 $('enemy-effects').innerHTML=effects.map(([label,detail,kind])=>`<li data-effect="${kind}"><b>${esc(label)}</b><span>${esc(detail)}</span></li>`).join('');
 $('enemy-method-title').textContent=enemy.disguised?'外观':'攻击方式';
 const weapon=state.weapons.find(w=>w.id===enemy.emitter)?.name;
 const rune=RUNE_DETAILS[enemy.inscription];
 $('enemy-method').textContent=(profile.description??'')+(weapon?` 持有 ${[weapon,rune].filter(Boolean).join(' · ')}。`:'');
 $('enemy-loot').hidden=!enemy.lootHint;
 $('enemy-loot').textContent=enemy.lootHint??'';
 $('enemy-light-loot').hidden=!enemy.lightLoot;
 $('enemy-light-loot').textContent=enemy.lightLoot
  ?'光点掉率 · '+Object.entries(LIGHT_INFO).map(([kind,light])=>`${light.name} ${enemy.lightLoot[kind]}%`).join(' · ')
  :'';
 $('enemy-dialog').showModal();
}
for(const id of ['enemies','encounter-strip']){
 $(id).addEventListener('click',event=>{
  const button=event.target.closest('[data-inspect-enemy]');
  if(!button||busy)return;
  const enemy=state.enemies.find(e=>e.id===Number(button.dataset.inspectEnemy));
  if(enemy){cancelTravel();inspectEnemy(enemy)}
 });
}
let travelId=0, travelMove=null, travelPath=[], travelTarget=null, pausedTravel=null;
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
 const wasTraveling=!!travelTarget;
 travelId++;
 travelPath=[];
 if(wasTraveling)setTravelTarget(null);
}
function unsafeTravelStep(cell,stepOnTrap=false){
 return state.walls.some(wall=>same(wall,cell))||same(state.lock,cell)||
  state.dangerCells?.some(danger=>same(danger,cell))||
  state.returning.some(wave=>wave.owner==='enemy'&&wave.cells.some(danger=>same(danger,cell)))||
  state.enemies.some(enemy=>same(pos(enemy),cell)||same(enemy.intent.target,cell)&&enemy.intent.action==='move')||
  state.terrain.some(tile=>same(pos(tile),cell)&&
   (['mirror','rubble'].includes(tile.kind)||(!stepOnTrap&&(tile.kind==='fragile'||tile.kind==='trap'&&tile.armed))));
}
function travelNeedsCaution(){
 return state.pursuing||state.returning.length||state.dangerCells?.length;
}
function visibleHostileIds(){
 return new Set(state.enemies.filter(enemy=>!enemy.dormant&&!enemy.disguised).map(enemy=>enemy.id));
}
function discoveredHostile(previous){
 return [...visibleHostileIds()].some(id=>!previous.has(id));
}
async function travelTo(target,id,previous,stepOnTrap){
 const inspectLoot=groundLootAt(target);
 let replan=false;
 try{
  do{
   const response=await api('path',{target,version:state.version,stepOnTrap});
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
    const previousEnemies=visibleHostileIds();
    const hp=state.player.hp, step=travelPath[0];
    const [dx,dy]=moveDirs[step];
    const next=[state.player.x+dx,state.player.y+dy];
    if(unsafeTravelStep(next,stepOnTrap&&same(next,target))){
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
     discoveredHostile(previousEnemies)||travelNeedsCaution();
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
    if(inspectLoot&&same(pos(state.player),target)&&hasGroundItems()&&!travelNeedsCaution()){
     showGroundItems();
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
function requestTravel(target,stepOnTrap=false){
 const previous=pausedTravel;
 setPausedTravel(null);
 travelPath=[];
 const id=++travelId;
 setTravelTarget(target,'寻路中…');
 return travelTo(target,id,previous,stepOnTrap);
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
function examineCell(target, preferEnemy=false){
 const enemy=state.enemies.find(e=>same(pos(e),target));
 const hazardDetails=cellHazards(target);
 setInspecting(false);
 if(enemy&&(preferEnemy||!hazardDetails.length)){inspectEnemy(enemy);return}
 const terrain=state.terrain.find(t=>same(pos(t),target));
 const door=state.doors.some(p=>same(p,target));
 const title=state.walls.some(p=>same(p,target))?'石墙':
  same(target,state.lock)?(lockStyle()?.name??'库房锁门'):door?'石门':
  same(target,state.exit)?(state.floorKind==='relic'?'终点祭坛':'下层阶梯'):
  same(target,state.upStairs)?'上层阶梯':terrain?terrainName(terrain):'地面';
 const lines=[...hazardDetails];
 if(same(target,state.entrance))lines.push(state.upStairs?'站在阶梯上再点击，即可返回上一层。':'本层入口，也是回程卷轴的落点。');
 if(state.openedShortcuts?.some(cell=>same(cell,target)))lines.push('已经揭开的隐蔽通路，可以双向穿行。');
 const smoke=state.smokeCells?.find(c=>same(pos(c),target));
 if(smoke)lines.push('烟雾还会持续 '+smoke.turns+' 拍，遮蔽敌人的视线。');
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
  if(feature.inspectItems?.length){
   for(const item of feature.inspectItems)lines.push(item.name+' · '+item.description);
  }else{
   lines.push((feature.kind==='dry_spring'||emptyChest(feature)?'':feature.used?'已使用：':'可拾取或使用：')+featureName(feature));
  }
  const light=LIGHT_INFO[feature.kind];
  if(light)lines.push(`${lightEffect(feature.kind)}，持续 ${state.lightDuration[feature.kind]} 拍。`);
  if(feature.kind==='supply_choice'&&!feature.used){
   lines.push('点击箱子走过去并打开。已站在箱上时，可点脚下或「打开补给箱」。');
   for(const item of state.supplyOptions??[])lines.push(item.name+' · '+item.description);
  }
 }
 $('cell-title').textContent=title;
 $('cell-details').innerHTML=lines.map(line=>`<li>${esc(line)}</li>`).join('');
 $('cell-details').hidden=!lines.length;
 openPanel('cell-dialog');
}
function cellHazards(target){
 const details=[];
 const contains=cells=>cells?.some(cell=>same(cell,target));
 if(contains(state.fireCells))details.push('下一拍 · 地火 1 伤。凝霜雾弹可扑灭。');
 if(contains(state.boneburstCells))details.push('下一拍 · 碎骨爆发 1 伤。');
 for(const wave of state.returning){
  if(wave.owner==='enemy'&&contains(wave.cells))details.push(`下一拍 · 敌方回波 ${wave.damage} 伤。`);
 }
 const terrainSources=details.length;
 let namedAttack=false;
 for(const enemy of state.enemies){
  const {intent}=enemy;
  if(contains(intent.cells)||contains(intent.water)){
   const effect=contains(intent.water)?'（浅水导电）':'';
   details.push(`下一拍 · ${enemy.name}：${intent.label}${effect}。`);
   namedAttack=true;
  }
  if(contains(intent.warning))details.push(`敌方预告 · ${enemy.name}：${intent.label}。`);
 }
 if(!namedAttack&&!terrainSources&&contains(state.dangerCells))details.push('下一拍 · 此格在攻击范围内。');
 return details;
}
async function mapClick(target, landmark=false, touch=false){
 if(!state)return;
 if(inspecting&&!landmark){examineCell(target);return}
 if(aimingItem&&!landmark){
  const redirect=aimingItem!=='plant'&&aimingItem!=='anchor_chain'&&state.throwRedirects?.[target.join(',')];
  if(!redirect&&!throwTargets().some(p=>same(p,target))){toast('请选择四格内高亮的地格。',true);return}
  lureSelection=target;
  lureHover=null;
  if(redirect)toast('道具会落在障碍近侧的高亮格。');
  renderControls();
  renderBoard();
  return;
 }
 const [x,y]=target;
 const rerouting=!!(travelTarget||travelMove);
 const pendingMove=travelMove;
 const clickFloor=state.depth;
 const stoodAtExit=same(pos(state.player),state.exit);
 const selection=++travelId;
 travelPath=[];
 if(rerouting)setTravelTarget(target,'改道中…');
 if(pendingMove)await pendingMove;
 if(selection!==travelId)return;
 if(!state||busy||state.depth!==clickFloor){cancelTravel();return}
 const enemy=state.enemies.find(e=>e.x===x&&e.y===y);
 if(enemy&&!landmark&&!aim){
  cancelTravel();
  if(touch)inspectEnemy(enemy);
  else if(canAct())toast('先选择波或重波，再左键确认方向。右键查看敌人。');
  return;
 }
 if(!canAct()){cancelTravel();return}
 const tile=state.terrain.find(t=>t.x===x&&t.y===y);
 if(!aim&&tile&&['mirror','rubble'].includes(tile.kind)){cancelTravel();toast(terrainName(tile)+(tile.rotating?' · 用波击中可旋转':''));return}
 if(!landmark&&stoodAtExit&&!state.exitUnlocked&&same(target,state.exit)){
  cancelTravel();toast(state.exitLockReason??'阶梯仍被封锁。',true);return;
 }
 if(!landmark&&stoodAtExit&&state.exitUnlocked&&same(target,state.exit)&&same(pos(state.player),state.exit)){cancelTravel();send('exit');return}
 if(!landmark&&!aim&&same(target,state.upStairs)&&same(target,pos(state.player))){cancelTravel();send('ascend');return}
 if(!aim&&unopenedSupplyAt(target)){
  if(same(target,pos(state.player))){
   cancelTravel();
   await send('open_supply');
  }else requestTravel(target);
  return;
 }
 if(!aim&&!landmark&&same(target,pos(state.player))){
  if(hasGroundItems()){
   showGroundItems();
   return;
  }
 }
 const dx=x-state.player.x,dy=y-state.player.y;let d;
 const moves=state.heroClass==='fan'?moveDirs:dirs;
 const step=Object.keys(moves).find(key=>same(moves[key],[dx,dy]));
 if(aim==='dodge'){
  if(step&&state.dodgeTargets[step])direction(step);
  else toast('请选择高亮的相邻地格。',true);
  return;
 }
 if(!landmark&&!aim&&same(target,state.lock)&&Math.abs(dx)+Math.abs(dy)===1){cancelTravel();send('unlock');return}
 if(aim){
  const orbAim=state.growth.orbWave&&['wave','heavy'].includes(aim);
  const matching=Object.keys(aimDetails??dirs).filter(heading=>
   (orbAim?state.orbTargets[heading]:ray(heading)).some(cell=>same(cell,target)));
  if(orbAim&&!matching.length)return toast('请选择能量球射线上可见的目标格。',true);
  if(radialWave(aim)){
   if(!matching.length)return toast('请选择身边高亮的地格。',true);
   const heading=Math.abs(dx)>=Math.abs(dy)?(dx<0?'left':'right'):(dy<0?'up':'down');
   d=matching.includes(heading)?heading:matching[0];
  }
  else if(matching.length===1)d=matching[0];
  else if(matching.length>1)return toast('多条波经过这里，请在预览中选择发射方向。');
  else if(enemy)return toast('该敌人当前不在射线上。',true);
  else if(dx===0&&dy!==0)d=dy<0?'up':'down';
  else if(dy===0&&dx!==0)d=dx<0?'left':'right';
  else return toast('请选择一条已标出的射线，或使用方向键。',true);
 }else{
  if(!landmark&&tile&&(tile.kind==='fragile'||tile.kind==='trap'&&tile.armed)){
   if(!step){requestTravel(target,true);return}
   direction(step);return;
  }
  if(step&&!travelNeedsCaution()&&groundLootAt(target)){requestTravel(target);return}
  if(landmark||rerouting||state.secretClues?.some(cell=>same(cell,target))||!step){requestTravel(target);return}
  d=step;
 }
 direction(d, target);
}
$('tactics').addEventListener('click',event=>{
 const button=event.target.closest('button');
 if(!button||!canAct())return;
 if(button.hasAttribute('data-anchor-chain')){setInspecting(false);useItem('anchor_chain');return}
 cancelTravel();
 if(button.hasAttribute('data-stored-charge')){setInspecting(false);send('stored_charge');return}
 if(button.hasAttribute('data-guard-forecast')){showGuardForecast();return}
 if(button.hasAttribute('data-ground')){showGroundItems();return}
 send(button.hasAttribute('data-open-supply')?'open_supply':'unlock');
});
async function showGuardForecast(){
 aim=null;aimingItem=null;refreshPreview();setInspecting(false);renderControls();
 const dialog=$('guard-forecast-dialog'), results=$('guard-forecast-options'), version=state.version;
 results.textContent='正在试算…';
 openPanel(dialog.id);
 const options=[
  {action:'guard',label:'防'},
  {action:'charge',label:'攒'},
  ...[['left','左'],['up','上'],['down','下'],['right','右']].map(([direction,name])=>
   ({action:'move',direction,label:`向${name}一步`}))
 ];
 const previews=await Promise.allSettled(options.map(({action,direction})=>api('preview',{action,direction,version})));
 if(!dialog.open||state.version!==version)return;
 results.innerHTML=previews.map((result,index)=>{
  const {action,direction,label}=options[index];
  const value=result.value;
  if(!value)return `<div class="upgrade"><b>${label}</b><p>${esc(result.reason?.message||'暂时无法试算。')}</p></div>`;
  const damage=`预计受 ${value.damage} 伤`;
  const detail=value.stepOutcome==='fall'?'已知地面会坠落':
   value.stepOutcome==='blocked'?`预计留在原地 · ${damage}`:
   action==='guard'?`挡下 ${value.blocked} 伤 · ${damage}`:damage;
  return `<div class="upgrade"><b>${label}</b><p>${detail}</p>
   <button type="button" data-confirm-defense="${action}" ${direction?`data-move-direction="${direction}"`:''}>选择「${label}」</button></div>`;
 }).join('');
}
$('guard-forecast-options').addEventListener('click',event=>{
 const button=event.target.closest('[data-confirm-defense]');
 const action=button?.dataset.confirmDefense;
 if(!action||!canAct())return;
 $('guard-forecast-dialog').close();
 send(action,button.dataset.moveDirection??null);
});
// A step redraws the SVG and moves the camera. Keep the cell selected on press
// even if the original SVG node has been replaced by the time the tap ends.
for(const map of [$('board'),$('minimap')]){
 let press=null;
 const select=(target,touch=false)=>map.id==='minimap'&&$('map-dialog').open?previewMapRoute(target):mapClick(target,false,touch);
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
  if(Math.hypot(event.clientX-x,event.clientY-y)<12)select(target,event.pointerType==='touch');
 });
 map.addEventListener('click',event=>{
  if(event.detail!==0)return;
  const target=targetAt(event);
  if(target)select(target);
 });
 map.addEventListener('contextmenu',event=>{
  const target=targetAt(event);
  if(!target||!state)return;
  event.preventDefault();
  if(busy)return;
  cancelTravel();
  closeDialogs();
  examineCell(target,true);
 });
}
for(const list of [$('landmarks'),$('journal-landmark-list')]){
 list.addEventListener('click',event=>{
  const button=event.target.closest('[data-landmark]');
  if(!button||button.disabled||!state||state.result||state.talentChoice||state.choices.length)return;
  const target=button.dataset.landmark.split(',').map(Number);
  if(list.id==='landmarks'&&$('map-dialog').open){
   previewMapRoute(target,button.dataset.landmarkName);
   return;
  }
  if(aim||aimingItem){aim=null;aimingItem=null;refreshPreview();renderControls()}
  if(inspecting)setInspecting(false);
  $('journal-dialog').close();
  if(same(target,pos(state.player))&&!unopenedSupplyAt(target)&&hasGroundItems()){
   showGroundItems();
   return;
  }
  mapClick(target,true);
 });
}
$('journal-rune-list').addEventListener('click',event=>{
 const button=event.target.closest('[data-rune-route]');
 if(!button||!canAct())return;
 const rune=state.runeJournal[Number(button.dataset.runeRoute)];
 if(!rune)return;
 const waypoint=runeJournalWaypoint(rune);
 if(!waypoint.cell)return;
 aim=null;aimingItem=null;refreshPreview();setInspecting(false);
 $('journal-dialog').close();
 if(same(waypoint.cell,pos(state.player))){
  if(rune.depth===state.depth&&hasGroundItems())showGroundItems();
  else toast(waypoint.label);
  return;
 }
 requestTravel(waypoint.cell);
});
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
 if(!state||event.pointerType==='touch')return;
 const key=event.target.closest('[data-cell]')?.dataset.cell;
 if(!aimingItem){
  const next=!aim&&state.returning.some(wave=>wave.sidePaths?.[key])?key:null;
  if(next!==tideHover){tideHover=next;renderBoard()}
  return;
 }
 const previews=aimingItem==='anchor_chain'?state.anchorChain?.targets:state.smokeItems?.includes(aimingItem)?state.smokePreviews:state.lurePreviews;
 const next=previews?.[key]||(aimingItem!=='plant'&&aimingItem!=='anchor_chain'&&state.throwRedirects?.[key])?key:null;
 if(next===lureHover)return;
 lureHover=next;
 renderBoard();
});
$('board').addEventListener('pointerleave',()=>{
 if(tideHover){tideHover=null;renderBoard()}
 if(!lureHover)return;
 lureHover=null;
 if(aimingItem)renderBoard();
});
$('throw-lure').addEventListener('click',()=>{
 if(!aimingItem||!lureSelection||!canAct())return;
 if(aimingItem==='plant')send('plant',lureSelection,plantingSeed);
 else if(aimingItem==='anchor_chain')send('anchor_chain',lureSelection);
 else send('item',lureSelection,aimingItem);
});
$('inspect-cell').addEventListener('click',toggleInspection);
$('resume-travel').addEventListener('click',()=>{if(pausedTravel&&!$('resume-travel').disabled)requestTravel(pausedTravel)});
$('stop-travel').addEventListener('click',()=>{forgetTravel();toast('已停止自动行走。')});

document.querySelectorAll('[data-action]').forEach(b=>b.addEventListener('click',()=>chooseAction(b.dataset.action)));
$('cancel-aim').addEventListener('click',()=>{aim=null;aimingItem=null;refreshPreview();renderBoard();renderControls();toast('已取消瞄准。')});
$('exit').addEventListener('click',()=>send('exit'));
$('ascend').addEventListener('click',()=>send('ascend'));
function openPanel(id){
 cancelTravel();closeDialogs();$(id).showModal();
}
$('open-pack').addEventListener('click',()=>{
 if(!state)return;
 selectedBagItem=null;
 selectedBagSlot=-1;
 renderBag();
 $('bag-feedback').textContent='';
 openPanel('pack-dialog');
});
$('talent-dialog').addEventListener('cancel',event=>event.preventDefault());
$('talent-options').addEventListener('change',()=>{
 const limit=state.talentChoice.limit;
 const selected=document.querySelectorAll('#talent-options input:checked');
 document.querySelectorAll('#talent-options input').forEach(input=>{
  input.disabled=input.type==='checkbox'&&!input.checked&&selected.length>=limit;
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
 bindQuickItem(slot.key,event.target.value);
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
  selectedBagSlot=Number(item.dataset.bagSlot);
  document.querySelectorAll('#bag-slots [data-item]').forEach(slot=>
   slot.setAttribute('aria-pressed',String(slot===item)));
  renderBagItem();
  return;
 }
 const binding=event.target.closest('[data-bind-item]');
 if(binding&&canAct()&&state.inventory.some(item=>item.id===selectedBagItem&&!item.passive)){
  bindQuickItem(binding.dataset.bindItem,selectedBagItem);
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
 renderGrowthPreview();
 renderControls();
 $('growth-dialog').showModal();
});
$('confirm-growth').addEventListener('click',async()=>{
 if($('confirm-growth').disabled)return;
 if(await send('forge')){
  $('growth-dialog').close();
  $('growth-status').textContent=state.log[0];
  document.querySelector('[data-growth="forge"]')?.focus();
 }else $('growth-feedback').textContent=$('message').textContent;
});
$('ground-bag').addEventListener('click',()=>$('open-pack').click());
$('ground-pick-all').addEventListener('click',()=>{if(canAct())send('pickup',null,{all:true})});
$('ground-items').addEventListener('click',event=>{
 const button=event.target.closest('[data-pickup]');
 if(button&&!button.disabled&&canAct())send('pickup',null,{feature:button.dataset.pickup,item:button.dataset.groundItem});
});
$('ground-runes').addEventListener('click',event=>{
 const button=event.target.closest('[data-ground-rune]');
 if(button&&!button.disabled&&canAct())send('equip_ground_rune',null,button.dataset.groundRune);
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
function describeRouteSanity(forecast){
 if(!forecast)return '';
 const details=[`预计理智 ${forecast.start} → ${forecast.end}`];
 if(forecast.recovered)details.push(`沿途已知光点 +${forecast.recovered}`);
 if(forecast.corrosionAt)details.push(`第 ${forecast.corrosionAt} 步触及腐蚀`);
 else if(forecast.lowAt)details.push(`第 ${forecast.lowAt} 步理智偏低`);
 return ' · '+details.join(' · ');
}
async function previewMapRoute(target,name='所选地格'){
 if(!canAct()||!$('map-dialog').open)return;
 const current=same(target,pos(state.player));
 const interaction=current&&(unopenedSupplyAt(target)?'open_supply':hasGroundItems()?'ground':null);
 const selection={target,version:state.version,interaction};
 mapSelection=selection;
 const go=$('map-route-go');
 go.textContent=interaction==='open_supply'?'打开补给箱':interaction==='ground'?'查看脚下物品':'出发';
 $('map-route-preview').textContent=interaction?`${name} · 就在脚下`:`${name} · 正在寻路…`;
 renderControls();
 renderBoard();
 if(interaction)return;
 try{
  const response=await api('path',{target,version:selection.version,forecast:true});
  if(mapSelection!==selection||!$('map-dialog').open||response.version!==state.version)return;
  selection.path=response.path;
  $('map-route-preview').textContent=selection.path.length
   ?`${name} · ${travelNeedsCaution()?'谨慎行走，先走一步':selection.path.length+' 步'}${describeRouteSanity(response.sanityForecast)}`
   :current?'你已在所选地格。':'你已到达目标附近。';
 }catch(e){
  if(mapSelection!==selection||!$('map-dialog').open)return;
  $('map-route-preview').textContent=e.name==='AbortError'?'寻路超时，请重新点选目的地。':e.message;
 }
 renderControls();
 renderBoard();
}
$('toggle-map').addEventListener('click',()=>{
 if(!state||busy)return;
 if(travelTarget)setPausedTravel(travelTarget);
 mapSelection=null;
 $('map-route-preview').textContent='点选地格或路标，预览路线。';
 $('map-route-go').textContent='出发';
 $('map-dialog-content').append($('floor-map-card'));
 openPanel('map-dialog');
 renderControls();
 renderBoard();
});
$('map-dialog').addEventListener('close',()=>{
 if($('map-dialog').open)return;
 mapSelection=null;
 $('map-rail').prepend($('floor-map-card'));
 $('map-magnify').setAttribute('aria-pressed','false');
 $('map-magnify').textContent='放大';
 $('minimap').parentElement.classList.remove('magnified');
 renderBoard();
});
$('map-magnify').addEventListener('click',()=>{
 const viewport=$('minimap').parentElement;
 const magnified=viewport.classList.toggle('magnified');
 $('map-magnify').setAttribute('aria-pressed',String(magnified));
 $('map-magnify').textContent=magnified?'适应':'放大';
 if(!magnified){viewport.scrollTo(0,0);return}
 const [x,y]=mapSelection?.target??pos(state.player);
 const matrix=$('minimap').getScreenCTM();
 if(!matrix)return;
 const location=new DOMPoint(x*8+4,y*8+4).matrixTransform(matrix);
 const bounds=viewport.getBoundingClientRect();
 viewport.scrollBy(location.x-bounds.left-viewport.clientWidth/2,location.y-bounds.top-viewport.clientHeight/2);
});
$('map-route-go').addEventListener('click',()=>{
 if($('map-route-go').disabled||!mapSelection)return;
 const {target,interaction}=mapSelection;
 $('map-dialog').close();
 aim=null;aimingItem=null;
 refreshPreview();
 setInspecting(false);
 renderControls();
 if(interaction==='open_supply')send('open_supply');
 else if(interaction==='ground')showGroundItems();
 else requestTravel(target);
});
$('help').addEventListener('click',()=>openPanel('help-dialog'));
document.querySelectorAll('.close-dialog').forEach(b=>b.addEventListener('click',()=>b.closest('dialog').close()));
$('reward-dialog').addEventListener('cancel',e=>e.preventDefault());
$('skip-reward').addEventListener('click',()=>send('skip_reward'));
$('organize-for-supply').addEventListener('click',async()=>{
 if(state.choices[0]?.supply&&await send('skip_reward'))$('open-pack').click();
});
$('return-to-supply').addEventListener('click',()=>{
 if(canAct()&&unopenedSupplyAt(pos(state.player)))send('open_supply');
});
$('rewards').addEventListener('click',e=>{
 const button=e.target.closest('[data-supply]');
 if(button)send('choose',null,button.dataset.supply);
});
$('rewards').addEventListener('change',()=>{$('confirm-reward').disabled=busy||!$('rewards').querySelector('input:checked')});
$('confirm-reward').addEventListener('click',()=>{
 const selection=$('rewards').querySelector('input:checked');
 if(selection)send('choose',null,selection.value);
});
let startingFirstRun=false;
function renderClassPreview(){
 const selection=$('class-options').querySelector('input:checked');
 const hero=state.classes.find(entry=>entry.id===selection?.value);
 const panel=$('class-preview');
 panel.hidden=!hero?.preview;
 if(panel.hidden)return;
 const {range,cells,targets,returns,origin:previewOrigin}=hero.preview;
 panel.style.setProperty('--class-color',hero.color);
 const detail=returns?'下一拍飞回你行动后的位置。可以侧移改变回程。':
  hero.id==='lance'?'将敌人引到同一条线上，波可贯穿整排。':
  hero.id==='fan'?'覆盖周围八格。斜向行走可以避开正面的攻击。':
  '波止于第一个敌人。可以在射程内先拉开距离。';
 const board=Array.from({length:(range+1)*3},(_,i)=>{
  const cell=[i%(range+1),Math.floor(i/(range+1))];
  const origin=same(cell,previewOrigin), hit=targets.some(target=>same(target,cell));
  const beam=cells.some(target=>same(target,cell));
  return `<span class="class-demo-cell"${beam?' data-wave':''}${hit?' data-target':''}>${origin?art.portrait(hero.color):hit?'◆':beam?(returns?'⇄':'·'):''}</span>`;
 }).join('');
 panel.innerHTML=`<div class="class-preview-copy"><b>${esc(hero.name)} · 波 ${hero.preview.damage} 伤 · ${hero.id==='lance'?'射程无限':hero.id==='fan'?'周围八格':`射程 ${range} 格`}</b><p>${detail}</p></div>
  <div class="class-preview-art" aria-hidden="true"><div class="class-demo" style="--demo-columns:${range+1}">${board}</div><small>◆ 示例敌人</small></div>`;
}
function chooseClass(firstRun=false){
 if(!state)return;
 startingFirstRun=firstRun;
 $('restart-dialog').querySelector('.close-dialog').hidden=firstRun;
 $('class-note').textContent=firstRun?'职业决定本次冒险的波形。':'开始后会替换当前冒险进度。';
 $('class-options').innerHTML='<legend>初始职业</legend>'+state.classes.map(c=>`<label class="class-option">
 <input type="radio" name="hero-class" value="${c.id}" ${(state.heroClass||'straight')===c.id?'checked':''}>
 <span class="class-avatar" aria-hidden="true">${art.portrait(c.color)}</span>
 <span><b>${esc(c.name)}</b><small>${esc(c.description)}</small></span></label>`).join('');
 renderClassPreview();
 openPanel('restart-dialog');
}
$('class-options').addEventListener('change',renderClassPreview);
$('restart').addEventListener('click',()=>chooseClass());
$('restart-dialog').addEventListener('cancel',event=>{if(startingFirstRun)event.preventDefault()});
$('confirm-restart').addEventListener('click',()=>{
 const selected=document.querySelector('[name="hero-class"]:checked');
 if(selected)reset(startingFirstRun?state.seed:undefined,selected.value);
});
$('retry').addEventListener('click',()=>reset(state.seed,state.heroClass));
$('new-seed').addEventListener('click',()=>chooseClass());
const directionKeys={arrowup:'up',w:'up',arrowright:'right',d:'right',
 arrowdown:'down',s:'down',arrowleft:'left',a:'left'};
const actionKeys={'1':'charge','2':'wave','3':'guard','4':'heavy','5':'reflect',x:'search',r:'dodge'};
const WALK_START_DELAY=240, WALK_STEP_DELAY=110;
let heldWalk=null;

function stopHeldWalk(){
 clearTimeout(heldWalk?.timer);
 heldWalk=null;
}

function heldWalkThreat(){
 return state.pursuing||state.returning.some(wave=>wave.owner==='enemy');
}

async function walkHeldStep(walk,first){
 if(heldWalk!==walk)return;
 if(!canAct()||document.querySelector('dialog[open]')||aim||aimingItem||state.movementLocked){
  stopHeldWalk();
  return;
 }
 const [dx,dy]=moveDirs[walk.direction];
 const next=[state.player.x+dx,state.player.y+dy];
 const [x,y]=next;
 if(!first&&(heldWalkThreat()||unsafeTravelStep(next,true)||state.fireCells?.some(cell=>same(cell,next))||
     x<0||x>=state.width||y<0||y>=state.height)){
  stopHeldWalk();
  return;
 }
 const {depth}=state, hp=state.player.hp;
 const previousEnemies=visibleHostileIds();
 walk.step=direction(walk.direction);
 const moved=await walk.step;
 if(heldWalk!==walk)return;
 if(!moved||state.depth!==depth||state.player.hp<hp||!same(pos(state.player),next)||
   state.effects.some(fx=>['trap','revive'].includes(fx.kind))){
  stopHeldWalk();
  return;
 }
 if(heldWalkThreat()||discoveredHostile(previousEnemies)){
  stopHeldWalk();
  toast('遇敌 · 已停止连续行走。');
  return;
 }
 walk.timer=setTimeout(()=>walkHeldStep(walk,false),first?WALK_START_DELAY:WALK_STEP_DELAY);
}

async function startHeldWalk(key,heading){
 const previousStep=busy?heldWalk?.step:null;
 stopHeldWalk();
 if(!previousStep&&!canAct())return;
 if(aim||aimingItem||state.movementLocked||heldWalkThreat()){
  direction(heading);
  return;
 }
 const walk={key,direction:heading};
 heldWalk=walk;
 if(previousStep){
  const previousEnemies=visibleHostileIds();
  await previousStep;
  if(heldWalk!==walk)return;
  if(heldWalkThreat()||discoveredHostile(previousEnemies)){stopHeldWalk();return}
 }
 await walkHeldStep(walk,true);
}

document.addEventListener('keydown',event=>{
 if(event.ctrlKey||event.metaKey||event.altKey||event.isComposing||
    event.target.closest?.('input, textarea, select, [contenteditable]')||
    document.querySelector('dialog[open]'))return;
 const key=event.key.toLowerCase();
 const diagonals={Numpad7:'up-left',Numpad9:'up-right',Numpad1:'down-left',Numpad3:'down-right'};
 const heading=directionKeys[key]||(state?.heroClass==='fan'?diagonals[event.code]:null);
 if(heading){
  event.preventDefault();
  if(!event.repeat)startHeldWalk(key,heading);
  return;
 }
 if(event.repeat)return;
 stopHeldWalk();
 if(key==='escape'){
  setInspecting(false);
  forgetTravel();
  $('cancel-aim').click();
 }else if(key==='i'){
  event.preventDefault();
  toggleInspection();
 }else if(QUICK_ITEMS.some(slot=>slot.key===key)){
  event.preventDefault();
  useQuickItem(key);
 }else if(actionKeys[key]){
  event.preventDefault();
  chooseAction(actionKeys[key]);
 }else if(key==='?')$('help').click();
});
document.addEventListener('keyup',event=>{
 if(event.key.toLowerCase()===heldWalk?.key)stopHeldWalk();
});
document.addEventListener('pointerdown',stopHeldWalk,{capture:true});
window.addEventListener('blur',stopHeldWalk);
document.addEventListener('visibilitychange',()=>{
 if(document.hidden)stopHeldWalk();
});
matchMedia('(max-width: 680px)').addEventListener('change',()=>renderBoard());
api('state').then(s=>{if(!s.floorVersion||!s.depth||!s.mechanicsVersion||!s.lastFloor||!s.sanityTurnsPerPoint||s.growthVersion!==7)throw Error('服务仍为旧版，请重启 Python 服务。');state=s;busy=false;render();$('saved').textContent='● 进度已保存';if(!state.result&&!state.choices.length&&!state.talentChoice&&state.turn===0&&!state.heroClass){chooseClass(true);return}if(!state.result&&!state.choices.length&&!state.talentChoice&&state.turn===0){try{if(!localStorage.getItem('bobozan-floor-guide-v1')){$('help-dialog').showModal();localStorage.setItem('bobozan-floor-guide-v1','seen')}}catch{}}}).catch(e=>{toast(window.bobozanLocalApi||e.message==='服务仍为旧版，请重启 Python 服务。'?e.message:'无法连接地牢。请运行 python3 server.py 后刷新页面。',true);$('saved').textContent='连接失败';$('restart').disabled=true;document.querySelectorAll('[data-action],#exit').forEach(b=>b.disabled=true)});
