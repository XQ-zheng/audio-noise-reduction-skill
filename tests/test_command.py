import pathlib
import subprocess
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]


class CommandTests(unittest.TestCase):
    def test_requested_command_reaches_processing_help(self):
        launcher = ROOT / 'scripts' / 'audio_command.py'
        self.assertTrue(launcher.exists(), 'Requested command has not been implemented')
        result = subprocess.run([sys.executable, str(launcher), 'noise', 'reduction',
                                 'skill', '--help'], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('--backend', result.stdout)
        self.assertIn('--strength', result.stdout)

    def test_invalid_command_does_not_start_processing(self):
        launcher = ROOT / 'scripts' / 'audio_command.py'
        self.assertTrue(launcher.exists(), 'Requested command has not been implemented')
        result = subprocess.run([sys.executable, str(launcher), 'noise', 'wrong',
                                 'skill'], capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)


if __name__ == '__main__':
    unittest.main()
