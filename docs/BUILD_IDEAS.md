# 构筑与赐福脑暴

## 发射器
1. 狙线器（直线）主束命中距离至少 3 格的敌人时伤害 +3，相邻命中伤害 −2，计算防御前最低 1 伤。可在战术补给箱选择，脱战后可在人物信息切换已取得的同系发射器。**已完成** 参考原作[投掷武器的距离判定](https://github.com/00-Evan/shattered-pixel-dungeon/blob/master/core/src/main/java/com/shatteredpixel/shatteredpixeldungeon/items/weapon/missiles/MissileWeapon.java#L210)。
2. 屏障扇（扇形）扇流者实际挡伤或成功反射后，下一发攻击 +2 伤害。可在战术补给箱选择，沿用扇形器的锻造和刻印。**已完成** 参考原作[盾牌格挡状态](https://github.com/00-Evan/shattered-pixel-dungeon/blob/master/core/src/main/java/com/shatteredpixel/shatteredpixeldungeon/items/weapon/melee/RoundShield.java#L86)。
3. 潮折器（回旋）下一拍的回波从主束终点飞向玩家行动后的位置。侧移可改线，石墙和关门会阻断回波。可在战术补给箱选择，鼠标悬停相邻地格可预览路线。**已完成** 参考原作[重型回旋镖的延迟回程](https://github.com/00-Evan/shattered-pixel-dungeon/blob/master/core/src/main/java/com/shatteredpixel/shatteredpixeldungeon/items/weapon/missiles/HeavyBoomerang.java#L111)。
4. 踏步枪（直线）实际移动后，下一发波或重波射程加一格。可在战术补给箱选择，沿用直线器的锻造等级和刻印。**已完成** 参考原作[移动蓄势](https://github.com/00-Evan/shattered-pixel-dungeon/blob/master/core/src/main/java/com/shatteredpixel/shatteredpixeldungeon/actors/buffs/Momentum.java#L88)。
5. 近身扇（扇形）波和重波固定覆盖角色周围八格，伤害乘以 1.5 并向上取整。墙和关门会遮挡。可在战术补给箱选择，点击高亮地格或在瞄准预览确认出波。**已完成** 参考原作[力场方块的八邻格判定](https://github.com/00-Evan/shattered-pixel-dungeon/blob/master/core/src/main/java/com/shatteredpixel/shatteredpixeldungeon/items/weapon/missiles/ForceCube.java#L90)。

## 刻印
7. 导电：如果主束有效命中浅水中的敌人时，电击同片水域所有敌人造成同等伤害。如果主束有效命中敌人时（不在水中），电击对该敌人半径六格范围内的所有敌人造成自身攻击力一半的伤害（向下取整，至少为一）**已完成**
8. 折射：主束首次命中敌人时，会同时发出一条光束命中半径 8 格内的另一名敌人造成一半的伤害。**已完成**
9. 近战：主光束命中敌人时，如果和敌人的距离小于等于一，伤害倍率*1.5（向上取整） **已完成**
10. 蚀盾：主光束命中敌人时，减少敌人一点防御力（防御力最低为 0）。**已完成**
11. 击晕：在两个行动回合中，主光束连续命中敌人两次时击晕敌人一回合。**已完成**
12. 中断：击中蓄力中的敌人后缩短其下一发射程（最低为 0），敌人仍会完成攻击。**已完成**

## 遗物与赐福
13. 侧翼阵列（遗物）已有并行束时才出现，发射波时宽度由两行变成三行。**已完成**
14. 守门盾（遗物）每次成功格挡后，下一发波附带击退。**已完成**
15. 镜链（遗物）一次发射经过两面镜子时，末端产生小分裂。**已完成**
16. 锚链（主动遗物）消耗一拍和一次充能，拉近敌人一格或把自己拉向空地，推进楼层补充使用次数。**已完成**
17. 预藏（主动遗物）消耗一拍和一次充能获得满能量，推进楼层补充使用次数。**已完成**
18. 待定
职业保留初始波形和颜色，替换发射器沿用该系的锻造等级与单刻印槽。所有种类的刻印共用每局的随机掉落池，每种最多掉落一次，留在地上也算已掉落。到达掉落位置后通过「脚下物品」装备或替换，人物界面只显示当前刻印。刻印池耗尽后，暗门、刺针库房、武器石像和守关战各有替代奖励。**已完成**
战术补给箱共享一次领取机会，武器、刻印、补给或赐福的获取不会因进出房间重置。

设计参考《破碎的像素地牢》的[武器能力](https://github.com/00-Evan/shattered-pixel-dungeon/blob/master/core/src/main/java/com/shatteredpixel/shatteredpixeldungeon/items/weapon/melee/Greatshield.java)、[浅水导电](https://github.com/00-Evan/shattered-pixel-dungeon/blob/master/core/src/main/java/com/shatteredpixel/shatteredpixeldungeon/items/wands/WandOfLightning.java)、[击退附魔](https://github.com/00-Evan/shattered-pixel-dungeon/blob/master/core/src/main/java/com/shatteredpixel/shatteredpixeldungeon/items/weapon/enchantments/Elastic.java)、[主动神器](https://github.com/00-Evan/shattered-pixel-dungeon/blob/master/core/src/main/java/com/shatteredpixel/shatteredpixeldungeon/items/artifacts/EtherealChains.java)和[饰品选择](https://github.com/00-Evan/shattered-pixel-dungeon/blob/master/core/src/main/java/com/shatteredpixel/shatteredpixeldungeon/items/trinkets/TrinketCatalyst.java)。

行波者主动闪避、扇流者周围八格攻击和斜走、回旋者能量球、穿锋者无限贯穿和射程转伤害已完成。重波开局可用，反弹通过遗物获得。
