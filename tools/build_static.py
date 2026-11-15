"""Build a playable, server-free site from the shared Bobozan engine."""
import argparse
from pathlib import Path
from shutil import copyfile


def build(destination):
    root = Path(__file__).resolve().parents[1]
    web = root / 'web'
    engine = destination / 'engine'
    engine.mkdir(parents=True, exist_ok=True)
    for name in ('app.js', 'style.css', 'art.js', 'static-api.js', 'static-worker.js', 'reflect-button.png'):
        copyfile(web / name, destination / name)
    for name in ('dungeon', 'encounters', 'enemy_design', 'floor', 'growth', 'layout', 'mechanics'):
        copyfile(root / f'{name}.py', engine / f'{name}.py')
    copyfile(root / 'tools/static_game.py', engine / 'static_game.py')
    html = (web / 'index.html').read_text()
    html = html.replace('href="/style.css"', 'href="./style.css"').replace('src="/', 'src="./')
    html = html.replace('<script src="./app.js"', '<script src="./static-api.js" defer></script><script src="./app.js"')
    html = html.replace('</head>', '<link rel="icon" href="data:,"></head>')
    (destination / 'index.html').write_text(html)
    (destination / '.nojekyll').touch()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('destination', type=Path)
    build(parser.parse_args().destination)
