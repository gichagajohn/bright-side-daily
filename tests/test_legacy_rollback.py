import unittest
from unittest.mock import patch
from pathlib import Path
from bsd.legacy_schedule import slot_for
from bsd.common import config

class RollbackTests(unittest.TestCase):
    def test_delayed_cron_keeps_slot(self):
        self.assertEqual(slot_for('0 5 * * *'),'morning_motivation')
        self.assertEqual(slot_for('0 10 * * *'),'midday_encouragement')
    def test_unknown_cron_rejected(self):
        with self.assertRaises(ValueError): slot_for('0,30 * * * *')
    def test_config_matches_crons(self):
        from bsd.legacy_schedule import SLOTS
        cfg=config()
        self.assertEqual(cfg['reel_renderer'],'legacy')
        self.assertEqual(sum(s['format']=='REELS' for s in cfg['slots']),3)
        for h, name in SLOTS.items():
            s=next(s for s in cfg['slots'] if s['name']==name)
            self.assertEqual(s['time'],f'{h+3:02d}:00')
    def test_narration_failure_withheld(self):
        from generators import reel_generator as legacy
        from bsd.legacy_reels import render_legacy
        def generate(*args,**kwargs): return legacy._speak('A quote')
        with patch.object(legacy,'_speak',return_value=None),patch.object(legacy,'generate',side_effect=generate):
            with self.assertRaisesRegex(RuntimeError,'narration unavailable'):
                render_legacy({'content':'A quote'},Path('/tmp'))
    def test_no_output_withheld(self):
        from generators import reel_generator as legacy
        from bsd.legacy_reels import render_legacy
        with patch.object(legacy,'generate',return_value=None):
            with self.assertRaisesRegex(RuntimeError,'no video'):
                render_legacy({'content':'A quote'},Path('/tmp'))

    def test_kenyan_voice_required(self):
        from generators import reel_generator as legacy
        from bsd.legacy_reels import render_legacy
        def generate(*args, **kwargs):
            legacy._speak('A quote')
            return None
        with patch.object(legacy, '_speak', return_value=('voice.mp3', [(0,'A')])) as speak, patch.object(legacy, 'generate', side_effect=generate):
            with self.assertRaisesRegex(RuntimeError, 'no video'):
                render_legacy({'content':'A quote'}, Path('/tmp'))
            speak.assert_called_once_with('A quote', voice='en-KE-ChilembaNeural', rate='+0%', strict=True)
