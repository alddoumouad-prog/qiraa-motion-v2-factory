import json, sys, unittest
from pathlib import Path
from unittest import mock
import numpy as np
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/'factory'))
import pipeline

class TestVoiceEngineering(unittest.TestCase):
    def test_original_session_voice_and_processing_profile(self):
        p=pipeline.VOICE_PROFILE
        self.assertEqual(p['approved_provider_for_new_scripts'],'agent_pre_recorded')
        self.assertEqual(p['arena_session_voice_id'],'voice-00')
        self.assertEqual(p['production_voice_id_status'],'arena_session_only')
        self.assertIn('acompressor=',pipeline.VOICE_FILTER)
        self.assertIn('highpass=f=80',pipeline.VOICE_FILTER)
    def test_previous_male_voice_cannot_be_silently_selected(self):
        spec=json.loads((ROOT/'spec.json').read_text());spec['tts']={'provider':'edge','fallback_voice':'ar-MA-JamalNeural'}
        with mock.patch.object(pipeline.Path,'read_text',return_value=json.dumps(spec)):
            with self.assertRaisesRegex(ValueError,'pre_recorded'):pipeline.load_spec('unused')
    def test_voice_processing_decodes_and_is_finite(self):
        x=pipeline.decode(ROOT/'assets/voice/production_voice_reference.mp3',1,pipeline.VOICE_FILTER)
        self.assertGreater(len(x),48000)
        self.assertTrue(np.isfinite(x).all())
        self.assertGreater(float(np.max(np.abs(x))),0.01)
    def test_recorded_clips_do_not_claim_automatic_identity_verification(self):
        self.assertIn('must not be assumed',pipeline.VOICE_PROFILE['voice_id_portability'])

if __name__=='__main__':unittest.main()
