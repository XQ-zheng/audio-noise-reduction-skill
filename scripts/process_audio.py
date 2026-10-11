"""Local model-assisted attenuation preview; no normalization or overwrite."""
import argparse
import importlib.metadata
import json
import math
from pathlib import Path
import numpy as np
from scipy.signal import resample_poly
if __package__:
    from .audio_tools import audit, parse_interval, read_audio, transfer_mask, validate_model_length, write_new_audio
else:
    from audio_tools import audit, parse_interval, read_audio, transfer_mask, validate_model_length, write_new_audio


def resample(x, source_sr, target_sr):
    divisor = math.gcd(source_sr, target_sr)
    return resample_poly(x, target_sr // divisor, source_sr // divisor)


def infer(x, sr, args):
    if args.backend == 'clearvoice':
        from clearvoice import ClearVoice
        model_sr = 48000
        if sr > model_sr:
            raise ValueError('Source bandwidth exceeds 48 kHz model; choose another backend')
        mono = resample(x, sr, model_sr).astype(np.float32)
        model = ClearVoice(task='speech_enhancement', model_names=['MossFormer2_SE_48K'])
        estimate = np.asarray(model(mono[None, :], False))[0]
        model_id = 'MossFormer2_SE_48K'
    else:
        import torch
        from sam_audio import SAMAudio, SAMAudioProcessor
        if args.device.startswith('cuda') and not torch.cuda.is_available():
            raise RuntimeError('CUDA unavailable; no automatic CPU fallback')
        processor = SAMAudioProcessor.from_pretrained(args.model)
        model_sr = int(processor.audio_sampling_rate)
        if sr > model_sr:
            raise ValueError('Source bandwidth exceeds model; upsampling cannot restore it')
        mono = resample(x, sr, model_sr).astype(np.float32)
        model = SAMAudio.from_pretrained(args.model).eval().to(args.device)
        anchors = [[['+', start, end] for start, end in args.anchor]]
        batch = processor(audios=[torch.from_numpy(mono)[None, :]],
                          descriptions=[args.description], anchors=anchors).to(args.device)
        with torch.inference_mode():
            result = model.separate(batch, predict_spans=False, reranking_candidates=1)
        estimate = result.target.detach().cpu().numpy().reshape(-1)
        model_id = args.model
    validate_model_length(estimate, len(mono))
    restored = resample(estimate, model_sr, sr)
    if len(restored) < len(x):
        raise ValueError('Model output is shorter than input timeline')
    restored = restored[:len(x)]
    return restored, {'model': model_id, 'model_sample_rate': model_sr,
                      'model_tail_padding_removed_samples': 0,
                      'device_request': args.device if args.backend == 'sam' else 'backend_default'}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--backend', choices=['sam', 'clearvoice'], required=True)
    parser.add_argument('--analysis-channel', type=int, default=0)
    parser.add_argument('--strength', type=float, default=0.8,
                        help='0..1; lower values retain more interference and more source detail')
    parser.add_argument('--description', default='foreground person speaking')
    parser.add_argument('--anchor', type=parse_interval, action='append', default=[])
    parser.add_argument('--model', default='facebook/sam-audio-large')
    parser.add_argument('--device', default='cuda')
    args = parser.parse_args(argv)
    if not np.isfinite(args.strength) or not 0 <= args.strength <= 1:
        parser.error('Strength must be between zero and one')
    report_path = args.output.with_suffix('.processing.json')
    if args.output.suffix.lower() != '.wav':
        parser.error('Output must be a new WAV file')
    if args.output.exists() or report_path.exists():
        parser.error('Output or report already exists; choose new paths')
    if args.backend == 'sam' and not args.anchor:
        parser.error('SAM needs a verified solo-target --anchor start:end')
    original, sr = read_audio(args.input)
    if not 0 <= args.analysis_channel < original.shape[1]:
        parser.error('Analysis channel is outside source channel range')
    if any(end > len(original) / sr for _, end in args.anchor):
        parser.error('Anchor is outside input timeline')
    estimate, metadata = infer(original[:, args.analysis_channel], sr, args)
    cleaned = transfer_mask(original, estimate, sr, args.analysis_channel, args.strength)
    if np.max(np.abs(cleaned)) >= 1:
        raise RuntimeError('Potential clipping; refusing to normalize or limit output')
    write_new_audio(args.output, cleaned, sr)
    metadata.update({'backend': args.backend, 'analysis_channel': args.analysis_channel,
                     'mask_strength': args.strength,
                     'description': args.description if args.backend == 'sam' else None,
                     'anchors_seconds': args.anchor, 'shared_attenuation_mask': True,
                     'automatic_gain_or_pitch_change': False,
                     'residual_and_identity_listening': 'not_verified_by_script',
                     'audit': audit(args.input, args.output)})
    versions = {}
    for name in ['numpy', 'scipy', 'soundfile', 'torch', 'sam-audio', 'clearvoice']:
        try:
            versions[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            pass
    metadata['package_versions'] = versions
    with report_path.open('x', encoding='utf-8') as stream:
        json.dump(metadata, stream, ensure_ascii=False, indent=2, allow_nan=False)
    print(f'Preview: {args.output}\nProcessing report: {report_path}')


if __name__ == '__main__':
    main()
