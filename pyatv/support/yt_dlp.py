"""Helper methods for working with yt-dlp.

Currently ytp-dl is used to extract video URLs from various video sites, e.g. YouTube
so they can be streamed via AirPlay.
"""
import asyncio

from pyatv import exceptions


def _extract_video_url(video_link: str) -> str:
    # TODO: For now, dynamic support for this feature. User must manually install
    # yt-dlp, it will not be pulled in by pyatv.
    try:
        import yt_dlp  # pylint: disable=import-outside-toplevel
    except ModuleNotFoundError as ex:
        raise exceptions.NotSupportedError("package yt-dlp not installed") from ex

    with yt_dlp.YoutubeDL({"quiet": True, "no_warnings": True}) as ydl:
        info = ydl.sanitize_info(ydl.extract_info(video_link, download=False))

        if "formats" not in info:
            raise exceptions.NotSupportedError(
                "formats are missing, maybe authentication is needed (not supported)?"
            )

        best = None
        best_bitrate = 0

        # Try to find supported video stream with highest bitrate. No way to customize
        # this in any way for now.
        for video_format in [
            x for x in info["formats"] if x.get("protocol") == "m3u8_native"
        ]:
            if video_format["video_ext"] == "none":
                continue
            if video_format["has_drm"]:
                continue

            if video_format["vbr"] > best_bitrate:
                best = video_format
                best_bitrate = video_format["vbr"]

        if not best or "manifest_url" not in best:
            raise exceptions.NotSupportedError("manifest url could not be extracted")

        return best["manifest_url"]


async def extract_video_url(video_link: str) -> str:
    """Extract video URL from external video service link.

    This method takes a video link from a video service, e.g. YouTube, and extracts the
    underlying video URL that (hopefully) can be played via AirPlay. Currently yt-dlp
    is used to the extract the URL, thus all services supported by yt-dlp should be
    supported. No customization (e.g. resolution) nor authorization is supported at the
    moment, putting some restrictions on use case.
    """
    loop = asyncio.get_event_loop()
    try:
        return await loop.run_in_executor(None, _extract_video_url, video_link)
    except Exception as ex:
        raise exceptions.InvalidFormatError(f"video {video_link} not supported") from ex
