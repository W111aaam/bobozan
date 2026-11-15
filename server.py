"""Local browser demo: python3 server.py. Shares combat rules with the CLI."""
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from random import Random
from http.cookies import SimpleCookie
import re
import secrets

from dungeon import Dungeon
from floor import FloorDungeon

from bobozan import Fighter, MAX_ROUNDS, Move, choose_ai_move, resolve_round


class Match:
    def __init__(self):
        self.rng = Random()
        self.scores = {"胜利": 0, "失败": 0, "平局": 0}
        self.version = 0
        self.reset()

    def reset(self):
        self.player, self.ai = Fighter(), Fighter()
        self.turn, self.result, self.last = 1, None, None
        self.version += 1
        self.ai_move = choose_ai_move(self.ai, self.player, self.rng)

    def state(self):
        return dict(player=vars(self.player), ai=vars(self.ai), turn=self.turn,
                    result=self.result, last=self.last, scores=self.scores,
                    version=self.version, maxRounds=MAX_ROUNDS)

    def play(self, move, version):
        if version != self.version or self.result:
            raise ValueError("对局状态已更新，请重新选择。")
        move = Move(move)
        before_player, before_ai = self.player, self.ai
        self.player, self.ai = resolve_round(self.player, self.ai, move, self.ai_move)
        self.last = dict(turn=self.turn, player=move.value, ai=self.ai_move.value,
                         playerDamage=before_player.hp - self.player.hp,
                         aiDamage=before_ai.hp - self.ai.hp)
        if not self.player.hp or not self.ai.hp or self.turn == MAX_ROUNDS:
            self.result = ("平局" if self.player.hp == self.ai.hp else
                           "胜利" if self.player.hp > self.ai.hp else "失败")
            self.scores[self.result] += 1
        else:
            self.turn += 1
            self.ai_move = choose_ai_move(self.ai, self.player, self.rng)
        self.version += 1


class LegacyHandler(BaseHTTPRequestHandler):
    def reply(self, status, data, content_type="application/json; charset=utf-8"):
        body = data if isinstance(data, bytes) else json.dumps(data, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == '/api/state':
            self.reply(200, self.server.match.state())
        elif self.path == '/':
            self.reply(200, Path(__file__).with_name('web').joinpath('index.html').read_bytes(),
                       'text/html; charset=utf-8')
        else:
            self.reply(404, {"error": "未找到页面"})

    def do_POST(self):
        if self.headers.get('Content-Type') != 'application/json':
            return self.reply(415, {"error": "需要 JSON 请求"})
        origin = self.headers.get('Origin')
        if origin and origin != f"http://{self.headers.get('Host')}":
            return self.reply(403, {"error": "只接受本地页面请求"})
        try:
            length = int(self.headers.get('Content-Length', '0'))
            if not 0 < length <= 1024:
                raise ValueError("请求大小无效")
            data = json.loads(self.rfile.read(length))
            if not isinstance(data, dict):
                raise ValueError("请求格式无效")
            if self.path == '/api/play':
                self.server.match.play(data.get('move'), data.get('version'))
            elif self.path == '/api/reset':
                self.server.match.reset()
            else:
                return self.reply(404, {"error": "未找到操作"})
            self.reply(200, self.server.match.state())
        except (ValueError, TypeError) as exc:
            self.reply(400, {"error": str(exc)})


class Handler(LegacyHandler):
    """One persisted adventure per browser cookie; server serializes all mutations."""
    def game(self):
        cookie = SimpleCookie()
        try:
            cookie.load(self.headers.get('Cookie', ''))
        except Exception:
            pass
        sid = cookie['bobozan'].value if 'bobozan' in cookie else ''
        if not re.fullmatch(r'[0-9a-f]{32}', sid):
            sid = secrets.token_hex(16)
        self.sid = sid
        self.save_path = self.server.save_dir / (sid + '.floor.json')
        if self.save_path.exists():
            return FloorDungeon.restore(json.loads(self.save_path.read_text()))
        return FloorDungeon()

    def save(self, game):
        game.archive_result()
        self.server.save_dir.mkdir(parents=True, exist_ok=True)
        temporary = self.save_path.with_suffix('.tmp')
        temporary.write_text(json.dumps(game.dump(), ensure_ascii=False))
        temporary.replace(self.save_path)

    def end_headers(self):
        if hasattr(self, 'sid'):
            self.send_header('Set-Cookie', f'bobozan={self.sid}; HttpOnly; SameSite=Strict; Path=/; Max-Age=2592000')
        self.send_header('X-Content-Type-Options', 'nosniff')
        super().end_headers()

    def do_GET(self):
        if self.path == '/api/state':
            game = self.game()
            self.save(game)
            self.reply(200, game.state())
        elif self.path in ('/', '/app.js', '/style.css', '/art.js'):
            name, mime = {'/': ('index.html', 'text/html'), '/app.js': ('app.js', 'text/javascript'),
                          '/style.css': ('style.css', 'text/css'), '/art.js': ('art.js', 'text/javascript')}[self.path]
            self.reply(200, Path(__file__).with_name('web').joinpath(name).read_bytes(), mime+'; charset=utf-8')
        elif self.path == '/reflect-button.png':
            self.reply(200, Path(__file__).with_name('web').joinpath(self.path[1:]).read_bytes(), 'image/png')
        elif self.path == '/favicon.ico':
            self.reply(204, b'', 'image/x-icon')
        else:
            self.reply(404, {'error': '未找到页面'})

    def do_POST(self):
        if self.headers.get('Content-Type') != 'application/json':
            return self.reply(415, {'error': '需要 JSON 请求'})
        origin = self.headers.get('Origin')
        if origin and origin != f"http://{self.headers.get('Host')}":
            return self.reply(403, {'error': '请求来源不匹配'})
        try:
            length = int(self.headers.get('Content-Length', '0'))
            if not 0 < length <= 2048:
                raise ValueError('请求大小无效')
            data = json.loads(self.rfile.read(length))
            if not isinstance(data, dict):
                raise ValueError('请求格式无效')
            game = self.game()
            if self.path == '/api/reset':
                if data.get('version') != game.version:
                    raise ValueError('局面已更新，请刷新后重试。')
                seed = data.get('seed')
                if seed is not None and (type(seed) is not int or not 0 <= seed < 1_000_000):
                    raise ValueError('种子必须是 0 到 999999 的整数')
                new_game = FloorDungeon(seed, data.get('heroClass'))
                game.archive_result()
                new_game.history = game.history
                new_game.version = game.version + 1
                game = new_game
            elif self.path == '/api/preview':
                if data.get('version') != game.version:
                    raise ValueError('局面已更新，请重新瞄准。')
                return self.reply(200, game.preview_details(data.get('action'), data.get('direction')))
            elif self.path == '/api/path':
                if data.get('version') != game.version:
                    raise ValueError('局面已更新，请重新选择。')
                return self.reply(200, {'path': game.path_to(data.get('target'), data.get('stepOnTrap')), 'version': game.version})
            elif self.path == '/api/action':
                game.act(data.get('action'), data.get('direction'), data.get('version'), data.get('choice'))
            else:
                return self.reply(404, {'error': '未找到操作'})
            self.save(game)
            self.reply(200, game.state())
        except (ValueError, TypeError) as exc:
            self.reply(400, {'error': str(exc)})


def create_server(port=8765, save_dir=None):
    server = HTTPServer(('127.0.0.1', port), Handler)
    server.save_dir = Path(save_dir) if save_dir else Path(__file__).with_name('.saves')
    return server


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='波波攒本地试玩服务')
    parser.add_argument('--port', type=int, default=8765)
    args = parser.parse_args()
    server = create_server(args.port)
    print(f'波波攒地牢试炼：http://127.0.0.1:{server.server_port} （Ctrl+C 停止）', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
