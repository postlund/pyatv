"""Simple script to generate audio files for testing.

This script can generate example audio files used for testing. Some metadata fields,
like artist or title, can be insert into the file. Various parameters can also be
changed, like number of channels or sample rate. It only outputs wav file, which is
good enough since we rely on a 3rd party library for loading files and metadata.

Number of frames to be written is specified with --frame-count (-n) and the same
pattern is always used. Assuming two channels and two bytes sample width, the
first frame will contain 00000000, second frame 01010101, third 02020202 and so
on. When reaching FFFFFFFF, the value will wrap back to 00000000 again.
"""

from argparse import ArgumentDefaultsHelpFormatter, ArgumentParser
from os import path
from typing import cast
import wave

from mutagen import File
from mutagen.id3 import TALB, TCON, TIT2, TORY, TPE1, TRCK, Encoding

METADATA_FIELDS = {
    "title": TIT2,
    "artist": TPE1,
    "album": TALB,
    "year": TORY,
    "track": TRCK,
    "genre": TCON,
}

FRAMES_PER_PACKET = 352


def write_new_wave_file(filename: str, args) -> None:
    """Generate and write a new sample WAV file."""
    if path.exists(filename) and not args.overwrite:
        raise RuntimeError("file already exists")

    with wave.open(filename, "wb") as handle:
        wfile: wave.Wave_write = cast(wave.Wave_write, handle)

        # See: https://github.com/PyCQA/pylint/issues/4534
        # pylint: disable=no-member
        wfile.setnchannels(args.channels)
        wfile.setsampwidth(args.sample_width)
        wfile.setframerate(args.sample_rate)
        for frame_number in range(args.frame_count):
            if args.static:
                frame = args.channels * args.sample_width * b"\x00"
            else:
                frame = args.channels * args.sample_width * bytes([frame_number & 0xFF])
            wfile.writeframes(frame)
        # pylint: enable=no-member


def add_metadata(filename: str, args):
    """Add metadata to an existing file."""
    f = File(filename)
    f.add_tags()
    for title, tag in METADATA_FIELDS.items():
        f.tags.add(tag(encoding=Encoding.UTF8, text=[getattr(args, title)]))
    f.save()


def main():
    """Script starts here."""
    parser = ArgumentParser(formatter_class=ArgumentDefaultsHelpFormatter)
    parser.add_argument("filename", help="output filename")
    parser.add_argument(
        "-c", "--channels", type=int, default=2, help="number of channels"
    )
    parser.add_argument(
        "-w", "--sample-width", type=int, default=2, help="sample width in bytes"
    )
    parser.add_argument(
        "-r", "--sample-rate", type=int, default=44100, help="sample rate"
    )
    parser.add_argument(
        "-s",
        "--static",
        default=False,
        action="store_true",
        help="use just zeroes as content",
    )
    parser.add_argument(
        "-o",
        "--overwrite",
        default=False,
        action="store_true",
        help="overwrite audio file if it exists",
    )
    parser.add_argument(
        "-n",
        "--frame-count",
        type=int,
        default=FRAMES_PER_PACKET * 2,
        help="frames to generate",
    )

    metadata = parser.add_argument_group("metadata")
    for item in METADATA_FIELDS:
        metadata.add_argument(f"--{item}", default=None, help=item)

    args = parser.parse_args()
    write_new_wave_file(args.filename, args)
    add_metadata(args.filename, args)


if __name__ == "__main__":
    main()
