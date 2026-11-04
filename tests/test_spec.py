import copy, json, tempfile, unittest
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/'factory'))
import pipeline

class TestSpec(unittest.TestCase):
    def setUp(self):self.spec=json.loads((ROOT/'spec.json').read_text(encoding='utf-8'))
    def validate(self,s):
        with tempfile.NamedTemporaryFile(mode='w',encoding='utf-8',suffix='.json',delete=False) as f:
            json.dump(s,f,ensure_ascii=False);name=f.name
        try:return pipeline.load_spec(name)
        finally:Path(name).unlink()
    def test_golden_spec(self):self.assertEqual(self.validate(self.spec)['project_id'],'space-voting-gold')
    def test_unsafe_url(self):
        self.spec['source_url']='file:///etc/passwd'
        with self.assertRaisesRegex(ValueError,'http'):self.validate(self.spec)
    def test_micro_overlap(self):
        self.spec['narration'][1]['start']=6.0
        with self.assertRaisesRegex(ValueError,'overlap'):self.validate(self.spec)
    def test_word_anchor(self):
        self.spec['micro'][0]['anchor_word']='invented'
        with self.assertRaisesRegex(ValueError,'not found'):self.validate(self.spec)
    def test_card_overlap_with_micro(self):
        self.spec['cards'][0]['start']=6.0
        with self.assertRaisesRegex(ValueError,'obscure'):self.validate(self.spec)
    def test_unverified_facts(self):
        self.spec['editorial_review']['facts_verified']=False
        with self.assertRaisesRegex(ValueError,'verified'):self.validate(self.spec)
    def test_path_traversal(self):
        self.spec['transcript_file']='../../etc/passwd'
        with self.assertRaisesRegex(ValueError,'inside'):self.validate(self.spec)
    def test_duplicate_id(self):
        self.spec['micro'][0]['id']=self.spec['micro'][1]['id']
        with self.assertRaisesRegex(ValueError,'unique'):self.validate(self.spec)
    def test_micro_duration_under_two(self):
        self.spec['micro'][0]['max_seconds']=2
        with self.assertRaisesRegex(ValueError,'less than 2'):self.validate(self.spec)
    def test_source_fade_filter_decodes(self):
        import numpy as np
        from scipy.io import wavfile
        with tempfile.NamedTemporaryFile(suffix='.wav') as f:
            wavfile.write(f.name,48000,(np.sin(np.arange(48000)*.04)*.1).astype(np.float32))
            x=pipeline.decode(Path(f.name),2,'afade=t=out:st=0.75:d=0.25')
            self.assertGreater(float(np.max(np.abs(x))),.05)

if __name__=='__main__':unittest.main()
