import sys,tempfile,unittest,subprocess
from pathlib import Path
import cv2
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/'factory'))
import outro_cache,render_motion

class TestOutroReuse(unittest.TestCase):
    def test_approved_outro_is_compatible(self):
        info=outro_cache.check_asset()
        self.assertEqual(info['frames'],135);self.assertEqual(info['duration_seconds'],4.5)
        self.assertEqual(outro_cache.MAIN_FRAMES,705)
        self.assertEqual(outro_cache.MAIN_FRAMES+outro_cache.OUTRO_FRAMES,840)
    def test_missing_or_invalid_outro_stops_instead_of_regenerating(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaisesRegex(ValueError,'missing'):outro_cache.check_asset(Path(d)/'missing.mp4')
            invalid=Path(d)/'broken.mp4';invalid.write_text('invalid')
            with self.assertRaises(ValueError):outro_cache.check_asset(invalid)
    def test_concat_copies_streams_at_boundary_and_decodes_all_frames(self):
        with tempfile.TemporaryDirectory() as d:
            a=Path(d)/'main.mp4';b=Path(d)/'outro.mp4';dest=Path(d)/'joined.mp4'
            for target,color,seconds in [(a,'black','1'),(b,'white','0.5')]:
                subprocess.run([render_motion.ffmpeg(),'-y','-hide_banner','-loglevel','error','-f','lavfi','-i',f'color=c={color}:s=160x240:r=30:d={seconds}','-an','-c:v','libx264','-preset','fast','-crf','18','-pix_fmt','yuv420p','-movflags','+faststart',str(target)],check=True)
            outro_cache.concat(a,b,dest)
            cap=cv2.VideoCapture(str(dest));decoded=[]
            while True:
                ok,frame=cap.read()
                if not ok:break
                decoded.append(frame.mean())
            cap.release()
            self.assertEqual(len(decoded),45)
            self.assertLess(decoded[29],10);self.assertGreater(decoded[30],245)
            subprocess.run([render_motion.ffmpeg(),'-v','error','-i',str(dest),'-f','null','-'],check=True)

if __name__=='__main__':unittest.main()
