# Bobozan 敌人设计工作台

参考 [Shattered Pixel Dungeon 敌人源码](https://github.com/00-Evan/shattered-pixel-dungeon/tree/master/core/src/main/java/com/shatteredpixel/shatteredpixeldungeon/actors/mobs)。以下是对行为的改编，规则和外观按 Bobozan 的单拍行动、波形和地形重新制作。

## 已进 Demo：12 种普通敌人

| 区域 | 敌人 | 它让玩家改变什么？ |
| --- | --- | --- |
| 1–4 层，下水道 | 滑鳞蛇 · [Snake](https://github.com/00-Evan/shattered-pixel-dungeon/blob/master/core/src/main/java/com/shatteredpixel/shatteredpixeldungeon/actors/mobs/Snake.java) | 看青色虚线判断它会不会侧闪，再决定等待或用扇形覆盖。 |
| 同上 | 疾钳蟹 · [Crab](https://github.com/00-Evan/shattered-pixel-dungeon/blob/master/core/src/main/java/com/shatteredpixel/shatteredpixeldungeon/actors/mobs/Crab.java) | 最多直冲两格，提前缩短站位距离；看到冲刺可先让开路线。 |
| 6–9 层，监狱 | 爆骨卫 · [Skeleton](https://github.com/00-Evan/shattered-pixel-dungeon/blob/master/core/src/main/java/com/shatteredpixel/shatteredpixeldungeon/actors/mobs/Skeleton.java) | 击倒后留下一拍尸爆预告；远杀、退一步或格挡。 |
| 同上 | 分裂群 · [Swarm](https://github.com/00-Evan/shattered-pixel-dungeon/blob/master/core/src/main/java/com/shatteredpixel/shatteredpixeldungeon/actors/mobs/Swarm.java) | 挨轻波后分出一个子群；重波击倒可阻止分裂，也能用扇形打散两群。 |
| 11–14 层，洞穴 | 汲血蝠 · [Bat](https://github.com/00-Evan/shattered-pixel-dungeon/blob/master/core/src/main/java/com/shatteredpixel/shatteredpixeldungeon/actors/mobs/Bat.java) | 挨咬会给它回血；用防把它的攻击变成自己的反击。 |
| 同上 | 棱晶萨满 · [Shaman](https://github.com/00-Evan/shattered-pixel-dungeon/blob/master/core/src/main/java/com/shatteredpixel/shatteredpixeldungeon/actors/mobs/Shaman.java) | 蓄能后打近距扇波，换一格未必够；读红格或反射。 |
| 16–19 层，矮人都市 | 蚀能术士 · [Warlock](https://github.com/00-Evan/shattered-pixel-dungeon/blob/master/core/src/main/java/com/shatteredpixel/shatteredpixeldungeon/actors/mobs/Warlock.java) | 将原作的弱化效果改为抽能；挡住伤害就能保住能量。 |
| 同上 | 静拳武僧 · [Monk](https://github.com/00-Evan/shattered-pixel-dungeon/blob/master/core/src/main/java/com/shatteredpixel/shatteredpixeldungeon/actors/mobs/Monk.java) | 守势、两伤重拳、收拳三拍循环。找空档比对着盾打更划算。 |
| 同上 | 折跃石像 · [Golem](https://github.com/00-Evan/shattered-pixel-dungeon/blob/master/core/src/main/java/com/shatteredpixel/shatteredpixeldungeon/actors/mobs/Golem.java) | 提前看到房内折跃落点，能用抢位或冻结打断，折跃后有休整。 |
| 21–24 层，恶魔大厅 | 灼瞳 · [Eye](https://github.com/00-Evan/shattered-pixel-dungeon/blob/master/core/src/main/java/com/shatteredpixel/shatteredpixeldungeon/actors/mobs/Eye.java) | 金线预告，红线实射。抓住蓄力和冷却的时间侧移。 |
| 同上 | 棘尾蝎 · [Scorpio](https://github.com/00-Evan/shattered-pixel-dungeon/blob/master/core/src/main/java/com/shatteredpixel/shatteredpixeldungeon/actors/mobs/Scorpio.java) | 远处用长尾针，近处后退。可借墙逼它在合适距离交战。 |
| 同上 | 裂步魔 · [RipperDemon](https://github.com/00-Evan/shattered-pixel-dungeon/blob/master/core/src/main/java/com/shatteredpixel/shatteredpixeldungeon/actors/mobs/RipperDemon.java) | 跃点先出现，落地后才横扫。看落点规划第二步。 |

楼层决定敌人组合，种子决定同房敌人的顺序。首层先遇到冲撞怪和滑鳞蛇，疾钳蟹从第 3 层加入。守关层沿用自己的敌人和地图，洞穴与都市各保留一层共鸣双子。敌人首次发现玩家仍有一拍警觉。特殊位移仅在房间内部，普通追击仍能开门。安全地点可以继续攒满再开战。

## 已进 Demo：10 种支房敌人

| 灵感 | Bobozan 版本 | 玩家能怎么应对 |
| --- | --- | --- |
| [Thief](https://github.com/00-Evan/shattered-pixel-dungeon/blob/master/core/src/main/java/com/shatteredpixel/shatteredpixeldungeon/actors/mobs/Thief.java) 偷窃逃跑 | 拾能贼碰到玩家后抢走一格能量，拎着可见的能量球跑向另一扇门。 | 格挡阻止抢夺，冲击波改写逃跑方向，击倒后拾回能量。 |
| [Necromancer](https://github.com/00-Evan/shattered-pixel-dungeon/blob/master/core/src/main/java/com/shatteredpixel/shatteredpixeldungeon/actors/mobs/Necromancer.java) 召唤骨兵 | 先描出召唤点，两拍后叫出一只骨傀儡，同时最多维持一只。 | 抢占召唤点、打断施法，或引骨兵挡施法者自己的波。 |
| [Guard](https://github.com/00-Evan/shattered-pixel-dungeon/blob/master/core/src/main/java/com/shatteredpixel/shatteredpixeldungeon/actors/mobs/Guard.java) 链条拉人 | 锁定单线磁钩，把命中的玩家拉近一格。 | 躲到门后、离开射线，或格挡阻止位移。 |
| [Spinner](https://github.com/00-Evan/shattered-pixel-dungeon/blob/master/core/src/main/java/com/shatteredpixel/shatteredpixeldungeon/actors/mobs/Spinner.java) 蛛网与毒 | 织网蛛先放网再找角度射毒针，玩家无法用飞雷神进出网格，敌人也无法在网上跃进。 | 用波割网、绕路，或引会跃进的敌人踩进网格。 |
| [Elemental](https://github.com/00-Evan/shattered-pixel-dungeon/blob/master/core/src/main/java/com/shatteredpixel/shatteredpixeldungeon/actors/mobs/Elemental.java) 元素分支 | 火核点燃一格草；霜核冻结空地一拍；电核沿镜面打跳跃波。 | 用环境转向攻击；可选择不同遗物抵消地形压力。 |
| [Statue](https://github.com/00-Evan/shattered-pixel-dungeon/blob/master/core/src/main/java/com/shatteredpixel/shatteredpixeldungeon/actors/mobs/Statue.java) 持有随机武器，受伤后苏醒 | 初次看到静止石像时，手记会记录位置、波形、刻印和掉落。可折返到它身旁查看，再决定是否出波。 | 从本局尚未掉落的刻印中随机抽取一枚。刻印池耗尽后掉落微光。 |
| [Succubus](https://github.com/00-Evan/shattered-pixel-dungeon/blob/master/core/src/main/java/com/shatteredpixel/shatteredpixeldungeon/actors/mobs/Succubus.java) 闪现逼近 | 镜魇从两处倒影选一处传送，真落点提前亮起。 | 离开预告落点，或用回旋波卡住显形时机。 |
| [Mimic](https://github.com/00-Evan/shattered-pixel-dungeon/blob/master/core/src/main/java/com/shatteredpixel/shatteredpixeldungeon/actors/mobs/Mimic.java) 拟态宝箱 | 假箱有微小呼吸动画；主动检查会显示异常，可以远距离先出波。 | 保持距离、检查箱子，用射程换安全。 |
| [DemonSpawner](https://github.com/00-Evan/shattered-pixel-dungeon/blob/master/core/src/main/java/com/shatteredpixel/shatteredpixeldungeon/actors/mobs/DemonSpawner.java) 定期生怪 | 产巢只有被惊动后才计拍，场上最多两只幼体，每个巢最多孵化三只。 | 先在门外准备；开战后决定先清幼体还是拆巢。 |
| [Piranha](https://github.com/00-Evan/shattered-pixel-dungeon/blob/master/core/src/main/java/com/shatteredpixel/shatteredpixeldungeon/actors/mobs/Piranha.java) 水域守卫 | 沟渠鱼只在水格活动，在可绕过的支房浅水里活动。 | 绕远保血，或者从岸上用远波打掉。 |

支房首次出现：第 1 层沟渠鱼、第 2 层拟态宝箱、第 3 层拾能贼、第 7 层召骨师、第 8 层磁钩守卫、第 11 层织网蛛、第 12 层元素核、第 13 层武器石像、第 21 层裂魔产巢、第 22 层镜魇。房间位置随地图种子变化。新楼层生成时启用，已经生成的楼层沿用原阵容。
