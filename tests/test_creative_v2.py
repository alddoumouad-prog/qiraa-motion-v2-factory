import copy,json,sys,tempfile,unittest
from pathlib import Path
from unittest import mock
import cv2,numpy as np
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/'factory'))
import creative_plan,framing,render_motion,adaptive_motion,pipeline

def plan(mode='quote'):
    return {'mode':mode,'angle':'الزاوية التحريرية الخاصة بهذا المصدر',
            'reason':'اختيار مناسب لطبيعة القصة','hook_type':'quote',
            'crop':'auto','card_position':'auto'}

class TestCreativePlan(unittest.TestCase):
    def setUp(self):self.spec=json.loads((ROOT/'spec.json').read_text())
    def test_legacy_defaults_preserve_golden(self):
        p=creative_plan.validate(self.spec)
        self.assertEqual((p['mode'],p['crop'],p['card_position']),('golden','center','lower'))
    def test_auto_selection_uses_explicit_hook_not_fabricated_facts(self):
        self.spec['creative']=plan('auto');self.assertEqual(creative_plan.validate(self.spec)['mode'],'quote')
        self.spec['creative']['hook_type']='visual';self.assertEqual(creative_plan.validate(self.spec)['mode'],'scene')
        self.spec['creative']['hook_type']='question';self.assertEqual(creative_plan.validate(self.spec)['mode'],'context')
    def test_missing_angle_is_rejected(self):
        self.spec['creative']=plan();del self.spec['creative']['angle']
        with self.assertRaisesRegex(ValueError,'creative.angle'):creative_plan.validate(self.spec)
    def test_invalid_mode_crop_and_extra_fields_rejected(self):
        for field,value in [('mode','unsafe'),('crop','arbitrary'),('card_position','unsafe'),('new_key','unknown')]:
            self.spec['creative']=plan();self.spec['creative'][field]=value
            with self.subTest(field=field),self.assertRaises(ValueError):creative_plan.validate(self.spec)
    def test_pipeline_rejects_unverified_creative_plan(self):
        self.spec['creative']=plan();self.spec['creative']['reason']=''
        with tempfile.NamedTemporaryFile(mode='w',suffix='.json',encoding='utf8',delete=False) as f:
            json.dump(self.spec,f,ensure_ascii=False);path=f.name
        try:
            with self.assertRaisesRegex(ValueError,'creative.reason'):pipeline.load_spec(path)
        finally:Path(path).unlink()
    def test_crop_projection_and_interpolation(self):
        self.assertEqual(framing.desired_centering(1280,720,0),0.)
        self.assertEqual(framing.desired_centering(1280,720,1280),1.)
        track=[{'time':1,'x':.2},{'time':3,'x':.8}]
        self.assertAlmostEqual(framing.centering_at(2,track),.5)
        self.assertAlmostEqual(framing.centering_at(0,track),.2)
        self.assertAlmostEqual(framing.overlap_fraction((0,0,100,100),(50,0,100,100)),.5)
    def test_sampled_face_overlap_is_only_a_warning_not_a_guarantee(self):
        boxes=[{'time':1.5,'projected':(600,120,120,120)}]
        events=framing.overlaps(boxes,self.spec,'context','lower')
        self.assertTrue(any(e['region']=='brand' for e in events))
        opposite=framing.overlaps(boxes,self.spec,'context','lower',brand_position='left')
        self.assertFalse(any(e['region']=='brand' for e in opposite))

class TestCreativeRenderer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory();cls.source=str(Path(cls.temp.name)/'source.avi')
        out=cv2.VideoWriter(cls.source,cv2.VideoWriter_fourcc(*'MJPG'),30,(320,180))
        if not out.isOpened():raise unittest.SkipTest('OpenCV MJPG encoder unavailable')
        frame=np.zeros((180,320,3),np.uint8);frame[:,:107]=(30,40,210);frame[:,107:213]=(40,160,70);frame[:,213:]=(200,80,30)
        for _ in range(125):out.write(frame)
        out.release();cls.spec=json.loads((ROOT/'spec.json').read_text())
    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()
    def analysis(self):return {'crop_centering_x':.5,'crop_track':[],'card_position':'lower','brand_position':'right','metadata_position':'right'}
    def test_golden_frame_pixels_match_original_renderer(self):
        original=render_motion.make_renderer(self.source,self.spec);original.credit=original.make_credit()
        new=adaptive_motion.make_renderer(self.source,self.spec,creative_plan.validate(self.spec),self.analysis())
        try:
            for t in (.15,1.35,3.0,8.2,21.9,26.2):
                with self.subTest(t=t):self.assertTrue(np.array_equal(np.array(original.render(t)),np.array(new.render(t))))
        finally:original.src.close();new.src.close()
    def test_new_layouts_are_visibly_distinct_and_keep_brand_asset(self):
        arrays=[]
        for mode in ('quote','scene','context'):
            spec=copy.deepcopy(self.spec);spec['creative']=plan(mode);p=creative_plan.validate(spec)
            r=adaptive_motion.make_renderer(self.source,spec,p,self.analysis())
            try:
                self.assertEqual(r.icon.tobytes(),render_motion.Image.open(ROOT/'assets/brand/logo_icon.png').convert('RGBA').tobytes())
                arrays.append(np.array(r.render(1.35)))
                self.assertEqual(r.render(8.2).size,(1080,1920))
            finally:r.src.close()
        for i in range(len(arrays)):
            for j in range(i+1,len(arrays)):self.assertFalse(np.array_equal(arrays[i],arrays[j]))
    def test_moved_brand_preserves_exact_logo_pixels(self):
        spec=copy.deepcopy(self.spec);spec['creative']=plan();p=creative_plan.validate(spec)
        a=self.analysis();r=adaptive_motion.make_renderer(self.source,spec,p,a);a2=dict(a,brand_position='left');r2=adaptive_motion.make_renderer(self.source,spec,p,a2)
        try:self.assertEqual(r.brand_layer.crop((540,0,1001,1920)).tobytes(),r2.brand_layer.crop((80,0,541,1920)).tobytes())
        finally:r.src.close();r2.src.close()
    def test_detector_failure_centers_without_false_confidence(self):
        spec=copy.deepcopy(self.spec);spec['creative']=plan()
        class MissingDetector:
            def empty(self):return True
        with mock.patch.object(framing.cv2,'CascadeClassifier',return_value=MissingDetector()):
            result=framing.analyze(self.source,spec,creative_plan.validate(spec))
        self.assertEqual(result['crop_centering_x'],.5)
        self.assertFalse(result['detector_available'])
        self.assertTrue(any('manual review' in x for x in result['warnings']))

if __name__=='__main__':unittest.main()
