"""Original, deterministic adaptations of enemy roles from Shattered Pixel Dungeon."""
from random import Random

# Name, inspection text, base HP, maximum attack.
ENEMY_DESIGNS = {
    'slipsnake': ('滑鳞蛇', '每三拍可侧移躲开直线波，青色虚线标记去向。贴近后会咬锁定的一格。可用扇形波覆盖侧移，或等它扑咬再打。', 2, 1),
    'rushcrab': ('疾钳蟹', '从同一直线锁定至多两格外的空地，再直冲过去；相邻时挥钳。冲刺本身不伤人，趁它靠近时侧移或准备反击。', 3, 1),
    'boneburst': ('爆骨卫', '相邻时攻击。死亡后标出尸体和四邻格，下一拍碎骨爆发，造成 1 伤；门和墙可挡住碎片。', 2, 1),
    'splitcloud': ('分裂群', '被打伤且剩至少 5 生命时，分出一个 4 血子群。每群最多分裂一次，子群不再分裂。', 4, 1),
    'drainbat': ('汲血蝠', '近身咬击实际伤到你才恢复 2 生命。格挡能同时防伤和阻止吸血。', 2, 1),
    'arcshaman': ('棱晶萨满', '先攒，再发射覆盖两格纵深的扇波。挡住可获得反击，反射也能将波打回去。', 2, 1),
    'nullmage': ('蚀能术士', '先攒，再沿直线发射吸能波。只有实际造成伤害才额外抽走 1 能量，防或反射可阻止。', 2, 1),
    'pulsemate': ('静拳武僧', '循环架势、进攻、露出空档。架势抵挡 2 波伤，相邻时使用震拳。', 2, 2),
    'blinkgolem': ('折跃石像', '锁定房间内一处可见空地，下一拍折跃过去，之后休整一拍。折跃不能跨过门墙，落点被争抢时失败。', 3, 1),
    'siegeeye': ('灼瞳', '直线看到你时蓄力，提前标出射线；下拍沿原线发射长波，然后休整。可提前离开射线或利用墙门。', 3, 2),
    'barbscorp': ('棘尾蝎', '攒力后沿直线发射长尾针；贴身时会试图撤向房间内部。封住退路，或从两格外引它射击再反击。', 2, 1),
    'leapripper': ('裂步魔', '锁定离你很近的空地跃入，再扫击相邻格，随后休整。移出落点附近，或用冰冻取消跃进。', 2, 1),
}

# Introduce a region's basic threats before combining its special abilities.
REGIONAL_ROSTERS = (
    (('ram', 'slipsnake'), ('slipsnake', 'charger', 'ram'),
     ('rushcrab', 'charger', 'ram'), ('rushcrab', 'slipsnake', 'charger')),
    (('boneburst', 'charger', 'boneburst'), ('boneburst', 'escort', 'charger'),
     ('escort', 'splitcloud', 'boneburst'), ('splitcloud', 'escort', 'charger')),
    (('drainbat', 'ram', 'arcshaman'), ('arcshaman', 'drainbat', 'ram', 'boneburst'),
     ('arcshaman', 'boneburst', 'drainbat', 'ram'), ('arcshaman', 'drainbat', 'twin', 'twin')),
    (('nullmage', 'shield', 'pulsemate'), ('pulsemate', 'nullmage', 'shield', 'blinkgolem'),
     ('blinkgolem', 'pulsemate', 'nullmage', 'shield'), ('blinkgolem', 'nullmage', 'twin', 'twin')),
    (('leapripper', 'nullmage', 'barbscorp'), ('siegeeye', 'barbscorp', 'leapripper', 'nullmage'),
     ('barbscorp', 'siegeeye', 'leapripper', 'nullmage'), ('siegeeye', 'leapripper', 'barbscorp', 'nullmage')),
)


def regional_roster(seed, depth, region):
    first, *group = REGIONAL_ROSTERS[region][(depth - 1) % 5]
    guards = [(1, first)]
    if depth % 5 == 4:
        guards.append((1, group.pop(0)))
    Random(seed + depth * 7207).shuffle(group)
    return guards + [(4, kind) for kind in group]

# Repeated entries make the area's basic enemies more common than specialists.
REINFORCEMENTS = (
    ('ram', 'ram', 'slipsnake', 'charger', 'rushcrab'),
    ('boneburst', 'boneburst', 'charger', 'escort', 'splitcloud'),
    ('drainbat', 'drainbat', 'arcshaman', 'ram', 'boneburst'),
    ('nullmage', 'shield', 'pulsemate', 'blinkgolem'),
    ('leapripper', 'leapripper', 'nullmage', 'barbscorp', 'siegeeye'),
)

# Percentage chance and terrain feature to drop. Limited separately from room rewards.
FIXED_ENEMY_LOOT = {'armedidol': 'rune_shard', 'chestmimic': 'kit'}
BOSS_KINDS = ('boss', 'breaker', 'mirrorboss')
ENEMY_LOOT = {
    'ram': (20, 'lure_cache'), 'slipsnake': (30, 'grass_seed'),
    'rushcrab': (30, 'dew'), 'charger': (25, 'smoke'),
    'boneburst': (25, 'grass_seed'), 'escort': (30, 'smoke'),
    'splitcloud': (25, 'dew'), 'drainbat': (18, 'kit'),
    'arcshaman': (30, 'grass_seed'), 'nullmage': (30, 'smoke'),
    'pulsemate': (30, 'dew'), 'blinkgolem': (30, 'echo_smoke'),
    'leapripper': (25, 'grass_seed'), 'barbscorp': (30, 'smoke'),
    'siegeeye': (35, 'echo_smoke'), 'canalfish': (25, 'dew'),
}

ENEMY_DESIGNS.update({
    'sparkthief': ('拾能贼', '贴身打伤你后偷走 1 能量，随后带着能量逃向门口。格挡可阻止偷窃，击倒后可捡回能量。', 2, 1),
    'bonesummoner': ('召骨师', '提前标记落点，两拍召出 1 只骨傀儡；施法期间受伤或结算时落点被占都会失败。随后用直线波掩护骨兵。', 3, 1),
    'magnetguard': ('磁钩守卫', '沿直线蓄能发钩，命中且造成伤害时拉近一格。门、反弹和格挡都能阻止拉拽。', 3, 1),
    'webspinner': ('织网蛛', '在你脚下预告落网，再用直线毒针攻击。网格限制飞雷神和敌人特殊位移，可用波割断。毒针打伤后下拍再受 1 伤。', 3, 1),
    'elementcore': ('元素核', '火核点燃高草，霜核预告结冰地面，电核可用镜面折射长波，电波也会沿相连的浅水导电。点击查看当前元素和招式。', 3, 1),
    'armedidol': ('武器石像', '受伤后苏醒。可先查看它的发射器和刻印，准备好再交战。', 3, 1),
    'mirrorwraith': ('镜魇', '标出真假两个倒影，青色虚线指向真正的落点。占住落点可打断闪现，落地后会有一拍空档。', 3, 1),
    'chestmimic': ('拟态宝箱', '异常的宝箱会微微起伏。靠近或打中会揭开伪装，先警觉一拍，再扑咬。击败后留下补给。', 3, 1),
    'broodnest': ('裂魔产巢', '察觉玩家后才开始孵化。两拍孵出一只裂魔，场上最多两只，每巢最多孵三只。受伤可打断孵化。', 4, 0),
    'canalfish': ('沟渠鱼', '只能在水格活动，在相邻格扑咬。可以从岸上用波消灭，或者绕过水池。', 2, 1),
    'bonepuppet': ('骨傀儡', '由召骨师召出，靠近后挥击。身体可以挡住直线波。', 1, 1),
    'broodling': ('裂魔幼体', '产巢孵出的幼体。接近后挥击，产巢倒下后仍需处理场上的幼体。', 1, 1),
})

SIDE_ENCOUNTERS = (
    ('canalfish', 'chestmimic', 'sparkthief', 'canalfish'),
    ('sparkthief', 'bonesummoner', 'magnetguard', 'chestmimic'),
    ('webspinner', 'elementcore', 'armedidol', 'webspinner'),
    ('magnetguard', 'bonesummoner', 'armedidol', 'elementcore'),
    ('broodnest', 'mirrorwraith', 'elementcore', 'broodnest'),
)

def enemy_health(kind, depth, boss_arena=False):
    region = min(4, (depth - 1) // 5)
    if kind in BOSS_KINDS:
        return (36, 48, 60, 72, 84)[region]
    if kind in ('bonepuppet', 'broodling'):
        return 4 + region
    if boss_arena:
        return 8 + 4 * region
    base = ENEMY_DESIGNS[kind][2] if kind in ENEMY_DESIGNS else (3 if kind in ('shield', 'escort') else 2)
    if kind == 'broodnest':
        return 18 + 3 * region
    if kind == 'canalfish':
        return 8 + 3 * region
    late_floor = (depth - 1) % 5 in (2, 3)
    durable = kind in ('rushcrab', 'escort', 'splitcloud', 'blinkgolem', 'siegeeye')
    return 3 * base + 2 + 4 * region + 3 * (late_floor and durable)


def enemy_damage(power, depth):
    """Convert attack strength to HP damage, with a steady regional increase."""
    if not power:
        return 0
    return 2 * power + 1 + min(4, (depth - 1) // 5)

# Stronger attacks are limited to readable, named moves rather than every hit.
def enemy_attack_bonus(kind, depth, action):
    if kind == 'ram' and action == 'melee':
        return 1
    if kind in ('rushcrab', 'escort') and action == 'melee':
        return 1
    if kind == 'charger' and action == 'wave':
        return 1
    if kind == 'leapripper' and depth >= 24 and action == 'melee':
        return 1
    if kind == 'breaker' and depth >= 15 and action == 'siege':
        return 1
    if kind == 'boss' and depth >= 20 and action == 'area':
        return 1
    if kind == 'siegeeye' and depth >= 23 and action == 'special_wave':
        return 1
    return 0
