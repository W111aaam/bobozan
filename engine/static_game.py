"""Adapt the game simulation to the browser worker's JSON protocol."""
import json

from floor import FloorDungeon


def dispatch(path, payload, save):
    game = FloorDungeon.restore(json.loads(save)) if save else FloorDungeon()
    data = json.loads(payload)
    try:
        if path != 'state' and data.get('version') != game.version:
            raise ValueError('局面已更新，请重新选择。')
        if path == 'path':
            return json.dumps(dict(result=game.path_details(data.get('target'), data.get('stepOnTrap'),
                                                            forecast=data.get('forecast') is True)))
        if path == 'preview':
            return json.dumps(dict(result=game.preview_details(data.get('action'), data.get('direction'),
                                                               data.get('choice'))))
        if path == 'action':
            game.act(data.get('action'), data.get('direction'), game.version, data.get('choice'))
        elif path == 'reset':
            seed = data.get('seed')
            if seed is not None and (type(seed) is not int or not 0 <= seed < 1_000_000):
                raise ValueError('种子必须是 0 到 999999 的整数')
            game.archive_result()
            new_game = FloorDungeon(seed, data.get('heroClass'))
            new_game.history = game.history
            new_game.version = game.version + 1
            game = new_game
        elif path != 'state':
            raise ValueError('未找到操作')
    except (ValueError, TypeError) as error:
        return json.dumps(dict(error=str(error)))
    game.archive_result()
    return json.dumps(dict(result=game.state(), save=json.dumps(game.dump())))
