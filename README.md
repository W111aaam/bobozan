# 波波攒 · 地牢试炼

浏览器格子地牢 demo：移动、攒、波、防；你行动，世界才前进一步。
纯 Python 3.10+ 与原生 HTML / CSS / JavaScript，无第三方依赖。

## 开始试玩

```sh
cd bobozan
python3 server.py --port 8767
```

打开 <http://127.0.0.1:8767>，Ctrl+C 停止。修改 Python 后需要重启服务，修改页面后刷新即可。服务只监听本机，尚未发布到公网。

## 静态试玩版

    python3 tools/build_static.py dist/bobozan
    python3 -m http.server 8768 --directory dist --bind 127.0.0.1

打开 <http://127.0.0.1:8768/bobozan/>。此版本在 Web Worker 中运行游戏的 Python 逻辑，首次加载需要访问 Pyodide 的 CDN。进度保存在当前浏览器。发布到 GitHub Pages 时，将 `dist/bobozan` 用作站点产物。

## 本轮完成

1. **整层自由探索**：按种子生成房间、环路和支路。走过门即可往返；敌人生命、奖励、宝箱、泉水状态不会重置。
2. **探索与导航**：墙体遮挡视线，探索后保留地形记忆，视野外隐藏敌人实时信息；提供小地图和已探索区域自动寻路。

玩家可以准备充分再开战：安全地点允许攒，能量有上限，跨房保留且脱战不衰减；每次有效操作仍消耗一拍。安全时点「攒满」可连续攒，能量满或遇险就停；也可点「停止攒能」取消。参考 [原作的持续休息](https://github.com/00-Evan/shattered-pixel-dungeon/blob/master/core/src/main/java/com/shatteredpixel/shatteredpixeldungeon/actors/hero/Hero.java#L1505)。反击跨房、清场保留，发射后消耗。

## 操作

| 操作 | 键盘 / 鼠标 | 效果 |
| --- | --- | --- |
| 移动 | 方向键 / WASD / 相邻格 / 方向按钮 | 每步消耗一拍。长按键盘方向可连续移动，松键或遇敌即停 |
| 自动行走 | 点击地图或小地图的已探索地面 | 途中可点另一处地面改道。遇敌、受伤或触发事件时停下并保留目标。手动走位后可点「继续前往」；局面仍危险时点「继续一步」，每次重新计算一格安全路线 |
| 停止行走 / 取消瞄准 | Esc / 停止按钮 | 停止后续步骤，已提交的一步仍结算 |
| 攒 | 1 / 攒按钮 | 增加 1 能量 |
| 波 | 2 / 波按钮，再按方向键或左键点射线上的敌人 | 消耗 1 能量，射程 4 格、伤害 1 |
| 防 | 3 / 防按钮 | 抵挡本拍最多 1 点总伤害；实际挡伤后下一次波 +1 |
| 重波 | 获得强化后按 4，再选方向 | 消耗 3 能量，伤害 2 |
| 查看 | 右键点地图上的物品或敌人，也可按 I 进入查看模式 | 查看物品说明或敌人的生命、攻防与攻击方式，不耗时 |
| 完成本层 | 击败守关者后走到楼梯，再次点击楼梯或完成按钮 | 每区第 4 层须击败封锁阶梯的守卫，守关层须清场，第 26 层在祭坛结算冒险 |

初始 5 生命、0 能量，上限 3。每进一个新区域生命上限 +1，当前生命不变。反击不叠加，移动/攒保留，发射即消耗（含打空）。普通波遇墙或首个角色停止。敌人意图提前锁定，红格显示下拍攻击范围；移动先结算、伤害同时生效，双方同时归零算失败。无效操作不消耗行动，没有实时倒计时。

## 地图与奖励

主线有五个区域，共 26 层。每个区域四层普通探索、一层独立守关地图，第 26 层是终点祭坛。

| 楼层 | 区域 | 守关层 |
| --- | --- | --- |
| 1–5 | 下水道 | 5 |
| 6–10 | 监狱 | 10 |
| 11–15 | 洞穴 | 15 |
| 16–20 | 矮人都市 | 20 |
| 21–25 | 恶魔大厅 | 25 |
| 26 | 终点 | 抵达祭坛结算 |

普通层根据种子和区域分配入口、战斗、补给、泉水和阶梯。房间数、位置和连接随种子变化，主环可接支房与捷径。普通房间可生成紧凑、狭长、切角、十字或带凹角的房型，门口留出侧移空间，高草与短草成片出现。普通战斗房至少有两个入口，入口前后有侧移空间。每区第 4 层（第 4、9、14、19、24 层）必须清理指定战斗区才可下楼。其他普通层允许绕开敌人。设计参考 [Shattered Pixel Dungeon 的楼层分配](https://github.com/00-Evan/shattered-pixel-dungeon/blob/master/core/src/main/java/com/shatteredpixel/shatteredpixeldungeon/Dungeon.java#L280) 和[房间生成](https://github.com/00-Evan/shattered-pixel-dungeon/blob/master/core/src/main/java/com/shatteredpixel/shatteredpixeldungeon/levels/RegularLevel.java#L99)。

普通门关闭时挡视线和波，玩家或敌人踏入就打开，门格无人时关闭。点击已探索地面可沿途打开普通门。自动移动遇到新发现的障碍或危险地格时会尝试绕路。找不到已知的安全路线时停步并保留目的地。新敌人出现、受伤或触发选项时会立即停下。接战时点击远处只走一步，并绕开已标出的危险格。敌人首次发现玩家时先警觉一拍，追击后会记住最后看到的位置，也能开门继续追击。旧存档保留当前层地形，下楼时使用新生成规则。

部分普通层有暗门。亲眼看到金色刻痕后，本层日志会记下位置。点击日志、主地图或小地图上的刻痕会导航到可搜查的位置。按 `X` 或点「搜查」消耗一拍揭开暗门，随后可进去寻找随机刻印。设计参考 [原作的地牢日志](https://github.com/00-Evan/shattered-pixel-dungeon/blob/master/core/src/main/java/com/shatteredpixel/shatteredpixeldungeon/journal/Notes.java#L138)和[主动搜查](https://github.com/00-Evan/shattered-pixel-dungeon/blob/master/core/src/main/java/com/shatteredpixel/shatteredpixeldungeon/actors/hero/Hero.java#L2490)。

普通层布置刺针、夹足、警报和坠落陷阱。自动寻路会绕开已布置的未触发机关和裂地。点选陷阱或手动踩入会直接触发，按 X 搜查仍可揭露两格内的隐藏机关。警报将触发位置广播给整层敌人。布满裂纹的脆弱地板在首次踩过后会变成方形破洞。踩中坠落机关或踏入已打开的破洞会掉到下一层的安全普通格，受到自身最大生命 30%–50% 的伤害，按整数结算。参考 [原作机关触发](https://github.com/00-Evan/shattered-pixel-dungeon/blob/master/core/src/main/java/com/shatteredpixel/shatteredpixeldungeon/levels/traps/Trap.java)、[全层警报](https://github.com/00-Evan/shattered-pixel-dungeon/blob/master/core/src/main/java/com/shatteredpixel/shatteredpixeldungeon/levels/traps/AlarmTrap.java)和[坠落过渡](https://github.com/00-Evan/shattered-pixel-dungeon/blob/master/core/src/main/java/com/shatteredpixel/shatteredpixeldungeon/levels/features/Chasm.java)。

地图右上角可缩放，桌面也可在地图上滚动；点击倍率恢复默认大小。参考 [原作的地图缩放](https://github.com/00-Evan/shattered-pixel-dungeon/blob/master/core/src/main/java/com/shatteredpixel/shatteredpixeldungeon/scenes/CellSelector.java)。

按 `I` 或点「查看」后，可以点选地格查看墙、门、机关、物品和攻击预警，查看不消耗行动。参考 [原作的地格查看](https://github.com/00-Evan/shattered-pixel-dungeon/blob/master/core/src/main/java/com/shatteredpixel/shatteredpixeldungeon/scenes/GameScene.java#L1750)。

楼层地图和冒险手记里的「本层路标」会记住已发现的阶梯、泉水、锁门和补给。点击可寻路，背包已满、泉水暂时用不上或补给隔着脆墙时会显示提示。离开视野或刷新页面后仍会保留记录，拿走的补给会移出列表。参考 [原作的地标笔记](https://github.com/00-Evan/shattered-pixel-dungeon/blob/master/core/src/main/java/com/shatteredpixel/shatteredpixeldungeon/journal/Notes.java)。

每个区域的第三层，泉水旁会放一张测绘卷轴。放进背包后可消耗一拍使用：小地图和主画面以冷色显示只经测绘的房间和通道，能直接点选这些地格寻路；敌人、物品、机关和未发现的暗门仍需亲眼确认。参考 [原作的魔法地图卷轴](https://github.com/00-Evan/shattered-pixel-dungeon/blob/master/core/src/main/java/com/shatteredpixel/shatteredpixeldungeon/items/scrolls/ScrollOfMagicMapping.java)。

普通层的战斗和探索房会生成矩形、长厅或削角房。长厅提供更长的射线，削角房压缩角落的走位空间。门口保留侧移空间。参考 [原作的房间尺寸分档](https://github.com/00-Evan/shattered-pixel-dungeon/blob/master/core/src/main/java/com/shatteredpixel/shatteredpixeldungeon/levels/rooms/standard/StandardRoom.java)。

从第 2 层开始，部分普通层会出现「积水」或「草木茂盛」。战斗区与普通探索房内会额外生成连片浅水或高草，出生点、补给和门口落脚区避开新增地形。积水会改变导电与灼烧的站位，茂盛高草提供更多遮挡视线的机会。参考 [原作的楼层随机特征](https://github.com/00-Evan/shattered-pixel-dungeon/blob/master/core/src/main/java/com/shatteredpixel/shatteredpixeldungeon/levels/Level.java#L248)。

普通层的初始怪量随区域内进度提高，目标为 4、5、6、7 只，洞穴之后的大地图可多一只。支房敌人计入目标，警戒库房守卫另计，实际数量受可用出生点限制。新增怪物分布在探索房，避开入口、门口和门轴，入口后的首次接战仍有侧移空间。每区先出现常见怪，后半段才混入更多特长怪。参考 [原作刷怪数量和位置](https://github.com/00-Evan/shattered-pixel-dungeon/blob/master/core/src/main/java/com/shatteredpixel/shatteredpixeldungeon/levels/RegularLevel.java#L197)和[怪种轮换](https://github.com/00-Evan/shattered-pixel-dungeon/blob/master/core/src/main/java/com/shatteredpixel/shatteredpixeldungeon/actors/mobs/MobSpawner.java#L58)。

从第 2 层起，有合适的探索房敌人时，会安排一只普通敌人巡逻。它每三拍尝试在房内移动一格，绕开门口落脚区和机关。看到玩家或听到诱饵后，按现有察觉和追踪规则行动。参考 [原作的游荡状态](https://github.com/00-Evan/shattered-pixel-dungeon/blob/master/core/src/main/java/com/shatteredpixel/shatteredpixeldungeon/actors/mobs/Mob.java#L1230)。

敌人会绕开地火、已开裂的地板和可见的未触发陷阱。玩家站在危险格时，近战怪可追到旁边继续攻击。敌人仍会经过隐藏陷阱，玩家可趁机远程触发，也可用冲击波把敌人推入危险格。参考 [原作按角色判断地格是否可走](https://github.com/00-Evan/shattered-pixel-dungeon/blob/master/core/src/main/java/com/shatteredpixel/shatteredpixeldungeon/actors/mobs/Mob.java#L541)。

每个区域的第三层有机会出现刺针库房。开锁后，一排可见机关挡住通往奖励的路。可用波或诱饵远程触发其中一格，再从那格安全通过。门纹与本层路标会预告机关和奖励。参考 [原作陷阱房的布置](https://github.com/00-Evan/shattered-pixel-dungeon/blob/master/core/src/main/java/com/shatteredpixel/shatteredpixeldungeon/levels/rooms/special/TrapsRoom.java#L55)。

从第 6 层起，部分普通层会在原本相邻但未直通的房间之间藏一条捷径。找到墙上的刻痕后可以搜查开门，之后可双向穿越，自动寻路也会计算新通道。捷径避开入口和阶梯所在房间。入口和已揭开的捷径都会记入本层路标，也可从地图直接寻路。设计参考 [原作的环形房间布局和暗门](https://github.com/00-Evan/shattered-pixel-dungeon/blob/master/core/src/main/java/com/shatteredpixel/shatteredpixeldungeon/levels/RegularLevel.java)。

## 波形、机关与新敌人

瞄准波、重波或反弹时，四向预览会同时列出可见命中、预计受到的伤害和反弹伤害。点击预览中的方向可直接出招。地图上只被一条射线经过的格子也可直接点选，包括镜面折射后的格子。伤害预览使用真实结算规则，并只显示已知来源。参考 [原作的弹道计算](https://github.com/00-Evan/shattered-pixel-dungeon/blob/master/core/src/main/java/com/shatteredpixel/shatteredpixeldungeon/mechanics/Ballistica.java)。


电核的电波可沿四向相连的浅水传导，带闪电标记的地格是下拍危险区。上岸可避开导电，普通防可挡住这次伤害。正面反弹电波时，反射束也能让经过的水池导电并击伤池中的敌人。同一束电波对同一目标只造成一次伤害。浅水也会熄灭敌人的灼烧，冲击波把敌人推入水中时同样生效。参考 [原作的闪电法杖](https://github.com/00-Evan/shattered-pixel-dungeon/blob/master/core/src/main/java/com/shatteredpixel/shatteredpixeldungeon/items/wands/WandOfLightning.java)和[灼烧状态](https://github.com/00-Evan/shattered-pixel-dungeon/blob/master/core/src/main/java/com/shatteredpixel/shatteredpixeldungeon/actors/buffs/Burning.java)。


- 展开「发射器与改装」切换直线、扇形、回旋和穿透发射器。切换花一拍。扇形覆盖近处多格，回旋下一拍沿实际去程返回，穿透可打到第二个敌人。
- 按 `5` 进入反弹瞄准，确认方向消耗 1 能量。挡住本拍第一发远程波并沿所选方向反射。短距强波改装使伤害 +1、射程减半。耗能厚盾让普通防消耗 1 能量、挡至多 2 点总伤害。
- 镜面会折转直线射线。金色镜面在本拍被波击中后翻转方向。脆弱地板第一次踩入会开裂，再次踩入会塌陷并让角色死亡。自动寻路绕开脆弱地板。
- 监狱护卫怪会掩护相邻同伴。破城守关者的震波可打开通往补给的脆墙。洞穴和矮人都市部分楼层的共鸣双子会因同伴受伤或死亡改变招式，镜像守关者会复制波形、强波和穿透等能力，攻击范围提前显示。
- 每层有约一成概率在锁门支路出现镜间奇遇。第一层可用种子 `3` 重现。奇遇一次性恢复 3 生命并补满能量。

每区有一只战术补给箱，出现在该区第 2 或第 4 层。点击箱子会走过去并打开，也可以站在箱子上点「打开补给箱」。可在两件消耗品中带走一件，或合上箱子稍后再选。本层路标和地格查看可预览已发现箱子的候选道具。即使背包已满也可以查看箱内物品。点「整理背包」腾出空间，再点「返回补给箱」继续挑选。种子可以补进未满的种子槽。下水道提供烟雾弹或诱饵，之后提供响雾弹或响草种子。参考 [原作的水晶选择房](https://github.com/00-Evan/shattered-pixel-dungeon/blob/master/core/src/main/java/com/shatteredpixel/shatteredpixeldungeon/levels/rooms/special/CrystalChoiceRoom.java)。

区域内的第 2、4 层，钥匙有机会打开封闭花圃或警戒库房。亲眼见过锁门后，门纹和本层路标会标出房间类型。按 I 查看门纹可了解里面的补给或警报。花圃的阳草可在受伤后回来踩，恢复 2 生命，旁边的缠根能限制追来的敌人。警戒库房的响雾弹占一个背包槽，入口警报会通知整层敌人。可先用波从远处触发警报，再利用声音引开追来的敌人。镜间奇遇仍可能出现在这些楼层。参考 [原作特殊房间生成](https://github.com/00-Evan/shattered-pixel-dungeon/blob/master/core/src/main/java/com/shatteredpixel/shatteredpixeldungeon/levels/rooms/special/SpecialRoom.java)和[花园](https://github.com/00-Evan/shattered-pixel-dungeon/blob/master/core/src/main/java/com/shatteredpixel/shatteredpixeldungeon/levels/rooms/special/GardenRoom.java)。


普通层有 12 种区域敌人和 10 种支房敌人，随区域和楼层轮换。金色虚线是蓄力预告，红格是下一拍的伤害范围，青色虚线标出侧闪或跃进方向。见[敌人图鉴与头脑风暴](ENEMY_DESIGN.md)。

旧存档保留当前楼层的地图与敌人，从更新后首次下楼起记录可往返的楼层。站在下层出生点的上行阶梯上，再点地格或「上楼」回到上一层。探索记录、敌人与物资均按楼层保存。上下楼各消耗一拍理智。

## 难度与补给

下水道的普通敌人多为 3–4 生命，重击型敌人的指定招式造成 2 伤。五位守关者分别有 9、12、15、18、21 生命。到矮人都市后，部分守关招式进一步增强。格挡初始可吸收 1 伤并准备一次反击。短距强波消耗 2 能量，普通波消耗 1 能量。

区域后半段的疾钳蟹、护卫怪、分裂群、折跃石像和灼瞳额外增加 1 生命，第 24 层的裂步魔横扫为 2 伤。新生成的普通敌人按怪种掉落补给，基础概率为 18%–35%，每层最多两份随机掉落，首份掉落后后续概率减半并向下取整。汲血蝠的疗愈药剂另限每区一瓶。武器石像、拟态宝箱和拾能贼的专属掉落单独结算。召唤物和分裂子群不参与随机掉落，敌人坠崖时不会留下物品。右键点击敌人可查看当前掉落概率。参考 [原作怪物掉落](https://github.com/00-Evan/shattered-pixel-dungeon/blob/master/core/src/main/java/com/shatteredpixel/shatteredpixeldungeon/actors/mobs/Mob.java#L1035)和[蝙蝠药剂](https://github.com/00-Evan/shattered-pixel-dungeon/blob/master/core/src/main/java/com/shatteredpixel/shatteredpixeldungeon/actors/mobs/Bat.java)。

第 5、20 层首领的震荡先以金色虚线预告，下一拍攻击原位置，之后休整一拍。半血后从横排变为更强的十字震荡，通常需要在蓄力时开始撤离。墙和关闭的门可挡住震荡。参考 [Goo 的蓄力与半血阶段](https://github.com/00-Evan/shattered-pixel-dungeon/blob/master/core/src/main/java/com/shatteredpixel/shatteredpixeldungeon/actors/mobs/Goo.java)。

第 1、7、12、17、22 层各有一瓶固定疗愈药剂，回复 2 生命并解毒。第 2、9、14、19、24 层及守关层有一次性泉水，各回复 1 生命。额外疗愈可从露珠、阳草和配方等途径获得。护心每个区域在受伤时生效一次。安全区域仍可蓄满能量再接战。 地图只生成可用的泉水和有内容的宝箱。使用过的泉水变为干石池，空箱保留打开的箱盖。

理智上限 450，每行动一拍降低 1 点。降到 150 及以下时，本层至多在两个未探索战斗或探索房间各增加一只敌人。理智耗尽立即扣 1 生命，之后按最大生命积累腐蚀，累计 120 点再扣 1 生命。击杀敌人每只恢复 20 理智，召唤物和分裂子群除外。微光回复 65 理智，波与重波伤害 +1，持续 65 拍。圣光回复 105 理智，每次攒额外获得 1 能量，持续 105 拍。辉光回复 155 理智，每实际走满 50 步回复 1 生命，持续 155 拍。三种效果分别计时，重复拾取同种光会刷新其时间，辉光步数保留至效果结束。普通层至少有一份圣光。沟渠鱼偶尔掉落微光，圣光不占背包槽。参考 [原作饱食度](https://github.com/00-Evan/shattered-pixel-dungeon/blob/master/core/src/main/java/com/shatteredpixel/shatteredpixeldungeon/actors/buffs/Hunger.java)及[普通层资源生成](https://github.com/00-Evan/shattered-pixel-dungeon/blob/master/core/src/main/java/com/shatteredpixel/shatteredpixeldungeon/levels/RegularLevel.java#L355)。

## 职业与成长

新冒险可选行波者、扇流者、回旋者或穿锋者。不同颜色的小波分别使用直线、扇形、回旋或穿透发射器。新冒险固定职业波形，旧存档可以继续切换发射器。

角色站在未捡走的补给上时，可以通过「脚下物品」拾取，消耗一拍。背包已满时可从拾取窗口打开背包整理，原地腾出空间后再选要拿的东西。参考 [原作的地面拾取逻辑](https://github.com/00-Evan/shattered-pixel-dungeon/blob/master/core/src/main/java/com/shatteredpixel/shatteredpixeldungeon/actors/hero/Hero.java#L1049)。

同格多件物品会在地图上标出数量。站在该格可逐件选取，也可用一拍捡起背包装得下的物品，余下的留在原地。参考 [原作的地面物品堆](https://github.com/00-Evan/shattered-pixel-dungeon/blob/master/core/src/main/java/com/shatteredpixel/shatteredpixeldungeon/items/Heap.java#L122)。

背包初始有 8 个物品槽，同类消耗品每 3 件占一槽，护命符单独占槽，点槽内道具可先查看说明，再选择使用或放下。背包、地面和快捷栏共用道具像素图标。快捷栏可同时绑定两种道具，默认用 Q 喝疗愈药剂、用 E 瞄准烟雾弹。可在道具详情直接绑定 Q 或 E，也可用下拉框解除绑定。第 5 层和第 15 层的守关战分别奖励一件扩容遗物，各增加 2 槽。第 5 层的侧袋还能把同类种子每 5 颗放一槽。拾取可补进未满的种子槽，播种、投掷和放下一次只用一颗。参考 [原作种子袋](https://github.com/00-Evan/shattered-pixel-dungeon/blob/master/core/src/main/java/com/shatteredpixel/shatteredpixeldungeon/items/bags/VelvetPouch.java)。背包的人物信息可查看生命、能量、发射器、遗物和已学天赋。

首次进入第 1、6、11 层时弹出天赋窗口，每组 3 选 1，也可以跳过。选择前可查看天赋对当前射程、命中上限、防御或耗能的影响，以及缺少的生效条件。确认或跳过后，该层不再提供天赋选择。重波节能需要先通过遗物解锁重波。

第 3、8、13、18、23 层的遗物宝箱各提供一枚锻造核心，可将当前发射器强化至 +3。第一级和第三级各加 1 点伤害，第二级加 1 格基础射程。刻印可在暗门、刺针库房、武器石像和守关战获得。每局的掉落顺序按种子随机决定，每种最多掉落一次。站在刻印所在格，脱战后通过「脚下物品」拾取并装备。每把发射器保留一个刻印，装备新的会替换旧的。扇形与回旋不能装回音。背包的人物信息可锻造并查看当前刻印。锻造和装备刻印不消耗行动拍数。

后续构筑按[构筑与赐福脑暴](docs/BUILD_IDEAS.md)的最新版实现。功能落地并验证后，在原条目标注「已完成」。

每个区域只有遗物宝箱和守关战各提供一次三选一遗物。普通清场解锁通路或附近资源。并行束从右侧一格补射，双击扳机追加一次连射。冲击波在本拍攻击结算后推开主束打伤的存活目标。灼烧在之后两拍各造成 1 伤，冰冻在叠两层霜后取消目标下一次移动。副束不触发这些遗物效果。

取得「穿透」遗物后，「飞雷神」才可能加入奖励。发射后先位移至主束最远的空地格，跳过致死裂地，再结算本拍的敌人攻击。瞄准时蓝圈标记视野内的落点。

新生成的普通层会出现高草。高草可通行并遮挡视线，踩踏或被双方攻击命中后会变成短草。少数草格会掉落露珠（回复 1 生命）或响草种子（可当诱饵）。[高草设计参考](https://github.com/00-Evan/shattered-pixel-dungeon/blob/master/core/src/main/java/com/shatteredpixel/shatteredpixeldungeon/levels/features/HighGrass.java)

灼烧主束与火核可点燃高草。地火先标出下一拍的危险格，结算时对格内的角色或敌人造成 1 伤，并可向四邻高草逐拍蔓延，最多扩散两步。凝霜雾弹可扑灭范围内的地火，并阻止本拍向该范围蔓延。自动行走会避开已知火格。[原作的火焰扩散](https://github.com/00-Evan/shattered-pixel-dungeon/blob/master/core/src/main/java/com/shatteredpixel/shatteredpixeldungeon/actors/blobs/Fire.java#L35)

背包里的「放下」会将道具留在当前格，消耗一拍。之后走回该格会拾起它；还站在原地时可以点脚下，查看这格放下的物品并选一件取回。参考 [原作的放下和拾取](https://github.com/00-Evan/shattered-pixel-dungeon/blob/master/core/src/main/java/com/shatteredpixel/shatteredpixeldungeon/items/Item.java#L121)。

战斗时会在受击者头顶显示实际扣血，成功格挡时显示挡下的伤害。参考 [原作的浮动战斗文字](https://github.com/00-Evan/shattered-pixel-dungeon/blob/master/core/src/main/java/com/shatteredpixel/shatteredpixeldungeon/effects/FloatingText.java)。

地图下方的状态标签会同时显示反击、中毒、霜冻、烟雾和敌方回波，点击可查看效果和应对方式。参考 [原作的状态栏](https://github.com/00-Evan/shattered-pixel-dungeon/blob/master/core/src/main/java/com/shatteredpixel/shatteredpixeldungeon/ui/BuffIndicator.java)。

诱饵和响草种子会先进入投掷瞄准。选择四格内的高亮空地可预览可见范围和听得见的敌人，点「投掷」才消耗一拍。可瞄准四格内高亮的墙、关门或其他障碍，道具会落在障碍近侧的可用地格，影响范围按实际落点预览。落点有陷阱时，投出的诱饵或响草种子也会压下机关。普通敌人走过隐藏陷阱时不会触发它。声音能绕过转角、穿过高草，遇到墙或关门会停止传播。听到诱饵的敌人会转去调查，玩家近在一格时则会重新专注于玩家。警报声传遍整层，敌人会先追踪触发位置。参考 [原作的道具投掷](https://github.com/00-Evan/shattered-pixel-dungeon/blob/master/core/src/main/java/com/shatteredpixel/shatteredpixeldungeon/items/Item.java#L633)。

烟雾弹也可选择落点。烟雾持续三拍，遮住落点及相邻的可通行地格。远处敌人的视线被挡住，相邻敌人仍可攻击，能量波仍可穿过。参考 [原作的遮蔽药剂](https://github.com/00-Evan/shattered-pixel-dungeon/blob/master/core/src/main/java/com/shatteredpixel/shatteredpixeldungeon/items/potions/exotic/PotionOfShroudingFog.java)。

每个区域的第四层，泉水旁有回程卷轴。使用后消耗一拍，先传送到本层入口，再结算锁定攻击。入口有敌人、被敌人抢位，或处在现有攻击范围、地火、碎骨和敌方回波中时，会保留卷轴。参考 [原作的传送卷轴](https://github.com/00-Evan/shattered-pixel-dungeon/blob/master/core/src/main/java/com/shatteredpixel/shatteredpixeldungeon/items/scrolls/ScrollOfTeleportation.java)。

生命已满时，拾到的露珠会存起来，上限 3 滴。受伤后可在背包中花一拍饮用，每滴恢复 1 生命，仅消耗补满所需的数量。参考 [原作的露珠与水袋](https://github.com/00-Evan/shattered-pixel-dungeon/blob/master/core/src/main/java/com/shatteredpixel/shatteredpixeldungeon/items/Dewdrop.java)。

第 15 层的守关场内可找到一枚护命符。放在背包中，受到致命伤时自动消耗一枚，恢复至 2 生命并解除中毒和霜冻。坠入深渊仍会结束冒险。参考 [原作的复活护符](https://github.com/00-Evan/shattered-pixel-dungeon/blob/master/core/src/main/java/com/shatteredpixel/shatteredpixeldungeon/items/Ankh.java)。

第 7 层和第 17 层的补给区有惊退卷轴。使用后，视野内可受影响的敌人接下来两拍会尝试远离玩家。这一拍已锁定的动作照常结算。参考 [原作的恐惧卷轴](https://github.com/00-Evan/shattered-pixel-dungeon/blob/master/core/src/main/java/com/shatteredpixel/shatteredpixeldungeon/items/scrolls/ScrollOfTerror.java)。

第 2 层泉水旁有一颗响草种子。种子可投作诱饵，也可从背包选择「播种」，在四格内的可见空地种下缠根。敌人踩上后，下一拍的移动会被取消。玩家踩上会消耗这株植物。参考 [原作的种植与踩踏触发](https://github.com/00-Evan/shattered-pixel-dungeon/blob/master/core/src/main/java/com/shatteredpixel/shatteredpixeldungeon/plants/Plant.java)。

第 6、16 层泉水旁可拾取阳草种子。提前种在撤退路线上，受伤后踩上可恢复 2 生命。满血经过会保留阳草，敌人踩上会毁掉它。参考 [原作的阳草](https://github.com/00-Evan/shattered-pixel-dungeon/blob/master/core/src/main/java/com/shatteredpixel/shatteredpixeldungeon/plants/Sungrass.java)。

脱战后可在背包的「炼金」中制作道具，每次消耗一拍。配方会显示持有量、缺少的材料以及当前材料够做几份。配方消耗材料后若背包仍满，成品会留在脚下。两颗响草种子加一滴存露可制成疗愈药剂。烟雾弹加诱饵可制成响雾弹，投出后同时遮蔽视线和吸引敌人调查。响雾弹加响草种子可改造成凝霜雾弹。凝霜雾弹放弃诱敌声，保留三拍烟雾，爆开时限制范围内敌人的下一拍移动，敌人仍能攻击。雾弹会先冻结范围内的浅水，结冰地格仍可通行，并在接下来两拍内暂停导电。冻结能截断同拍的水中电流，电波本身仍可直射。灼烧主束穿过冰封水格时会提前融冰，该拍的电波就能借水传导。参考 [原作浅水与霜冻的互动](https://github.com/00-Evan/shattered-pixel-dungeon/blob/master/core/src/main/java/com/shatteredpixel/shatteredpixeldungeon/actors/blobs/Freezing.java)和[原作的霜冻炸弹](https://github.com/00-Evan/shattered-pixel-dungeon/blob/master/core/src/main/java/com/shatteredpixel/shatteredpixeldungeon/items/bombs/FrostBomb.java)和[原作的炼金配方](https://github.com/00-Evan/shattered-pixel-dungeon/blob/master/core/src/main/java/com/shatteredpixel/shatteredpixeldungeon/items/Recipe.java)。

疗愈药剂恢复 2 生命，并解除用药前已有的中毒。参考 [原作的疗愈药剂](https://github.com/00-Evan/shattered-pixel-dungeon/blob/master/core/src/main/java/com/shatteredpixel/shatteredpixeldungeon/items/potions/PotionOfHealing.java)。

背包内可绑定一种快捷道具。按 `Q` 或点行动栏里的道具按钮直接使用，消耗一拍；同类道具用完后保留绑定，再次拾取即可继续使用。参考 [原作的快捷栏](https://github.com/00-Evan/shattered-pixel-dungeon/blob/master/core/src/main/java/com/shatteredpixel/shatteredpixeldungeon/ui/QuickSlotButton.java)。

## 存档

新整层存档位于 `.saves/<会话>.floor.json`，与旧线性版本 `.json` 分开保存，不覆盖旧进度。刷新及服务重启恢复探索、敌人、奖励、生命、能量和意图。新冒险替换当前整层存档。

浏览器 Cookie 标识会话；不同浏览器会话独立，同一会话多标签页共享进度，过期操作会被版本校验拒绝。清除 Cookie 或更换域名不会自动找回存档。

手记的「历次冒险」保留最近 20 次通关或失败记录，可重试原种子与职业。结算界面会记录抵达楼层、行动拍数、击败敌人、发现暗门、触发陷阱和获得遗物；失败时还会显示倒下原因。旧存档从升级后继续累计。参考 [原作的冒险统计](https://github.com/00-Evan/shattered-pixel-dungeon/blob/master/core/src/main/java/com/shatteredpixel/shatteredpixeldungeon/windows/WndRanking.java)。

## 验证

```sh
python3 -m unittest discover -v
node --check web/app.js
python3 tools/floor_playtest.py
```

测试覆盖旧版回归、整层连通/持久状态、视野、寻路、真实 HTTP 通关、会话隔离和重启恢复。HTTP 测试需要绑定本机临时端口。合法动作搜索器验证种子 0 的 26 层主线可通关；不代表真人难度与游玩时间结论。

## 文件与后续

- `floor.py`：整层地图、视野、持久对象与寻路；复用 `dungeon.py` 的战斗结算。
- `server.py`：本地服务和会话存档。
- `web/`：响应式游戏界面、小地图和操作。
- `docs/TASKS.md`：完整任务清单及完成状态。
- `docs/DESIGN.md`、`docs/FLOOR_RESEARCH.md`：设计记录与调研。
- `bobozan.py`：保留原终端对战。

任务 6 暂缓。游戏使用原创代码和图形。正式域名与服务器由用户后续提供。
