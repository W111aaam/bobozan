'use strict';

// Original pixel silhouettes on a 16×16 grid. The same sprites are used on
// the board and in the character panels.
const art = (() => {
 const ink='#191727', eye='#fff5cd';
 const palettes={
  charger:[ink,'#873f72','#d86498','#ffc1ae',eye],
  ram:[ink,'#8b4934','#d17a47','#ffca79',eye],
  shield:[ink,'#454067','#8277ab','#c5b9db',eye],
  escort:[ink,'#394b70','#658cb0','#c9dcbd',eye],
  twin:[ink,'#5e3c85','#a56bd3','#f4a8da',eye],
  boss:[ink,'#753d42','#c96660','#f8c87d',eye],
  breaker:[ink,'#655046','#ab6950','#ff9b51',eye],
  mirrorboss:[ink,'#374768','#668ab8','#a8f0e4',eye]
 };
 const sprites={
  hero:[
   '................','.....111111.....','....13333331....','...1333333221...',
   '..133344333221..','..133444333221..','..133133133221..','..133533533221..',
   '..133333333221..','..123331333221..','...1222222221...','...112222211....',
   '....11111111....','....111..111....','................','................'
  ],
  charger:[
   '.......44.......','.......33.......','......1331......','.....133331.....',
   '....13333331....','...1333333321...','..132555552331..','..132511152331..',
   '..132555552331..','...1323333231...','....12222221....','.....111111.....',
   '....14....41....','................','................','................'
  ],
  ram:[
   '...44......44...','..4431....1344..','..133311113331..','...1333333331...',
   '..133233332331..','..133153351331..','.13333333333331.','.13331111333321.',
   '.12314554133221.','.12214444122221.','..122111122221..','...1111111111...',
   '...12..12..12...','...11..11..11...','................','................'
  ],
  shield:[
   '......1111......','.....133331.....','....13333331....','....13444431....',
   '....13155131....','.....111111.....','...1222332221...','..124444444421..',
   '..124333333421..','..124334433421..','...1433443341...','...1433333341...',
   '....14444441....','.....111111.....','.....11..11.....','................'
  ],
  escort:[
   '..11....1111....','..141..133331...','..141.13333331..','..141.13444431..',
   '..141.13155131..','..141..111111...','..141122222221..','..1412333344421.',
   '..1412333343421.','..1412333344421.','..141122223431..','..11112222341...',
   '......111111....','......11..11....','................','................'
  ],
  twin:[
   '.....44..44.....','....14311341....','...1333333331...','..13343343331...',
   '..13313313321...','..13353353321...','...133333321....','....1222221.....',
   '...123343321....','..12334433221...','..12344333221...','...122222221....',
   '....1111111.....','...11.....11....','................','................'
  ],
  boss:[
   '..4....44....4..','..44...44...44..','..444444444444..','...143444341....',
   '..133333333331..','.13333333333331.','.13315555513331.','.13311333113331.',
   '.13333333333321.','.13333111333221.','.12333333332221.','..122222222221..',
   '...1111111111...','...11......11...','................','................'
  ],
  breaker:[
   '...111....111...','..1431....1341..','..143111111341..','.14333333333341.',
   '.14334444333341.','.14311551133341.','.14333333333341.','.14443333334441.',
   '.14243333334241.','.14443333334441.','.1122233222211..','...122222221....',
   '..11111111111...','..111....1111...','................','................'
  ],
  mirrorboss:[
   '.......44.......','......4334......','.....433334.....','....43333334....',
   '...4335113334...','..433155113334..','.43311155113334.','..433115511334..',
   '...433111334....','....4333334.....','...143333341....','..14332233341...',
   '...144444441....','.....11..11.....','................','................'
  ]
 };
 // Compact original silhouettes: center these 10×10 designs in the shared 16×16 frame.
 const regional = {
  slipsnake:['#416e39','#83bb55','#d5e68e',[
   '......11..','.....1331.','.....3511.','.....13...','.....13...','..11113...','1333331...','123111....','..1333331.','...111111.']],
  rushcrab:['#933c37','#d96849','#ffc475',[
   '11......11','141....141','1341..1431','.131..131.','..133331..','.13533531.','1323333231','.12222221.','..1.11.1..','.11....11.']],
  boneburst:['#696278','#c9bdad','#eee0b7',[
   '...1111...','..134431..','..151151..','...1331...','....11....','..133331..','.12133121.','.1.1221.1.','...1..1...','..11..11..']],
  splitcloud:['#694555','#bb7387','#f0afae',[
   '..11..11..','.13411341.','.151..151.','..1.11.1..','.1.1331.1.','1313551131','151.11.151','.1.11.1.1.','..134131..','..151151..']],
  drainbat:['#4a3b68','#896fc0','#de93d6',[
   '11......11','131....131','1331..1331','1331111331','.13533531.','..133331..','...1541...','....11....','..........','..........']],
  arcshaman:['#35666e','#57b4b6','#99eee0',[
   '...4....4.','..434..434','..131...1.','..1551..1.','...131..1.','..13331.1.','..1343311.','.13344311.','.1222221..','...1.1....']],
  nullmage:['#69386d','#b35aa5','#ffd38b',[
   '....11....','...1441...','..134431..','..135531..','..133331..','...1221...','..123321..','..132231..','.13222231.','.11111111.']],
  pulsemate:['#604055','#b17c65','#ebd08c',[
   '...1111...','...1331...','...1551...','.11.11.11.','1441331441','1341331431','.11233211.','..122221..','..11..11..','..11..11..']],
  blinkgolem:['#484b70','#748db8','#a1f1e7',[
   '...1111...','...1551...','.11111111.','1331441331','1331441331','1221441221','.11333311.','..111111..','..133331..','..11..11..']],
  siegeeye:['#813855','#d45c72','#ffc485',[
   '...1441...','..143341..','.14333341.','1433553341','1435115341','1433553341','.14333341.','..143341..','...1441...','....11....']],
  barbscorp:['#623853','#ad695b','#ebad70',[
   '.....1441.','........13','.....11131','.11..1331.','14311121..','134133331.','.11533531.','..1322331.','...111111.','..11.1..1.']],
  leapripper:['#78434c','#c75d58','#f0a378',[
   '..4....4..','.141..141.','.13311331.','..153351..','.11333311.','1413333141','1.122221.1','..133331..','...1..1...','..11..11..']]
 };
 Object.assign(regional, {
 "sparkthief":[
  "#54465e",
  "#9c6690",
  "#f4bf75",
  [
   "...1111...",
   "..134431..",
   "..135531..",
   "...1331...",
   "..123321..",
   ".1323321..",
   ".12222144.",
   "..1221444.",
   "..11..111.",
   ".11..11..."
  ]
 ],
 "bonesummoner":[
  "#454358",
  "#897593",
  "#d4ed9d",
  [
   "..4114....",
   "..1311..4.",
   "..1511.434",
   "...111..1.",
   "..13331.1.",
   ".13233111.",
   ".13223211.",
   ".12222211.",
   "..122211..",
   ".11111111."
  ]
 ],
 "magnetguard":[
  "#3d5268",
  "#628fb5",
  "#ffa379",
  [
   "..1111....",
   "..1341.4.4",
   "..1551.434",
   "...11...1.",
   ".13333111.",
   "133443311.",
   "122442211.",
   ".122221...",
   "..11.11...",
   "..11.11..."
  ]
 ],
 "webspinner":[
  "#3c374b",
  "#785d82",
  "#d499c8",
  [
   ".1......1.",
   "..1....1..",
   "1..1111..1",
   ".11344311.",
   "..135531..",
   "1113333111",
   "..133331..",
   ".11.11.11.",
   "1........1",
   ".........."
  ]
 ],
 "elementcore":[
  "#73436c",
  "#bb6587",
  "#ffd17a",
  [
   "....44....",
   "...4334...",
   "..434434..",
   ".43355334.",
   ".43355334.",
   "..434434..",
   "...4334...",
   "....44....",
   "..4....4..",
   ".........."
  ]
 ],
 "armedidol":[
  "#50525d",
  "#999b9f",
  "#8bf0d4",
  [
   "...1111...",
   "...1331.4.",
   "...1551.4.",
   ".111111.4.",
   "1333331141",
   "132442311.",
   ".1233211..",
   "..11111...",
   "..13231...",
   ".1111111.."
  ]
 ],
 "mirrorwraith":[
  "#484169",
  "#8275ba",
  "#aef2ef",
  [
   "...4444...",
   "..433334..",
   ".43355334.",
   ".43333334.",
   "..433334..",
   "..133331..",
   ".1333321..",
   "1333321.1.",
   ".11111.11.",
   ".........."
  ]
 ],
 "chestmimic":[
  "#6f3f44",
  "#af7155",
  "#ffe5a0",
  [
   "..111111..",
   ".14444441.",
   ".13443331.",
   "1111111111",
   "1454545411",
   "1411111411",
   "1454545411",
   ".12222221.",
   "..111111..",
   "..11..11.."
  ]
 ],
 "broodnest":[
  "#603b4f",
  "#a95169",
  "#f4aa9a",
  [
   "....44....",
   "...4334...",
   "..433334..",
   ".43355334.",
   "1433553341",
   "1433333341",
   "1434443341",
   ".14333341.",
   ".12222221.",
   "1111111111"
  ]
 ],
 "canalfish":[
  "#2b5974",
  "#4f9dba",
  "#aae9f3",
  [
   "....4.....",
   "...434....",
   "..1131....",
   "11333311..",
   "1433355311",
   "1333333311",
   "11233311..",
   "..1111....",
   "....1.....",
   ".........."
  ]
 ],
 "bonepuppet":[
  "#645b67",
  "#b7aeb1",
  "#e4d6a5",
  [
   "...1111...",
   "...1551...",
   "....11....",
   "..133331..",
   "..113311..",
   ".1.1221.1.",
   "...1111...",
   "...1..1...",
   "..11..11..",
   ".........."
  ]
 ],
 "broodling":[
  "#5e3f53",
  "#a96165",
  "#ee9f87",
  [
   "..4....4..",
   "..14..41..",
   "...1331...",
   "..135531..",
   "..133331..",
   "...1221...",
   "..11..11..",
   "..........",
   "..........",
   ".........."
  ]
 ]
});
 for(const [id,[shade,base,light,rows]] of Object.entries(regional)){
  palettes[id]=[ink,shade,base,light,eye];
  sprites[id]=['................','................',...rows.map(row=>'...'+row+'...'),
   '................','................','................','................'];
 }
 const items={
  chart:['..........','..111111..','.14444441.','.14333441.','..143341..','..144341..','..143441..','.14444441.','..111111..','..........'],
  chest:['..........','..111111..','.14444441.','.14333441.','.11111111.','.12242221.','.12222221.','.11111111.','..........'],
  shrine:['..........','....44....','...4344...','...4334...','..111111..','.14333341.','.14444441.','..111111..','..........'],
  key:['..........','...1111...','..144441..','..141141..','...1441...','....41....','....444...','....41....','..........'],
  kit:['..........','...1111...','...1441...','..133331..','..134431..','..134431..','..133331..','...1111...','..........'],
  lure_cache:['..........','....41....','...4331...','..433331..','..433331..','...4331...','....11....','..........','..........'],
  wonder:['..........','....4.....','...434....','.4433344..','..43334...','...434....','....4.....','..........','..........'],
  stairs:['..........','....1111..','....1441..','...14431..','..144331..','.1443331..','.1443331..','.1111111..','..........'],
  high_grass:['....4.....','4...4....4','34..34..43','334.343.33','2334344333','2333333332','2232332322','.22222222.','..111111..'],
  grass:['..........','..........','..........','..........','..........','..3...3...','.232.232..','.22222222.','..111111..'],
  dew:['..........','..........','....4.....','...434....','..43334...','..43334...','...444....','..........','..........'],
  lock:['..........','...1111...','..14..41..','..144441..','..144441..','..144441..','...1111...','..........','..........']
 };
 const props=[ink,'#865333','#e5b760','#ffda87',eye];
 const itemColors={high_grass:[ink,'#365940','#6c9e53','#a3cb69',eye],
  grass:[ink,'#3d5a41','#73915b','#9ba96b',eye],dew:[ink,'#387a8d','#87d7ef','#dcfcff',eye],
  shrine:[ink,'#49657c','#75bed1','#b5f4ee',eye],kit:[ink,'#81425a','#ce6480','#ffc7bd',eye],
  wonder:[ink,'#685082','#bd8bef','#f7d0ff',eye],lure_cache:[ink,'#4e7767','#8dc7a3','#d7efd6',eye]};
 const cache=new Map();
 function pixels(rows,colors){
  return colors.map((color,i)=>{
   const key=String(i+1);let d='';
   rows.forEach((row,y)=>{
    for(let x=0;x<row.length;x++)if(row[x]===key){
     const start=x;while(row[x+1]===key)x++;
     d+=`M${start} ${y}h${x-start+1}v1H${start}z`;
    }
   });
   return d?`<path fill="${color}" d="${d}"/>`:'';
  }).join('');
 }
 function sprite(kind,color){
  const key=kind==='hero'?'hero'+color:kind;
  if(!cache.has(key))cache.set(key,pixels(sprites[kind]||sprites.charger,
   kind==='hero'?[ink,'#465e67',color,'#e6ffe5',eye]:palettes[kind]||palettes.charger));
  return cache.get(key);
 }
 function portrait(color){
  return `<svg viewBox="0 0 16 16" shape-rendering="crispEdges" aria-hidden="true">${sprite('hero',color)}</svg>`;
 }
 function actor(x,y,kind,id,color,enemy){
  if(enemy?.disguised)return `<g class="mimic-breath" pointer-events="none">${prop('chest',x,y)}</g>`;
  const hero=kind==='hero', boss=['boss','breaker','mirrorboss'].includes(kind);
  const hp=enemy?Math.min(1,enemy.hp/(enemy.maxHp||enemy.hp)):0;
  return `<g transform="translate(${x*60},${y*60})" pointer-events="none" class="map-actor ${hero?'player-sprite':'enemy-sprite'}">
   <ellipse cx="30" cy="49" rx="22" ry="8" fill="#100f1d" opacity=".8"/>
   ${hero?`<path d="M8 44v9h10m24 0h10v-9" stroke="${color}" fill="none" stroke-width="2"/>`:''}
   <g transform="translate(${boss?1:4},${boss?2:5}) scale(${boss?3.6:3.25})" shape-rendering="crispEdges">${sprite(kind,color)}</g>
   ${enemy?`<path d="M13 54h34" stroke="#1a1321" stroke-width="6"/><path d="M13 54h${34*hp}" stroke="#e88576" stroke-width="3"/>
   <text x="8" y="14" fill="#ffe3aa" font-size="10" font-weight="800">${id+1}</text>
   ${enemy.stolen?'<circle cx="44" cy="18" r="5" fill="#86eeea" stroke="#eefcff"/>':''}
   ${enemy.element?`<circle cx="46" cy="15" r="5" fill="${{fire:'#fa855f',frost:'#a5e8ff',spark:'#f5d374'}[enemy.element]}"/>`:''}
   ${enemy.intent.action==='notice'?'<text x="44" y="15" fill="#ffde8a" font-size="20" font-weight="900">!</text>':''}`:''}</g>`;
 }
 function prop(kind,x,y,used=false){
  const key=({cache:'chest',materials:'chest',supply_choice:'chest',dry_spring:'shrine',recall:'chart',terror:'chart',ankh:'wonder',smoke:'lure_cache',echo_smoke:'lure_cache',dropped_item:'lure_cache',grass_seed:'lure_cache',sun_seed:'dew',stolen_energy:'dew',rune_shard:'wonder'})[kind]||kind;
  if(!items[key])return '';
  if(!cache.has(key))cache.set(key,pixels(items[key],itemColors[key]||props));
  return `<g transform="translate(${x*60+9},${y*60+12}) scale(4.2)" opacity="${used||kind==='dry_spring'||kind==='materials'?.4:1}" pointer-events="none" shape-rendering="crispEdges">${cache.get(key)}</g>`;
 }
 function doorway(x,y,color,vertical,open,locked=false,front=true){
  if(vertical&&!front){
   return `<g transform="translate(${x*60},${y*60})" pointer-events="none" shape-rendering="crispEdges">
    <path d="M0 6h13v17H0zm47 0h13v17H47z" fill="${color}"/>
    <path d="M0 7h13m34 0h13" stroke="#e5d9bf" stroke-width="2" opacity=".4"/>
    <path d="M9 25V8h6V4h30v4h6v17h-7V12H16v13z" fill="${color}"/>
    <path d="M16 12h28v13H16z" fill="${open?'#272733':'#8d6244'}"/>
    ${open?'':'<path d="M19 17h22v3H19z" fill="#c6a476"/><path d="M35 20h4v4h-4z" fill="#f2ce87"/>'}
    ${locked?`<g transform="translate(12,-10) scale(.6)">${prop('lock',0,0)}</g>`:''}</g>`;
  }
  const gate=vertical
   ? `<path d="M0 0h60v25H0zM0 25h12v31H0zM48 25h12v31H48z" fill="${color}"/>
      <path d="M0 3h60M0 22h60" stroke="#e5d9bf" opacity=".3" stroke-width="3"/>
      <path d="M0 25h12v31H0zM48 25h12v31H48z" fill="#171522" opacity=".45"/>
      <path d="M8 56V30h5v-8h8v-6h18v6h8v8h5v26h-8V32h-6v-7H22v7h-6v24z" fill="${color}"/>
      <path d="M12 50V30h6v-8h8v-4h10v4h8v8h4v20" fill="none" stroke="#dfd5b5" opacity=".48" stroke-width="2"/>`
   : `<path d="M0 0h60v12H0zM0 48h60v12H0z" fill="${color}"/>
      <path d="M5 0v60m47-60v60" stroke="#181622" opacity=".8" stroke-width="3"/>
      <path d="M8 13h44M8 51h44" stroke="#ddd0b1" opacity=".42" stroke-width="3"/>
      <path d="M10 10h40v8H10zm0 32h40v8H10z" fill="${color}"/>`;
  const opening=vertical
   ? `<path d="M16 31h6v-6h16v6h6v25H16z" fill="${open?'#23232c':'#68422e'}"/>
      ${open?'<path d="M16 32h5v22h-5zm23 0h5v22h-5z" fill="#a27851"/>':
      '<path d="M21 32h5v22h-5zm9-6h5v28h-5z" fill="#9e754d"/><path d="M16 34h28v4H16zm0 13h28v4H16z" fill="#c6a476"/><path d="M36 39h5v6h-5z" fill="#f2ce87"/>'}`
   : `<path d="M10 18h40v24H10z" fill="${open?'#262733':'#714832'}"/>
      ${open?'<path d="M10 18h39v4H10z" fill="#a27851"/>':
      '<path d="M12 23h36v4H12zm0 10h36v4H12z" fill="#aa7a4b"/><path d="M17 18h4v24h-4zm22 0h4v24h-4z" fill="#c6a476"/><path d="M28 28h6v5h-6z" fill="#f2ce87"/>'}`;
  return `<g transform="translate(${x*60},${y*60})" pointer-events="none" shape-rendering="crispEdges">
   ${gate}${opening}${locked?prop('lock',0,0):''}</g>`;
 }
 function stoneWall(x,y,color,{north,east,south,west}){
  // Open neighbors expose the bevel; the south side alone shows tall masonry.
  const left=west?7:0,right=east?53:60,top=north?6:0;
  const cap=south?25:north?19:60, bottom=south?57:60;
  const noise=(x*47+y*73+x*y*3)%97;
  const seam=14+noise%21, lower=42-noise%13;
  const width=right-left;
  const brickFace=south?`
   <path d="M${left} ${cap}h${width}v${bottom-cap}H${left}z" fill="${color}"/>
   <path d="M${left} ${cap}h${width}v${bottom-cap}H${left}z" fill="#191524" opacity=".47"/>
   <path d="M${left} 42H${right}M${seam} 27v15m${lower-seam} 0v15" stroke="#171623" stroke-width="2"/>
   <path d="M${left+1} 44H${right-1}M${left+1} 28H${right-1}" stroke="#e2d4b9" opacity=".13" stroke-width="2"/>
   <path d="M${left} 55H${right}" stroke="#161421" stroke-width="4"/>`:'';
  const edge=(west||east||north||south);
  return `<g transform="translate(${x*60},${y*60})" shape-rendering="crispEdges" pointer-events="none">
   <path d="M0 0h60v60H0z" fill="#1b1b28"/>
   ${brickFace}
   <path d="M${left} ${top}H${right}V${cap}H${left}z" fill="${color}" opacity="${edge?'.93':'.54'}"/>
   <path d="M${left} ${top+1}H${right}" stroke="#e2dac4" stroke-width="2" opacity="${north?'.40':'.10'}"/>
   ${cap>35?`<path d="M${left} 30H${right}m${seam-right} -30v30m${lower-seam} 0v30" stroke="#1c1926" opacity=".52" stroke-width="2"/>`:
     `<path d="M${seam} ${top}V${cap}" stroke="#231f2c" stroke-width="2" opacity=".65"/>`}
   ${south||north?`<path d="M${left} ${cap-3}H${right}" stroke="#efe0bf" opacity=".34" stroke-width="2"/>
   <path d="M${left} ${cap}H${right}" stroke="#191723" stroke-width="3"/>`:''}
   ${west?`<path d="M${left+1} ${top}V${bottom}" stroke="#d7cbb1" opacity=".26" stroke-width="2"/>`:''}
   ${east?`<path d="M${right-1} ${top}V${bottom}" stroke="#171522" opacity=".75" stroke-width="3"/>`:''}
   ${edge&&noise<45?`<path d="M${seam+3} ${top+5}h7v2h-7z" fill="#e1d2b0" opacity=".24"/>`:''}
  </g>`;
 }
 function ground(x,y,floorColor,shade){
  const X=x*60,Y=y*60,n=(x*47+y*73+x*y*3)%97;
  return `<rect class="floor" x="${X}" y="${Y}" width="60" height="60" fill="${floorColor}"/>
   <g transform="translate(${X},${Y})" pointer-events="none" shape-rendering="crispEdges">
    <path d="M0 0h60v60H0z" fill="${n%4===0?'#ffffff':'#080612'}" opacity=".05"/>
    <path d="M3 3h54v54H3z" fill="none" stroke="#dfcdaf" opacity=".08"/>
    <path d="M${n%33+6} ${n%28+8}h9v3h-9zM${n%17+15} ${n%11+35}h4v4h-4z" fill="#e9d2a5" opacity=".15"/>
    ${n%9===0?'<path d="M9 52h12v-4h-5v-4h-4v4H9z" fill="#8ca96d" opacity=".42"/>':''}
    <path d="${shade.north?'M0 0h60v8H0z':''}${shade.west?'M0 0h4v60H0z':''}${shade.east?'M56 0h4v60h-4z':''}" fill="#10121b" opacity=".30"/>
   </g>`;
 }
 function effects(fx,color){
  const labels={
   damage:[28,12,19,'#ffb29e','−'+fx.amount],
   blocked:[42,22,13,'#a8ddfc','挡 '+fx.amount],
   healed:[17,22,14,'#bce887','+'+fx.amount],
   cured:[42,38,12,'#bce887','解毒']
  };
  if(labels[fx.kind]){
   const [dx,dy,size,tint,label]=labels[fx.kind];
   return fx.cells.map(([x,y])=>`<g transform="translate(${x*60+dx},${y*60+dy})"
    pointer-events="none" aria-hidden="true"><text class="hit-fx" text-anchor="middle" font-size="${size}"
    font-weight="900" stroke="#191321" stroke-width="3" paint-order="stroke" fill="${tint}">
    ${label}</text></g>`).join('');
  }
  const palette={wave:color,return:'#b5a2fb',laser:'#ff9479',enemy:'#ff8d75',guard:'#a1d7fc',blink:'#88eff2',burn:'#ffab5a',impact:'#f2c985',grass:'#acd46a',bones:'#ede2c8',web:'#d9c3e8',ice:'#9cecff',electric:'#9cecff',steam:'#c8e1e7',thaw:'#c8e1e7',hook:'#fcce83',poison:'#b5e86c',trap:'#edb481',sound:'#ffdf91',smoke:'#b3c2de',revive:'#f7d574',roots:'#b6cc78',split:'#e5a3d6'};
  const tint=palette[fx.kind]||'#eaa781';
  const beam=['wave','return','laser'].includes(fx.kind);
  if(beam){
   const cells=fx.origin?[fx.origin,...fx.cells]:fx.cells;
   const parts=[];let d='';
   if(fx.spread&&fx.origin){
    const [x,y]=fx.origin;
    d=fx.cells.map(([a,b])=>`M${x*60+30} ${y*60+30}L${a*60+30} ${b*60+30}`).join('');
   }
   for(const [i,[x,y]] of cells.entries()){
    const prev=cells[i-1];
    const near=prev&&Math.abs(x-prev[0])+Math.abs(y-prev[1])===1;
    if(!fx.spread||!fx.origin)d+=`${near?'L':'M'}${x*60+30} ${y*60+30}`;
    if(i>0||!fx.origin)parts.push(`<path d="M${x*60+26} ${y*60+26}h8v8h-8z" fill="#fff6d4"/>`);
   }
   return `<g class="fx beam-fx" pointer-events="none"><path d="${d}" stroke="${tint}" stroke-width="21" opacity=".22" fill="none"/><path d="${d}" stroke="${tint}" stroke-width="10" fill="none"/><path d="${d}" stroke="#fff9e1" stroke-width="3" fill="none"/>${parts.join('')}</g>`;
  }
  return fx.cells.map(([x,y])=>`<g transform="translate(${x*60+30},${y*60+30})" pointer-events="none"><g class="fx pulse-fx" fill="none" stroke="${tint}" stroke-width="4"><path d="M-21 -12l9-9h24l9 9v24l-9 9h-24l-9-9z"/><path d="M-7 0h14m-7-7v14"/></g></g>`).join('');
 }
 return {actor,portrait,prop,ground,stoneWall,effects,doorway};
})();
