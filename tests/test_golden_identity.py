import base64, hashlib, json, os, sys, tempfile, unittest
from pathlib import Path
from unittest import mock
from urllib.error import HTTPError
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/'factory'))
import brand_lock, pipeline

class TestGoldenIdentity(unittest.TestCase):
    def test_locked_assets(self):
        self.assertEqual(brand_lock.verify(),'qiraa-motion-v2-golden-1')
    def test_tampered_logo_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);p=root/'assets/brand';p.mkdir(parents=True)
            (p/'logo.png').write_bytes(b'correct')
            digest=hashlib.sha256(b'correct').hexdigest()
            (p/'brand_manifest.json').write_text(json.dumps({'profile_id':'qiraa-motion-v2-golden-1','files':{'assets/brand/logo.png':digest}}))
            self.assertEqual(brand_lock.verify(root),'qiraa-motion-v2-golden-1')
            (p/'logo.png').write_bytes(b'wrong')
            with self.assertRaisesRegex(ValueError,'verification failed'):brand_lock.verify(root)
    def test_all_sfx_available_and_recipe_present(self):
        self.assertEqual(len(list((ROOT/'assets/sfx_library/audio').rglob('*.wav'))),120)
        self.assertEqual(len(list((ROOT/'assets/sfx_library/audio').rglob('*.mp3'))),120)
        r=json.loads((ROOT/'assets/sfx/recipe_motion_v2.json').read_text())
        self.assertEqual(r['peak_dbfs_each_before_master'],-15.0)
        for item in r['events']:self.assertTrue((ROOT/'assets/sfx'/(item['asset']+'.wav')).is_file())
    def test_elevenlabs_request_mocked(self):
        class Response:
            def __enter__(self):return self
            def __exit__(self,*a):return False
            def read(self,n):return b'ID3'+b'a'*1000
        seen={}
        def fake_open(req,timeout):
            seen['url']=req.full_url;seen['body']=json.loads(req.data)
            self.assertEqual(req.get_header('Xi-api-key'),'test_api_key')
            return Response()
        with tempfile.TemporaryDirectory() as tmp, mock.patch.dict(os.environ,{'ELEVENLABS_API_KEY':'test_api_key','ELEVENLABS_VOICE_ID':'VOICE12345'}), mock.patch.object(pipeline.urllib.request,'urlopen',fake_open):
            p=Path(tmp)/'voice.mp3';pipeline.synthesize_elevenlabs('نص تجريبي',p)
            self.assertTrue(p.read_bytes().startswith(b'ID3'))
            self.assertEqual(seen['body']['model_id'],'eleven_multilingual_v2')
            self.assertEqual(seen['body']['voice_settings']['stability'],0.5)
            self.assertIn('VOICE12345',seen['url'])
            self.assertNotIn('test_api_key',seen['url'])
    def test_no_voice_credentials_does_not_silently_fallback(self):
        with mock.patch.dict(os.environ,{'ELEVENLABS_API_KEY':'','ELEVENLABS_VOICE_ID':''}):
            with self.assertRaisesRegex(ValueError,'not configured'):pipeline.synthesize_elevenlabs('نص',Path('/unused'))
    def test_elevenlabs_error_does_not_print_api_key(self):
        def fail(req,timeout):raise HTTPError(req.full_url,401,'unauthorized',None,None)
        with mock.patch.dict(os.environ,{'ELEVENLABS_API_KEY':'sensitive_test_key','ELEVENLABS_VOICE_ID':'VOICE12345'}), mock.patch.object(pipeline.urllib.request,'urlopen',fail):
            with self.assertRaises(RuntimeError) as exc:pipeline.synthesize_elevenlabs('نص',Path('/unused'))
            self.assertNotIn('sensitive_test_key',str(exc.exception))

if __name__=='__main__':unittest.main()
