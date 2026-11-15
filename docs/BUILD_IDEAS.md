# 构筑与赐福脑暴

## 发射器
1. 狙线器（直线）增加远距离威力，近距离较弱。
2. 屏障扇（扇形）成功格挡后，下一发扇波两侧各多覆盖一格。
3. 潮折器（回旋）回波从终点改向玩家现站位，侧移可以重新布置回程路线。
4. 踏步枪（直线）移动后下一发射程加一格。
5. 近身扇（扇形）攻击距离缩短为以角色半为中心的 3*3 区域， 发波伤害 * 1.5 倍（向上取整） 。

## 刻印
7. 导电：如果主束有效命中浅水中的敌人时，电击同片水域所有敌人造成同等伤害。如果主束有效命中敌人时（不在水中），电击对该敌人半径六格范围内的所有敌人造成自身攻击力一半的伤害（向下取整，至少为一）
8. 折射：主束首次命中敌人时，会同时发出一条光束命中半径 8 格内的另一名敌人造成一半的伤害。
9. 近战：主光束命中敌人时，如果和敌人的距离小于等于一，伤害倍率*1.5（向上取整）
10. 蚀盾：主光束命中敌人时，减少敌人一点防御力（防御力最低为 0）。
11. 击晕：在两个行动回合中，主光束连续命中敌人两次时击晕敌人一回合。
12. 中断：击中蓄力中的敌人后缩短其下一发射程（最低为 0），敌人仍会完成攻击。

## 遗物与赐福
13. 侧翼阵列（遗物）已有并行束时才出现，发射波时宽度由两行变成三行。**已完成**
14. 守门盾（遗物）每次成功格挡后，下一发波附带击退。**已完成**
15. 镜链（遗物）一次发射经过两面镜子时，末端产生小分裂。**已完成**
16. 锚链（主动遗物）消耗一拍和一次充能，拉近敌人一格或把自己拉向空地，推进楼层补充使用次数。**已完成**
17. 预藏（主动遗物）消耗一拍和一次充能获得满能量，推进楼层补充使用次数。
18. 待定
职业保留初始波形和颜色，替换发射器沿用该系的锻造等级与单刻印槽。战术补给箱共享一次领取机会，武器、刻印碎片、补给或赐福的获取不会因进出房间重置。

设计参考《破碎的像素地牢》的[武器能力](https://github.com/00-Evan/shattered-pixel-dungeon/blob/master/core/src/main/java/com/shatteredpixel/shatteredpixeldungeon/items/weapon/melee/Greatshield.java)、[浅水导电](https://github.com/00-Evan/shattered-pixel-dungeon/blob/master/core/src/main/java/com/shatteredpixel/shatteredpixeldungeon/items/wands/WandOfLightning.java)、[击退附魔](https://github.com/00-Evan/shattered-pixel-dungeon/blob/master/core/src/main/java/com/shatteredpixel/shatteredpixeldungeon/items/weapon/enchantments/Elastic.java)、[主动神器](https://github.com/00-Evan/shattered-pixel-dungeon/blob/master/core/src/main/java/com/shatteredpixel/shatteredpixeldungeon/items/artifacts/EtherealChains.java)和[饰品选择](https://github.com/00-Evan/shattered-pixel-dungeon/blob/master/core/src/main/java/com/shatteredpixel/shatteredpixeldungeon/items/trinkets/TrinketCatalyst.java)。
