"""Audio fidelity measurements and shared attenuation masks; no normalization."""
import argparse
import json
from pathlib import Path
import numpy as np
import soundfile as sf
from scipy import signal
from scipy.ndimage import uniform_filter1d


def db(value):
    return 20 * np.log10(np.maximum(np.asarray(value, dtype=float), 1e-12))


def stft(x, sr):
    size = min(2048, len(x))
    if size < 4:
        raise ValueError('Audio must contain at least four samples')
    return signal.stft(x, fs=sr, nperseg=size, noverlap=size * 3 // 4,
                       boundary='zeros', padded=True)


def transfer_mask(original, estimate, sr, analysis_channel=0, strength=1.0):
    """Apply one nonnegative, <=1 real mask to every original channel."""
    original = np.asarray(original, dtype=np.float64)
    estimate = np.asarray(estimate, dtype=np.float64).reshape(-1)
    if not np.isfinite(strength) or not 0 <= strength <= 1:
        raise ValueError('Strength must be between zero and one')
    if original.ndim != 2 or len(original) != len(estimate):
        raise ValueError('Estimate must align exactly with [samples, channels] input')
    if not 0 <= analysis_channel < original.shape[1]:
        raise ValueError('Invalid analysis channel')
    if not np.isfinite(original).all() or not np.isfinite(estimate).all():
        raise ValueError('Nonfinite audio')
    if strength == 0:
        return original.copy()
    _, _, source = stft(original[:, analysis_channel], sr)
    _, _, target = stft(estimate, sr)
    magnitude = np.abs(source)
    mask = np.clip(np.abs(target) / np.maximum(magnitude, 1e-12), 0, 1)
    # Silence/padded frames must not drag the neighboring identity mask down.
    weights = uniform_filter1d(magnitude, size=3, axis=1, mode='nearest')
    weighted = uniform_filter1d(mask * magnitude, size=3, axis=1, mode='nearest')
    mask = np.clip(weighted / np.maximum(weights, 1e-12), 0, 1)
    mask = 1 - strength * (1 - mask)
    channels = []
    size = min(2048, len(original))
    for ch in original.T:
        _, _, z = stft(ch, sr)
        _, y = signal.istft(z * mask, fs=sr, nperseg=size,
                            noverlap=size * 3 // 4, boundary=True)
        channels.append(y[:len(original)])
    return np.column_stack(channels)


def read_audio(path):
    x, sr = sf.read(str(path), dtype='float64', always_2d=True)
    if len(x) < 4 or not np.isfinite(x).all():
        raise ValueError('Empty, too-short, or nonfinite audio')
    return x, sr


def validate_model_length(estimate, expected_samples):
    if len(estimate) != expected_samples:
        raise ValueError('Model length changed; verify padding position and latency before any trimming')


def write_new_audio(path, x, sr):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as stream:
        sf.write(stream, x, sr, format='WAV', subtype='FLOAT')


def stats(x, sr):
    return {'sample_rate': sr, 'channels': x.shape[1], 'samples': len(x),
            'duration_seconds': len(x) / sr,
            'rms_dbfs': db(np.sqrt(np.mean(x ** 2, axis=0))).tolist(),
            'peak_dbfs': db(np.max(np.abs(x), axis=0)).tolist(),
            'near_full_scale_samples': np.sum(np.abs(x) >= .999, axis=0).tolist()}


def pitch_comparison(a, b, sr):
    import librosa
    # Resampling is analysis-only and never replaces the deliverable waveform.
    a = librosa.resample(a, orig_sr=sr, target_sr=16000)
    b = librosa.resample(b, orig_sr=sr, target_sr=16000)
    fa, va, _ = librosa.pyin(a, sr=16000, fmin=60, fmax=600,
                           frame_length=1024, hop_length=160)
    fb, vb, _ = librosa.pyin(b, sr=16000, fmin=60, fmax=600,
                           frame_length=1024, hop_length=160)
    valid = va & vb & np.isfinite(fa) & np.isfinite(fb)
    if not valid.any() or not va.any():
        return {'status': 'no_reliable_voiced_frames'}
    cents = np.abs(1200 * np.log2(fb[valid] / fa[valid]))
    return {'status': 'measured', 'absolute_cents_median': float(np.median(cents)),
            'absolute_cents_p95': float(np.percentile(cents, 95)),
            'input_voiced_frames': int(va.sum()), 'joint_voiced_frames': int(valid.sum()),
            'voiced_retention': float(valid.sum() / va.sum())}


def audit(input_path, output_path, intervals=(), pitch=False):
    a, sr = read_audio(input_path)
    b, out_sr = read_audio(output_path)
    report = {'input': stats(a, sr), 'output': stats(b, out_sr),
              'format_matches': sr == out_sr and a.shape == b.shape,
              'pitch_status': 'not_measured', 'solo_target_intervals': [],
              'target_source_preservation': 'cannot_prove_without_clean_target_source',
              'thresholds_are_review_hints': True}
    if not report['format_matches']:
        report['comparison_status'] = 'format_or_timeline_mismatch'
        return report
    report['comparison_status'] = 'aligned_by_sample_index_not_verified_acoustically'
    for start, end in intervals:
        if not 0 <= start < end <= len(a) / sr:
            raise ValueError('Solo-target interval is outside the input timeline')
        left, right = int(round(start * sr)), int(round(end * sr))
        if right - left < max(4, int(.05 * sr)):
            raise ValueError('Solo-target interval must be at least 50 ms')
        x, y = a[left:right], b[left:right]
        delta = db(np.sqrt(np.mean(y ** 2, axis=0))) - db(np.sqrt(np.mean(x ** 2, axis=0)))
        frame = max(1, int(.05 * sr))
        count = len(x) // frame
        xr = np.sqrt(np.mean(x[:count * frame].reshape(count, frame, -1) ** 2, axis=1))
        yr = np.sqrt(np.mean(y[:count * frame].reshape(count, frame, -1) ** 2, axis=1))
        usable = xr > 1e-5
        window_delta = np.abs(db(yr)[usable] - db(xr)[usable])
        p95 = float(np.percentile(window_delta, 95)) if window_delta.size else None
        spectral = []
        for ch in range(x.shape[1]):
            _, _, zx = stft(x[:, ch], sr)
            _, _, zy = stft(y[:, ch], sr)
            mag = np.abs(zx)
            keep = (mag > mag.max() * .01) & (mag > 1e-8)
            difference = db(np.abs(zy))[keep] - db(mag)[keep]
            spectral.append(float(np.sqrt(np.mean(difference ** 2))) if keep.any() else None)
        measured = p95 is not None and all(v is not None for v in spectral)
        passed = bool(measured and np.max(np.abs(delta)) <= .5 and p95 <= 1
                      and max(spectral) <= 1)
        item = {'start': start, 'end': end, 'rms_delta_db': delta.tolist(),
                'window_absolute_rms_delta_db_p95': p95,
                'strong_bin_log_spectral_difference_db': spectral,
                'within_review_thresholds': passed}
        if pitch:
            item['pitch_channels'] = [pitch_comparison(x[:, i], y[:, i], sr)
                                      for i in range(x.shape[1])]
            item['within_review_thresholds'] = passed and all(
                p['status'] == 'measured' and p['absolute_cents_p95'] <= 20
                and p['voiced_retention'] >= .95 for p in item['pitch_channels'])
        report['solo_target_intervals'].append(item)
    if pitch and intervals:
        pitches = [p for item in report['solo_target_intervals'] for p in item['pitch_channels']]
        report['pitch_status'] = ('measured' if all(p['status'] == 'measured' for p in pitches)
                                  else 'partially_or_not_measured')
    return report


def parse_interval(value):
    try:
        start, end = map(float, value.split(':'))
        if not np.isfinite([start, end]).all() or not 0 <= start < end:
            raise ValueError
        return start, end
    except ValueError as exc:
        raise argparse.ArgumentTypeError('Use a valid start:end interval in seconds') from exc


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input')
    parser.add_argument('output')
    parser.add_argument('--solo-target', type=parse_interval, action='append', default=[])
    parser.add_argument('--pitch', action='store_true')
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    report = audit(args.input, args.output, args.solo_target, args.pitch)
    data = json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        with args.report.open('x', encoding='utf-8') as stream:
            stream.write(data + '\n')
    print(data)


if __name__ == '__main__':
    main()
