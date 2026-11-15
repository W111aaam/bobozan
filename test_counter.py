import unittest
from test_dungeon import arena, act, enemy
from dungeon import Dungeon

class CounterTests(unittest.TestCase):
    def block(self,g):
        g.enemies[0]['intent']=dict(action='melee',cells=[[g.player['x'],g.player['y']]])
        act(g,'guard')

    def test_real_block_only_and_no_stacking(self):
        g=arena();act(g,'guard');self.assertFalse(g.counter)
        self.block(g);self.block(g)
        self.assertTrue(g.counter)
        g.enemies[0]['hp']=4;g.enemies[0]['intent']=dict(action='wait',cells=[])
        act(g,'wave','right')
        self.assertEqual(g.enemies[0]['hp'],2)
        self.assertFalse(g.counter)

    def test_preserved_on_movement_charge_and_invalid_shot(self):
        g=arena();self.block(g)
        act(g,'move','down');act(g,'charge')
        self.assertTrue(g.counter)
        with self.assertRaises(ValueError):act(g,'wave','invalid')
        self.assertTrue(g.counter)
        act(g,'wave','left')
        self.assertFalse(g.counter)

    def test_heavy_and_enemy_guard(self):
        g=arena();self.block(g);g.upgrades=['heavy'];g.player['energy']=3
        g.enemies[0].update(hp=4,intent=dict(action='guard',cells=[]))
        act(g,'heavy','right')
        self.assertEqual(g.enemies[0]['hp'],2) # 2 base + 1 counter - 1 shield

    def test_heart_still_triggers_and_room_clears_counter(self):
        g=arena();g.upgrades=['heart'];g.player['hp']=3
        self.block(g)
        self.assertEqual(g.player['hp'],4)
        self.assertTrue(g.counter)
        g.enter_room();self.assertFalse(g.counter)

    def test_save_roundtrip_and_old_save_migration(self):
        g=arena();self.block(g)
        self.assertTrue(Dungeon.restore(g.dump()).counter)
        old=g.dump();del old['counter']
        self.assertFalse(Dungeon.restore(old).counter)

if __name__=='__main__':unittest.main()
