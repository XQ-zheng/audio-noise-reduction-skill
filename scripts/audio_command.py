"""Entry point for the literal shell command: audio noise reduction skill."""
import sys


def main(argv=None):
    args = list(sys.argv[1:] if argv is None else argv)
    if args in (['--help'], ['-h']):
        print('Usage: audio noise reduction skill INPUT OUTPUT --backend {sam,clearvoice} [options]')
        print('Run audio noise reduction skill --help for processing options.')
        return 0
    if args[:3] != ['noise', 'reduction', 'skill']:
        print('Usage: audio noise reduction skill INPUT OUTPUT --backend {sam,clearvoice} [options]', file=sys.stderr)
        return 2
    if __package__:
        from .process_audio import main as process
    else:
        from process_audio import main as process
    process(args[3:])
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
