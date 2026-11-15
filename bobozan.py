"""《波波攒》终端人机对战原型。"""

from dataclasses import dataclass
from enum import Enum
from random import Random


MAX_ROUNDS = 30


class Move(Enum):
    CHARGE = "攒"
    WAVE = "波"
    GUARD = "防"


@dataclass(frozen=True)
class Fighter:
    hp: int = 3
    energy: int = 0


def legal_moves(fighter: Fighter) -> tuple[Move, ...]:
    if fighter.energy > 0:
        return Move.CHARGE, Move.WAVE, Move.GUARD
    return Move.CHARGE, Move.GUARD


def choose_ai_move(ai: Fighter, player: Fighter, rng: Random) -> Move:
    """Use only the public state at the start of the round."""
    moves = legal_moves(ai)
    weights = {Move.CHARGE: 2, Move.WAVE: 5, Move.GUARD: 0}
    if player.energy > 0:
        weights[Move.GUARD] = 3 if ai.hp == 1 else 1
    if ai.energy == 0 and player.energy == 0:
        return Move.CHARGE
    return rng.choices(moves, weights=[weights[move] for move in moves], k=1)[0]


def resolve_round(
    player: Fighter, ai: Fighter, player_move: Move, ai_move: Move
) -> tuple[Fighter, Fighter]:
    if player_move not in legal_moves(player) or ai_move not in legal_moves(ai):
        raise ValueError("能量不足，无法出波。")

    def settle(fighter: Fighter, move: Move, opponent_move: Move) -> Fighter:
        energy = fighter.energy + (move is Move.CHARGE) - (move is Move.WAVE)
        hit = opponent_move is Move.WAVE and move is not Move.GUARD
        return Fighter(hp=max(0, fighter.hp - hit), energy=energy)

    return settle(player, player_move, ai_move), settle(ai, ai_move, player_move)


def describe_action(before: Fighter, after: Fighter, move: Move) -> str:
    change = "能量 +1" if move is Move.CHARGE else "能量 -1" if move is Move.WAVE else "防守"
    damage = before.hp - after.hp
    return f"{move.value}（{change}，受到 {damage} 点伤害）"


def show_rules() -> None:
    print("\n规则：攒 +1 能量；波消耗 1 能量，造成 1 点伤害；防挡住波。")
    print("双方同时行动，同时出波会互相扣血；双方同时归零为平局。")
    print(f"双方各有 3 点生命，最多 {MAX_ROUNDS} 回合，到时比较剩余生命。")
    print("输入 1/攒、2/波、3/防 出招；h 查看规则；q 退出。")


def play_game(rng: Random) -> str | None:
    """Play one match, returning its result or None when the player quits."""
    player, ai = Fighter(), Fighter()
    commands = {"1": Move.CHARGE, "2": Move.WAVE, "3": Move.GUARD}
    commands.update({move.value: move for move in Move})

    for turn in range(1, MAX_ROUNDS + 1):
        print(f"\n第 {turn} 回合 | 你：{player.hp} 血 / {player.energy} 能量"
              f" | AI：{ai.hp} 血 / {ai.energy} 能量")
        ai_move = choose_ai_move(ai, player, rng)
        available = legal_moves(player)
        options = " / ".join(f"{key} {move.value}" for key, move in commands.items()
                             if key.isdigit() and move in available)
        while True:
            try:
                command = input(f"{options} / q 退出 > ").strip().lower()
            except (EOFError, KeyboardInterrupt):
                print("\n对战结束。")
                return
            if command == "q":
                return
            if command in ("h", "help", "?"):
                show_rules()
                continue
            player_move = commands.get(command)
            if player_move in available:
                break
            print("能量不足，先攒能量才能出波。" if player_move is Move.WAVE
                  else "请选择当前可用的招式，或输入 h 查看规则。")

        previous_player, previous_ai = player, ai
        player, ai = resolve_round(player, ai, player_move, ai_move)
        print(f"你：{describe_action(previous_player, player, player_move)}")
        print(f"AI：{describe_action(previous_ai, ai, ai_move)}")
        print(f"结算：你 {player.hp} 血 / {player.energy} 能量；"
              f"AI {ai.hp} 血 / {ai.energy} 能量。")
        if player.hp == 0 or ai.hp == 0:
            print("\n生命归零，对局结束。")
            break
    else:
        print(f"\n已到 {MAX_ROUNDS} 回合，按剩余生命结算。")

    if player.hp == ai.hp:
        return "平局"
    return "胜利" if player.hp > ai.hp else "失败"


def main() -> None:
    rng = Random()
    scores = {"胜利": 0, "失败": 0, "平局": 0}
    print("《波波攒》终端人机对战")
    show_rules()
    while True:
        result = play_game(rng)
        if result is None:
            break
        scores[result] += 1
        print(f"\n本局：{result}！")
        print(f"本次战绩：{scores['胜利']} 胜 / {scores['失败']} 负 / {scores['平局']} 平")
        while True:
            try:
                command = input("再来一局？[y/回车 继续，q 退出] > ").strip().lower()
            except (EOFError, KeyboardInterrupt):
                print()
                return
            if command in ("", "y"):
                break
            if command in ("q", "n"):
                return
            print("输入 y 或回车开始新对局，输入 q 退出。")


if __name__ == "__main__":
    main()
