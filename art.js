'use strict';

// Original pixel silhouettes shared by the board and the character panels.
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
 const detailedSprites={
  hero:[
   '.........111111.........','.......1134444311.......','......134444333231......',
   '.....13433333332231.....','....1343311113322231....','....1431122221132231....',
   '...143123444432132231...','...143134777743132231...','...143137177173132231...',
   '...133137577573132231...','....1331266762112231....','.....11234332221111.....',
   '......123411322311......','.....123313333123311....','.....1221134331136511...',
   '....112111333211366651..','....125112332211566471..','.....1112222221226551...',
   '.......122222211611.....','.......112.2111.........',
  ],
  charger:[
   '...........11...........','..........1441..........','...........41...........',
   '..........1331..........','........11333311........','......113444333211......',
   '.....13443333233321.....','....1343333333332221....','...134333111133322221...',
   '...143331555513332221...','...143315544551332221...','...143315411451332221...',
   '...133315544551322221...','....1333155551332221....','.....13331111332221.....',
   '......123333332211......','.......112222111........','......1131.1131.........',
  ],
  ram:[
   '...441............144...','..4441............1444..','..4431.111111111..1344..',
   '...44314333333231.134...','....1413433333221141....','....134433333322221.....',
   '...13433333333332221....','..1343351133511332221...','..1433355133551332221...',
   '.134333333333333322221..','.133331111111333322221..','.133314444444133322221..',
   '..1331445444413322221...','..1231444144413222221...','...12211111112222221....',
   '....112222222222111.....','.....131113111321.......','.....111..111.111.......',
  ],
  boss:[
   '..44................44..','..434..............434..','...434..44....44..434...',
   '...433143411114341334...','....1433334334333341....','...143344333333443341...',
   '..14334333333333343321..','..14343331111113333221..','.1343333155555513332221.',
   '.1343331555445551332221.','.1333331541111451333221.','.1333331555445551333221.',
   '.1233333155555513333221.','..12333331111113332221..','..12343333333333432221..',
   '...123433322223343221...','...112223333333222111...','....1311111111113321....',
   '.....111........111.....',
  ],
 };
 for(const [kind,rows] of Object.entries(detailedSprites)){
  sprites[kind]=[...rows,...Array(24-rows.length).fill('........................')];
 }
 const items={
  chart:['..........','..111111..','.14444441.','.14333441.','..143341..','..144341..','..143441..','.14444441.','..111111..','..........'],
  chest:['..........','..111111..','.14533451.','.14533351.','.44455444.','.12545251.','.12555251.','.22522522.','..111111..','..........'],
  open_chest:['.11111111.','.14533451.','.14533351.','.12222221.','1444444441','1411111141','1444444441','1255525521','1222222221','.11111111.'],
  shrine:['..........','....44....','...4344...','...4334...','..111111..','.14333341.','.14444441.','..111111..','..........'],
  dry_spring:['..........','..144441..','..142241..','.14222241.','1444444441','1433333341','.13444331.','...1441...','..111111..','..........'],
  light_wisp:['.....1....','....131...','...1341...','..13421...','..1441....','..134321..','...1331...','....11..3.','..3.......','..........'],
  light_soul:['....11....','...1441...','...1431...','.11344311.','1444444441','.11344311.','...1431...','...1441...','....11....','..........'],
  light_radiant:['3...44...3','.3..44..3.','...1111...','..143341..','4413443144','4413443144','..143341..','...1111...','.3..44..3.','3...44...3'],
  key:['..........','...1111...','..144441..','..141141..','...1441...','....41....','....444...','....41....','..........'],
  kit:['..........','...1111...','...1441...','..133331..','..134431..','..134431..','..133331..','...1111...','..........'],
  lure_cache:['......55..','...61...5.','...661....','...141..5.','..14321...','..14321...','.1443321..','.1332221..','..11211...','....1.....'],
  wonder:['..........','....4.....','...434....','.4433344..','..43334...','...434....','....4.....','..........','..........'],
  stairs:['..........','....1111..','....1441..','...14431..','..144331..','.1443331..','.1443331..','.1111111..','..........'],
  up_stairs:['..........','....44....','...4444...','..441144..','....44....','....44....','..111111..','.14444441.','.11111111.','..........'],
  high_grass:['......4...','4..4..4...','34.34.3..4','33.33.3343','2342334333','.234333343','.23232332.','..2222222.','..111111..'],
  grass:['..........','..........','..........','..........','..........','..3...3...','.232.232..','.22222222.','..111111..'],
  dew:['..........','..........','....4.....','...434....','..43334...','..43334...','...444....','..........','..........'],
  smoke:['..........','...111....','...1441...','...111....','..12221...','.1234321..','.1233321..','..11111...','..........'],
  seed:['..........','..........','.....4....','....441...','...4331...','..43321...','..3321....','...11.....','..........'],
  ankh:['..........','....44....','...4114...','...4114...','....44....','..444444..','....44....','....44....','..........'],
  lock:['..........','...1111...','..14..41..','..144441..','..144441..','..144441..','...1111...','..........','..........']
 };
 const props=[ink,'#865333','#e5b760','#ffda87',eye];
 const itemColors={chest:[ink,'#704a44','#a87351','#d1a05f','#f4d795'],
  open_chest:[ink,'#704a44','#a87351','#d1a05f','#f4d795'],
  high_grass:[ink,'#2d5147','#699356','#b4ce75',eye],
  grass:[ink,'#3d5a41','#73915b','#9ba96b',eye],dew:[ink,'#387a8d','#87d7ef','#dcfcff',eye],
  shrine:[ink,'#49657c','#75bed1','#b5f4ee',eye],dry_spring:[ink,'#49403e','#88776a','#bbaa8b',eye],
  light_wisp:[ink,'#497c9d','#8fe5eb','#e2ffff'],light_soul:[ink,'#96703e','#edc665','#fff3b4'],
  light_radiant:[ink,'#925275','#f297b7','#ffe0dd'],up_stairs:[ink,'#5f684f','#8f9d68','#c7dfa4'],kit:[ink,'#81425a','#ce6480','#ffc7bd',eye],
  wonder:[ink,'#685082','#bd8bef','#f7d0ff',eye],lure_cache:[ink,'#907044','#d19b51','#ffe0a0','#f6c878','#c46a64']};
 const inventorySprites={
  heal:['kit'],lure:['lure_cache'],ankh:['ankh',[ink,'#805e42','#bd955f','#ffe0a0']],
  smoke:['smoke',[ink,'#536874','#91a9b4','#d9f1ef']],
  echo_smoke:['smoke',[ink,'#6d527d','#a67cbb','#edcbff']],
  frost_smoke:['smoke',[ink,'#366e87','#6ebcdb','#d4f5ff']],
  grass_seed:['seed',[ink,'#4e763b','#8abd62','#c7f386']],
  sun_seed:['seed',[ink,'#8f6439','#df974d','#ffe684']],
  chart:['chart'],recall:['chart',[ink,'#53718a','#94c1d5','#d5eef5']],
  terror:['chart',[ink,'#8a484e','#d98f89','#ffc0a7']]
 };
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
   kind==='hero'?[ink,'#34475c',color,'#e6f7d8','#8eb1bb','#cb8d54','#ead4a7']:palettes[kind]||palettes.charger));
  return cache.get(key);
 }
 function spriteSize(kind){return sprites[kind]?.length??16}
 function portrait(color){
  return `<svg viewBox="0 0 24 24" shape-rendering="crispEdges" aria-hidden="true">${sprite('hero',color)}</svg>`;
 }
 function enemyPortrait(enemy){
  if(enemy.disguised)return `<svg viewBox="0 0 60 60" shape-rendering="crispEdges" aria-hidden="true">${prop('chest',0,0)}</svg>`;
  const size=spriteSize(enemy.kind);
  return `<svg viewBox="0 0 ${size} ${size}" shape-rendering="crispEdges" aria-hidden="true">${sprite(enemy.kind)}</svg>`;
 }
 const uiIcons={
  heart:[['.11.11.','1221221','1233221','1222221','.12221.','..121..','...1...'],['#422733','#cf605a','#f6a181']],
  charge:[[
   '.....11.....','....1321....','....1431....','...144321...','...143321...',
   '..14433321..','.1444333221.','..14433321..','...143221...','...132221...',
   '....1221....','.....11.....',
  ],['#203046','#438691','#79c6c2','#e6ffd8']],
  wave:[[
   '.......1111...','........1331..','.........1441.','..3......13441',
   '...11111134441','.1123333344441','12334444444441','.1123333344441',
   '...11111134441','..3......13441','.........1441.','........1331..',
   '.......1111...',
  ],['#20313f','#4b86a9','#86d7e8','#e9fff2']],
  heavy:[[
   '........111.','.......13441','.....113441.','...1134441..','..13444411..',
   '.1344421.111','134421113441','14421134441.','1211344421..','.13444211...',
   '.144421.....','..111.......',
  ],['#302042','#7d59a9','#b28ae8','#f4ddff']],
  guard:[[
   '..11111111..','.1244444321.','.1442332441.','.1443342441.','.1444444441.',
   '.1334444431.','..13444431..','..12344321..','...123321...','....1221....',
   '.....11.....','............',
  ],['#273747','#5289a7','#83c4d3','#e2f0ed']],
  crest:[[
   '............','11..1111..11','121133331121','123344443321','..13444431..',
   '..14411441..','..14144141..','..14422441..','...144441...','....3434....',
   '....1111....','............',
  ],['#26202d','#8a7373','#ba9b84','#e5ccb0']],
  bag:[['..111..','.13231.','1233321','1322231','1333331','1233321','.11111.'],['#503b30','#a5794c','#deae68']],
  book:[['.......','1111111','1331331','1321321','1331331','1221221','1111111'],['#564a38','#aba27d','#ece1b3']],
  inspect:[['.111...','12321..','13231..','12321..','.1111..','....221','.....21'],['#504a43','#ad8c62','#ede0aa']],
  search:[['..111..','.13231.','1322231','1231321','1322231','.13231.','..111..'],['#53544d','#99b7a0','#dfdcb0']],
  map:[['..11111','1122321','1322321','1233221','1232221','122221.','11111..'],['#50453c','#a4a777','#e0c997']],
 };
 const waveSprites={
  impact:{width:30,height:16,markup:`
   <path fill="#2465b7" d="M17 0h6v1h3v1h2v2h1v2h1v4h-1v2h-1v2h-2v1h-3v1h-6v-1h4v-1h2v-2h-9v-1H9v-1H4V9H0V7h4V6h5V5h5V4h9V2h-2V1h-4z"/>
   <path fill="#39b3e5" d="M20 1h4v1h3v2h1v2h1v4h-1v2h-1v2h-3v1h-4v-1h3v-2h2v-1H14v-1H8V9H4V8H2V7h6V6h6V5h11V4h-2V2h-3z"/>
   <path fill="#8cf3ff" d="M22 2h3v1h2v2h1v6h-1v2h-2v1h-3v-1h2v-2h1v-1h-9V9H9V8H5V7h9V6h11V5h-1V3h-2z"/>
   <path fill="#eaffff" d="M25 4h2v2h1v4h-1v2h-2v-1h1V9H18V8h-6V7h14V5h-1z"/>
   <path fill="#9fefff" d="M10 3h1v1h-1zm3 9h1v1h-1zm4 2h1v1h-1z"/>
  `},
  reflect:{width:14,height:18,markup:`
   <path fill="#346eaf" d="M1 0h5v1h3v2h2v2h1v2h1v4h-1v2h-1v2H9v2H6v1H1v-2h2v-2h2v-2h1V6H5V4H3V2H1z"/>
   <path fill="#8fd2f4" d="M1 0h4v1h3v2h2v2h1v2h1v4h-1v2h-1v2H8v2H5v1H1v-1h2v-2h2v-2h2V5H5V3H3V1H1z"/>
   <path fill="#56a8e3" d="M3 0h2v1h2v2h2v2h1v2h1v4h-1v2H9v2H7v2H5v1H3v-1h2v-2h2v-2h1v-2h1V7H8V5H7V3H5V1H3z"/>
   <path fill="#c4efff" d="M2 0h1v1H2zm4 4h1v2H6zm1 3h2v4H7zm-1 5h1v2H6zm-4 5h1v1H2z"/>
  `},
 };
 function uiIcon(name){
  if(waveSprites[name]){
   const {width,height,markup}=waveSprites[name];
   return `<svg viewBox="0 0 ${width} ${height}" shape-rendering="crispEdges" aria-hidden="true">${markup}</svg>`;
  }
  const [rows,colors]=uiIcons[name];
  return `<svg viewBox="0 0 ${rows[0].length} ${rows.length}" shape-rendering="crispEdges" aria-hidden="true">${pixels(rows,colors)}</svg>`;
 }
 function buttonIcon(name){
  if(name!=='reflect')return uiIcon(name);
  // Keep the supplied PNG intact and key out its original backdrop at render time.
  return `<svg viewBox="83 2 282 436" aria-hidden="true">
   <defs><filter id="reflect-texture-background" color-interpolation-filters="sRGB">
    <feColorMatrix values="1 0 0 0 0  0 1 0 0 0  0 0 1 0 0  -3 0 0 0 2.75"/>
    <feComposite in2="SourceAlpha" operator="in"/>
   </filter></defs>
   <image href="./reflect-button.png" width="416" height="444" filter="url(#reflect-texture-background)"/>
  </svg>`;
 }
 function actor(x,y,kind,id,color,enemy){
  if(enemy?.disguised)return `<g class="mimic-breath" pointer-events="none">${prop('chest',x,y)}</g>`;
  const hero=kind==='hero', boss=['boss','breaker','mirrorboss'].includes(kind);
  const drawnSize=boss?58:52;
  const hp=enemy?Math.min(1,enemy.hp/(enemy.maxHp||enemy.hp)):0;
  return `<g transform="translate(${x*60},${y*60})" pointer-events="none" class="map-actor ${hero?'player-sprite':'enemy-sprite'}">
   <ellipse cx="30" cy="49" rx="22" ry="8" fill="#100f1d" opacity=".8"/>
   ${hero?`<path d="M8 44v9h10m24 0h10v-9" stroke="${color}" fill="none" stroke-width="2"/>`:''}
   <g transform="translate(${boss?1:4},${boss?2:5}) scale(${drawnSize/spriteSize(kind)})" shape-rendering="crispEdges">${sprite(kind,color)}</g>
   ${enemy?`<path d="M13 54h34" stroke="#1a1321" stroke-width="6"/><path d="M13 54h${34*hp}" stroke="#e88576" stroke-width="3"/>
   <text x="8" y="14" fill="#ffe3aa" font-size="10" font-weight="800">${id+1}</text>
   ${enemy.stolen?'<circle cx="44" cy="18" r="5" fill="#86eeea" stroke="#eefcff"/>':''}
   ${enemy.element?`<circle cx="46" cy="15" r="5" fill="${{fire:'#fa855f',frost:'#a5e8ff',spark:'#f5d374'}[enemy.element]}"/>`:''}
   ${enemy.intent.action==='notice'?'<text x="44" y="15" fill="#ffde8a" font-size="20" font-weight="900">!</text>':''}`:''}</g>`;
 }
 function itemPixels(id){
  const entry=inventorySprites[id];
  if(!entry)return '';
  const [spriteName,palette]=entry;
  const cacheKey='inventory:'+id;
  if(!cache.has(cacheKey))cache.set(cacheKey,pixels(items[spriteName],palette||itemColors[spriteName]||props));
  return cache.get(cacheKey);
 }
 function itemIcon(id){
  return `<svg class="item-icon" viewBox="0 0 10 10" shape-rendering="crispEdges" aria-hidden="true">${itemPixels(id)}</svg>`;
 }
 function prop(kind,x,y,used=false,item=null){
  const key=({cache:'chest',materials:'open_chest',supply_choice:'chest',recall:'chart',terror:'chart',ankh:'wonder',smoke:'smoke',echo_smoke:'smoke',dropped_item:'lure_cache',grass_seed:'seed',sun_seed:'seed',stolen_energy:'dew',rune:'wonder'})[kind]||kind;
  const sprite=used&&key==='chest'?'open_chest':used&&key==='shrine'?'dry_spring':key;
  if(!items[sprite])return '';
  if(!cache.has(sprite))cache.set(sprite,pixels(items[sprite],itemColors[sprite]||props));
  const spriteMarkup=itemPixels(item??kind)||cache.get(sprite);
  const dimmed=used&&sprite!=='open_chest'&&sprite!=='dry_spring';
  return `<g transform="translate(${x*60+9},${y*60+12}) scale(4.2)" opacity="${dimmed?.4:1}" pointer-events="none" shape-rendering="crispEdges">${spriteMarkup}</g>`;
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
  const left=west?5:0,right=east?55:60,top=north?5:0;
  const cap=south?23:60, width=right-left;
  const n=(x*47+y*73+x*y*3)%97;
  const strips=south?[[top,cap,1],[cap,36,.65],[36,48,.53],[48,58,.43]]:
   [[top,20,.82],[20,40,.73],[40,60,.64]];
  const blocks=strips.map(([a,b,tone],row)=>{
   const seam=13+(n+row*19)%34;
   return `<path d="M${left} ${a}h${width}v${b-a-2}H${left}z" fill="${color}" opacity="${tone}"/>
    <path d="M${left+2} ${a+2}H${seam-3}m5 0H${right-2}" stroke="#e8dbb4" stroke-width="2" opacity="${row===0?.27:.16}"/>
    <path d="M${seam} ${a}v${b-a-1}" stroke="#161520" stroke-width="2" opacity=".72"/>`;
  }).join('');
  const moss=south&&n%4===0?`<path d="M${left+3} 49h9v3h5v2h-12v-2h-2z" fill="#819073" opacity=".44"/>`:'';
  return `<g transform="translate(${x*60},${y*60})" shape-rendering="crispEdges" pointer-events="none">
   <path d="M0 0h60v60H0z" fill="#1b1a27"/>
   ${blocks}${moss}
   <path d="M${left+5+n%10} ${top+8}h5v2h-5zm${22+n%9} 5h7v2h-7z" fill="#e6cba7" opacity=".24"/>
   ${south?`<path d="M${left} ${cap-4}h${width}v3H${left}z" fill="#eedab0" opacity=".24"/>
   <path d="M${left} ${cap-1}h${width}v3H${left}z" fill="#201b29"/>`:''}
   ${west?`<path d="M${left+1} ${top}V58" stroke="#d7cbb1" opacity=".26" stroke-width="2"/>`:''}
   ${east?`<path d="M${right-1} ${top}V58" stroke="#171522" opacity=".53" stroke-width="3"/>`:''}
  </g>`;
 }
 function ground(x,y,floorColor,shade){
  const X=x*60,Y=y*60,n=(x*47+y*73+x*y*3)%97;
  const grout=n%3===0?'M2 31h56m-38-29v29m20 0v27':'M4 55V5h51v48m-50 1h47';
  const scuff=n%5===0?`<path d="M${15+n%9} 13h9v4h6v6h6" fill="none" stroke="#1a1c2c" stroke-width="2" opacity=".38"/>`:'';
  const moss=(shade.north||shade.west)&&n%3!==0?'<path d="M5 10h8v3h5v3H9v-2H5zM9 17h4v3H9z" fill="#91a86e" opacity=".42"/>':'';
  return `<rect class="floor" x="${X}" y="${Y}" width="60" height="60" fill="${floorColor}"/>
   <g transform="translate(${X},${Y})" pointer-events="none" shape-rendering="crispEdges">
    <path d="M0 0h60v60H0z" fill="${n%4===0?'#e1cfad':'#10121e'}" opacity="${.05+(n%7)/100}"/>
    <path d="${grout}" fill="none" stroke="#1a1a2a" stroke-width="2" opacity=".28"/>
    <path d="M3 3h52m-52 0v51" fill="none" stroke="#dcd6c2" opacity=".12"/>
    <path d="M${n%32+7} ${n%28+7}h7v2h-7zm3 4h3v3h-3zM${n%19+14} ${n%11+39}h4v3h-4z"
     fill="#c4b592" opacity=".2"/>
    ${scuff}${moss}
    <path d="${shade.north?'M0 0h60v9H0z':''}${shade.west?'M0 0h5v60H0z':''}${shade.east?'M55 0h5v60h-5z':''}" fill="#10121b" opacity=".32"/>
   </g>`;
 }
 function fragileFloor(x,y,open){
  if(open)return `<g data-terrain-art="pit" transform="translate(${x*60},${y*60})" pointer-events="none" shape-rendering="crispEdges">
   <path d="M3 3h54v54H3z" fill="#20202b"/>
   <path d="M5 7h50v47H5z" fill="#030407"/>
   <path d="M5 7h50v5H44v3H29v-2H17v-2H5z" fill="#36323a"/>
   <path d="M6 12h4v13H8v12H6zm47 0h2v24h-2z" fill="#181821"/>
   <path d="M3 3h54v2H3zm0 52h54v2H3z" fill="#9a8874" opacity=".69"/>
  </g>`;
  const cracks='M2 14h9v5h10v7h7v9h8v8h9v8h13M28 35v8H18v9h-6v6M21 26h-9v8H2m26-8h9v-8h7V9h8V2m-8 16h9v7h5M17 4v6h6v8m13 25v9h-5v6m14-7h8v-9h5';
  return `<g data-terrain-art="cracked" transform="translate(${x*60},${y*60})" pointer-events="none" fill="none" shape-rendering="crispEdges">
   <path d="${cracks}" stroke="#c4af91" stroke-width="2" opacity=".6" transform="translate(1 1)"/>
   <path d="${cracks}" stroke="#201b24" stroke-width="2"/>
   <path d="M7 8h6v2H7zM35 8h4v3h-4zM34 29h4v2h-4zM51 32h4v3h-4zM7 43h4v3H7zM21 55h3v2h-3z" fill="#d7b490" opacity=".48"/>
  </g>`;
 }
 function statusLabel({kind,amount}){
  return {
   damage:'−'+amount, blocked:'挡 '+amount, reflected:'反弹 '+amount,
   healed:'+'+amount, cured:'解毒', revive:'复苏至 '+amount, fall:'坠落', energy_gain:'能量 +'+amount, sanity_gain:'理智 +'+amount, defense_loss:'防御 −'+amount, range_loss:'射程 −'+amount, stun:'击晕',
  }[kind];
 }
 function statusEffects(effects, top, left, width, height){
  const stacks=new Map();
  for(const fx of effects){
   if(!statusLabel(fx)||fx.kind==='fall'||(fx.kind==='revive'&&fx.amount==null))continue;
   for(const [x,y] of fx.cells){
    if(x<left||x>=left+width||y<top||y>=top+height)continue;
    const key=x+','+y;
    if(!stacks.has(key))stacks.set(key,{x,y,labels:[]});
    stacks.get(key).labels.push(fx);
   }
  }
  return [...stacks.values()].map(({x,y,labels})=>{
   const start=Math.max(top*60+20,y*60+15-(labels.length-1)*17);
   return `<g transform="translate(${x*60+30},${start})" pointer-events="none" aria-hidden="true">
    ${labels.map((fx,index)=>`<text class="hit-fx" data-effect="${fx.kind}" y="${index*17}" text-anchor="middle"
     font-size="${fx.kind==='damage'?20:15}" font-weight="900" stroke="#191321" stroke-width="3"
     paint-order="stroke">${statusLabel(fx)}</text>`).join('')}</g>`;
  }).join('');
 }
 function refraction(path,preview=false){
  const points=path.map(([x,y])=>`${x*60+30},${y*60+30}`).join(' ');
  return `<g data-refraction="${preview?'preview':'hit'}" class="${preview?'':'fx beam-fx'}" pointer-events="none" fill="none" stroke-linejoin="bevel">
   <polyline points="${points}" stroke="#bd86ff" stroke-width="${preview?4:11}" opacity="${preview ? .65 : .32}"${preview?' stroke-dasharray="5 7"':''}/>
   ${preview?'':`<polyline points="${points}" stroke="#f0d8ff" stroke-width="4"/>`}
  </g>`;
 }
 function effects(fx,color){
  if(fx.kind==='refraction')return (fx.segments??[]).map(path=>refraction(path)).join('');
  if(fx.kind==='conduction')return fx.cells.map(([x,y])=>`<g data-conduction-hit class="fx beam-fx" transform="translate(${x*60},${y*60})" pointer-events="none">
   <path d="M9 43l13-15 7 8 11-19 10 5M29 36l4 12 14 2" fill="none" stroke="#7feaff" stroke-width="5"/>
   <path d="M9 43l13-15 7 8 11-19 10 5" fill="none" stroke="#e6fbff" stroke-width="2"/>
  </g>`).join('');
  if(fx.kind==='guard'){
   const [rows,colors]=uiIcons.guard;
   return fx.cells.map(([x,y])=>`<g transform="translate(${x*60+30},${y*60+32})" pointer-events="none" aria-hidden="true">
    <g class="guard-shield-fx"><g transform="translate(-19,-19) scale(3.17)" shape-rendering="crispEdges">
     ${pixels(rows,colors)}</g></g>
   </g>`).join('');
  }
  if(fx.kind==='reflect_arc'||(fx.kind==='impact'&&fx.direction)){
   const impact=fx.kind==='impact';
   const {markup}=waveSprites[impact?'impact':'reflect'];
   const [dx,dy]=fx.direction;
   const angle=Math.atan2(dy,dx)*180/Math.PI;
   return fx.cells.map(([x,y])=>`<g transform="translate(${x*60+30},${y*60+30}) rotate(${angle})"
    pointer-events="none" aria-hidden="true" shape-rendering="crispEdges">
    <g class="${impact?'shock-wave-fx':'reflect-arc-fx'}">
     <g transform="${impact?'translate(-67,-22) scale(2.8)':'translate(11,-24) scale(2.65)'}">${markup}</g>
    </g>
   </g>`).join('');
  }
  const palette={wave:color,return:'#b5a2fb',laser:'#ff9479',enemy:'#ff8d75',guard:'#a1d7fc',blink:'#88eff2',burn:'#ffab5a',impact:'#f2c985',grass:'#acd46a',bones:'#ede2c8',web:'#d9c3e8',ice:'#9cecff',electric:'#9cecff',steam:'#c8e1e7',thaw:'#c8e1e7',hook:'#fcce83',poison:'#b5e86c',trap:'#edb481',sound:'#ffdf91',smoke:'#b3c2de',revive:'#f7d574',roots:'#b6cc78',split:'#e5a3d6'};
  const tint=fx.kind==='energy_gain'?'#9de8f7':palette[fx.kind]||'#eaa781';
  if(fx.kind==='anchor_chain'){
   const cells=fx.origin?[fx.origin,...fx.cells]:fx.cells;
   if(cells.length<2)return '';
   const points=cells.map(([x,y])=>`${x*60+30},${y*60+30}`).join(' ');
   return `<g class="fx beam-fx" pointer-events="none" fill="none" stroke-linejoin="bevel">
    <polyline points="${points}" stroke="#19262b" stroke-width="9"/>
    <polyline points="${points}" stroke="#81c8b5" stroke-width="6" stroke-dasharray="9 4"/>
    <polyline points="${points}" stroke="#e0f5dc" stroke-width="2"/>
   </g>`;
  }
  const beam=['wave','return','laser','mirror_split'].includes(fx.kind);
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
   const split=fx.kind==='mirror_split';
   const beamColor=split?'#b4b4ff':tint;
   return `<g class="fx beam-fx" pointer-events="none"><path d="${d}" stroke="${beamColor}" stroke-width="${split?12:21}" opacity=".22" fill="none"/><path d="${d}" stroke="${beamColor}" stroke-width="${split?6:10}" fill="none"/><path d="${d}" stroke="#fff9e1" stroke-width="3" fill="none"/>${parts.join('')}</g>`;
  }
  return fx.cells.map(([x,y])=>`<g transform="translate(${x*60+30},${y*60+30})" pointer-events="none"><g class="fx pulse-fx" fill="none" stroke="${tint}" stroke-width="4"><path d="M-21 -12l9-9h24l9 9v24l-9 9h-24l-9-9z"/><path d="M-7 0h14m-7-7v14"/></g></g>`).join('');
 }
 return {actor,portrait,enemyPortrait,uiIcon,buttonIcon,prop,itemIcon,ground,fragileFloor,stoneWall,effects,refraction,statusLabel,statusEffects,doorway};
})();
