"""HTTP integration tests. Bind only an ephemeral loopback port."""
import json
import tempfile
import threading
import unittest
from pathlib import Path
from http.cookiejar import CookieJar
from urllib.request import build_opener, HTTPCookieProcessor, Request
from urllib.error import HTTPError
from server import create_server


class HTTPTests(unittest.TestCase):
    def setUp(self):
        self.directory=tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.start()
        self.addCleanup(self.stop)
        self.client=build_opener(HTTPCookieProcessor(CookieJar()))

    def start(self):
        self.server=create_server(0,self.directory.name)
        self.server.RequestHandlerClass.log_message=lambda *args: None
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True)
        self.thread.start()
        self.url=f'http://127.0.0.1:{self.server.server_port}'

    def stop(self):
        self.server.shutdown();self.server.server_close();self.thread.join()

    def call(self,path='state',data=None,client=None):
        req=Request(self.url+'/api/'+path, data=json.dumps(data).encode() if data is not None else None,
                    headers={'Content-Type':'application/json'} if data is not None else {})
        with (client or self.client).open(req,timeout=3) as response:
            return json.load(response)

    def test_independent_clients_and_refresh(self):
        a=self.call();other=build_opener(HTTPCookieProcessor(CookieJar()));b=self.call(client=other)
        a=self.call('action',dict(action='charge',version=a['version']))
        self.assertEqual(a['turn'],1)
        self.assertEqual(self.call(client=other),b)
        self.assertEqual(self.call(),a)

    def test_rejects_stale_and_malformed_without_mutating(self):
        a=self.call()
        for data in [[],dict(action='wave',direction='right',version=a['version']),dict(action='guard',version=-1)]:
            with self.assertRaises(HTTPError) as err:self.call('action',data)
            self.assertEqual(err.exception.code,400)
            err.exception.close()
            self.assertEqual(self.call(),a)

    def test_persistence_after_server_restart(self):
        a=self.call();a=self.call('action',dict(action='charge',version=a['version']))
        self.stop();self.start()
        self.assertEqual(self.call(),a)

    def test_full_adventure_through_real_api(self):
        a=self.call();a=self.call('reset',dict(version=a['version'],seed=0))
        actions=json.loads(Path(__file__).with_name('tools').joinpath('floor_replay.json').read_text())
        seen={1}
        for command in actions:
            a=self.call('action',dict(**command,version=a['version']))
            seen.add(a['depth'])
        self.assertEqual(a['result'],'victory')
        self.assertEqual(seen,set(range(1, 27)))
        record, = a['history']
        self.assertEqual((record['result'], record['depth'], record['turns']), ('victory', 26, a['turn']))
        self.assertEqual(self.call(),a)
        retry = self.call('reset', dict(version=a['version'], seed=record['seed'], heroClass=record['heroClass']))
        self.assertEqual(retry['history'], [record])
        self.assertEqual(retry['depth'], 1)

    def test_floor_path_request_is_read_only(self):
        a=self.call();a=self.call('reset',dict(version=a['version'],seed=0))
        response=self.call('path',dict(version=a['version'],target=[a['player']['x']+1,a['player']['y']]))
        self.assertEqual(response['path'],['right'])
        response=self.call('path',dict(version=a['version'],target=[a['player']['x']+1,a['player']['y']],forecast=True))
        self.assertEqual(response['sanityForecast']['end'],a['sanity'])
        self.assertEqual(self.call(),a)

    def test_legacy_save_is_not_overwritten(self):
        a=self.call()
        current=next(Path(self.directory.name).glob('*.floor.json'))
        legacy=current.with_name(current.name.replace('.floor.json','.json'))
        legacy.write_text('{"legacy":true}')
        self.call('action',dict(action='charge',version=a['version']))
        self.assertEqual(legacy.read_text(),'{"legacy":true}')

    def test_origin_and_static_assets(self):
        self.call()
        req=Request(self.url+'/api/reset',data=b'{}',headers={'Content-Type':'application/json','Origin':'https://unrelated.example'})
        with self.assertRaises(HTTPError) as err:self.client.open(req)
        self.assertEqual(err.exception.code,403)
        err.exception.close()
        for path,mime in [('/','text/html'),('/app.js','text/javascript'),('/art.js','text/javascript'),('/style.css','text/css')]:
            with self.client.open(self.url+path) as res:
                self.assertEqual(res.status,200)
                self.assertIn(mime,res.headers['Content-Type'])


if __name__=='__main__':unittest.main()
