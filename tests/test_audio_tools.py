import importlib.util
import pathlib
import tempfile
import unittest
import numpy as np
import soundfile as sf

ROOT = pathlib.Path(__file__).resolve().parents[1]


class AudioToolsTests(unittest.TestCase):
    def setUp(self):
        helper = ROOT / 'scripts' / 'audio_tools.py'
        self.assertTrue(helper.exists(), 'Audio processing and audit helper has not been implemented')
        spec = importlib.util.spec_from_file_location('audio_tools', helper)
        self.mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.mod)
        self.sr = 48000
        t = np.arange(self.sr) / self.sr
        self.x = .15 * np.sin(2 * np.pi * 220 * t)

    def test_identity_mask_preserves_samples_and_stereo_balance(self):
        stereo = np.column_stack([self.x, self.x * .35])
        y = self.mod.transfer_mask(stereo, self.x, self.sr, 0)
        self.assertEqual(y.shape, stereo.shape)
        np.testing.assert_allclose(y, stereo, atol=1e-9)

    def test_zero_target_does_not_restore_noise(self):
        stereo = np.column_stack([self.x, self.x * .35])
        y = self.mod.transfer_mask(stereo, np.zeros_like(self.x), self.sr, 0)
        np.testing.assert_allclose(y, 0, atol=1e-12)

    def test_shared_mask_preserves_interchannel_relation(self):
        stereo = np.column_stack([self.x, self.x * .35])
        y = self.mod.transfer_mask(stereo, self.x * .5, self.sr, 0)
        np.testing.assert_allclose(y[:, 1], y[:, 0] * .35, atol=1e-9)
        self.assertLess(np.sqrt(np.mean(y ** 2)), np.sqrt(np.mean(stereo ** 2)))

    def test_audit_detects_gain_change_without_normalizing(self):
        with tempfile.TemporaryDirectory() as td:
            a, b = pathlib.Path(td) / 'a.wav', pathlib.Path(td) / 'b.wav'
            sf.write(a, self.x, self.sr, subtype='FLOAT')
            sf.write(b, self.x * .5, self.sr, subtype='FLOAT')
            report = self.mod.audit(a, b, [(0, 1)], False)
            self.assertAlmostEqual(report['solo_target_intervals'][0]['rms_delta_db'][0], -6.0206, places=3)
            self.assertFalse(report['solo_target_intervals'][0]['within_review_thresholds'])
            self.assertEqual(report['pitch_status'], 'not_measured')

    def test_misaligned_audio_cannot_pass_review(self):
        with tempfile.TemporaryDirectory() as td:
            a, b = pathlib.Path(td) / 'a.wav', pathlib.Path(td) / 'b.wav'
            sf.write(a, self.x, self.sr, subtype='FLOAT')
            sf.write(b, self.x[:-100], self.sr, subtype='FLOAT')
            report = self.mod.audit(a, b, [(0, .5)], False)
            self.assertFalse(report['format_matches'])
            self.assertEqual(report['solo_target_intervals'], [])

    def test_output_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as td:
            p = pathlib.Path(td) / 'original.wav'
            sf.write(p, self.x, self.sr, subtype='FLOAT')
            before = p.read_bytes()
            with self.assertRaises(FileExistsError):
                self.mod.write_new_audio(p, self.x, self.sr)
            self.assertEqual(before, p.read_bytes())

    def test_invalid_interval_and_mask_lengths_rejected(self):
        with self.assertRaises(ValueError):
            self.mod.transfer_mask(self.x[:, None], self.x[:-10], self.sr, 0)
        with tempfile.TemporaryDirectory() as td:
            p = pathlib.Path(td) / 'a.wav'
            sf.write(p, self.x, self.sr, subtype='FLOAT')
            with self.assertRaises(ValueError):
                self.mod.audit(p, p, [(0, 2)], False)

    def test_strength_zero_preserves_original(self):
        stereo = np.column_stack([self.x, self.x * .35])
        y = self.mod.transfer_mask(stereo, np.zeros_like(self.x), self.sr, 0, strength=0)
        np.testing.assert_allclose(y, stereo, atol=1e-9)

    def test_invalid_strength_rejected(self):
        with self.assertRaises(ValueError):
            self.mod.transfer_mask(self.x[:, None], self.x, self.sr, 0, strength=1.1)

    def test_model_padding_is_not_assumed_to_be_at_tail(self):
        self.assertTrue(hasattr(self.mod, 'validate_model_length'), 'Strict model alignment guard is missing')
        with self.assertRaises(ValueError):
            self.mod.validate_model_length(np.zeros(self.sr + 100), self.sr)
        with self.assertRaises(ValueError):
            self.mod.validate_model_length(np.zeros(self.sr - 100), self.sr)
        self.mod.validate_model_length(self.x, self.sr)


if __name__ == '__main__':
    unittest.main(verbosity=2)
