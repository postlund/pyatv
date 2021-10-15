"""Definitions of DMAP tags used by various applications."""

import logging

from pyatv.protocols.dmap.parser import DmapTag
from pyatv.protocols.dmap.tags import (
    read_bool,
    read_bplist,
    read_bytes,
    read_ignore,
    read_str,
    read_uint,
)

_LOGGER = logging.getLogger(__name__)


# Internal version that works like read_ignore, but also logs
def _read_unknown(data, start, length):
    _LOGGER.warning("Unknown data: %s", str(data[start - 8 : start + length + 8]))


# These are the tags that we know about so far
_TAGS = {
    "aelb": DmapTag(read_bool, "com.apple.itunes.like-button"),
    "aels": DmapTag(read_uint, "com.apple.itunes.liked-state"),
    "aeFP": DmapTag(read_uint, "com.apple.itunes.req-fplay"),
    "aeGs": DmapTag(read_bool, "com.apple.itunes.can-be-genius-seed"),
    "aeSV": DmapTag(read_uint, "com.apple.itunes.music-sharing-version"),
    "apro": DmapTag(read_uint, "daap.protocolversion"),
    "asai": DmapTag(read_uint, "daap.songalbumid"),
    "asal": DmapTag(read_str, "daap.songalbum"),
    "asar": DmapTag(read_str, "daap.songartist"),
    "asgr": DmapTag(read_uint, "com.apple.itunes.gapless-resy"),
    "astm": DmapTag(read_uint, "daap.songtime"),
    "ated": DmapTag(read_bool, "daap.supportsextradata"),
    "caar": DmapTag(read_uint, "dacp.albumrepeat"),
    "caas": DmapTag(read_uint, "dacp.albumshuffle"),
    "caci": DmapTag("container", "dacp.controlint"),
    "cafe": DmapTag(read_bool, "dacp.fullscreenenabled"),
    "cafs": DmapTag(read_uint, "dacp.fullscreen"),
    "cana": DmapTag(read_str, "daap.nowplayingartist"),
    "cang": DmapTag(read_str, "dacp.nowplayinggenre"),
    "canl": DmapTag(read_str, "daap.nowplayingalbum"),
    "cann": DmapTag(read_str, "daap.nowplayingtrack"),
    "canp": DmapTag(read_bytes, "daap.nowplayingid"),
    "cant": DmapTag(read_uint, "dacp.remainingtime"),
    "capr": DmapTag(read_uint, "dacp.protocolversion"),
    "caps": DmapTag(read_uint, "dacp.playstatus"),
    "carp": DmapTag(read_uint, "dacp.repeatstate"),
    "cash": DmapTag(read_uint, "dacp.shufflestate"),
    "cast": DmapTag(read_uint, "dacp.tracklength"),
    "casu": DmapTag(read_uint, "dacp.su"),
    "cavc": DmapTag(read_bool, "dacp.volumecontrollable"),
    "cave": DmapTag(read_bool, "dacp.dacpvisualizerenabled"),
    "cavs": DmapTag(read_uint, "dacp.visualizer"),
    "ceGS": DmapTag(read_str, "com.apple.itunes.genius-selectable"),
    "ceQR": DmapTag("container", "com.apple.itunes.playqueue-contents-response"),
    "ceSD": DmapTag(read_bplist, "playing metadata"),
    "cmcp": DmapTag("container", "dmcp.controlprompt"),
    "cmmk": DmapTag(read_uint, "dmcp.mediakind"),
    "cmnm": DmapTag(read_str, "dacp.devicename"),
    "cmpa": DmapTag("container", "dacp.pairinganswer"),
    "cmpg": DmapTag(read_uint, "dacp.pairingguid"),
    "cmpr": DmapTag(read_uint, "dmcp.protocolversion"),
    "cmsr": DmapTag(read_uint, "dmcp.serverrevision"),
    "cmst": DmapTag("container", "dmcp.playstatus"),
    "cmty": DmapTag(read_str, "dacp.devicetype"),
    "mdcl": DmapTag("container", "dmap.dictionary"),
    "miid": DmapTag(read_uint, "dmap.itemid"),
    "minm": DmapTag(read_str, "dmap.itemname"),
    "mlcl": DmapTag("container", "dmap.listing"),
    "mlid": DmapTag(read_uint, "dmap.sessionid"),
    "mlit": DmapTag("container", "dmap.listingitem"),
    "mlog": DmapTag("container", "dmap.loginresponse"),
    "mpro": DmapTag(read_uint, "dmap.protocolversion"),
    "mrco": DmapTag(read_uint, "dmap.returnedcount"),
    "msal": DmapTag(read_bool, "dmap.supportsautologout"),
    "msbr": DmapTag(read_bool, "dmap.supportsbrowse"),
    "msdc": DmapTag(read_uint, "dmap.databasescount"),
    "msed": DmapTag(read_bool, "dmap.supportsedit"),
    "msex": DmapTag(read_bool, "dmap.supportsextensions"),
    "msix": DmapTag(read_bool, "dmap.supportsindex"),
    "mslr": DmapTag(read_bool, "dmap.loginrequired"),
    "mspi": DmapTag(read_bool, "dmap.supportspersistentids"),
    "msqy": DmapTag(read_bool, "dmap.supportsquery"),
    "msrv": DmapTag("container", "dmap.serverinforesponse"),
    "mstc": DmapTag(read_uint, "dmap.utctime"),
    "mstm": DmapTag(read_uint, "dmap.timeoutinterval"),
    "msto": DmapTag(read_uint, "dmap.utcoffset"),
    "mstt": DmapTag(read_uint, "dmap.status"),
    "msup": DmapTag(read_bool, "dmap.supportsupdate"),
    "mtco": DmapTag(read_uint, "dmap.containercount"),
    # Tags with (yet) unknown purpose
    "aead": DmapTag(read_bytes, "unknown tag"),
    "aeFR": DmapTag(read_uint, "unknown tag"),
    "aeSX": DmapTag(read_uint, "unknown tag"),
    "asse": DmapTag(read_uint, "unknown tag"),
    "atCV": DmapTag(read_uint, "unknown tag"),
    "atSV": DmapTag(read_uint, "unknown tag"),
    "caks": DmapTag(read_uint, "unknown tag"),
    "caov": DmapTag(read_uint, "unknown tag"),
    "capl": DmapTag(read_bytes, "unknown tag"),
    "casa": DmapTag(read_uint, "unknown tag"),
    "casc": DmapTag(read_uint, "unknown tag"),
    "cass": DmapTag(read_uint, "unknown tag"),
    "ceQA": DmapTag(read_uint, "unknown tag"),
    "ceQU": DmapTag(read_bool, "unknown tag"),
    "ceMQ": DmapTag(read_bool, "unknown tag"),
    "ceNQ": DmapTag(read_uint, "unknown tag"),
    "ceNR": DmapTag(read_bytes, "unknown tag"),
    "ceQu": DmapTag(read_bool, "unknown tag"),
    "cmbe": DmapTag(read_str, "unknown tag"),
    "cmcc": DmapTag(read_str, "unknown tag"),
    "cmce": DmapTag(read_str, "unknown tag"),
    "cmcv": DmapTag(read_ignore, "unknown tag"),
    "cmik": DmapTag(read_uint, "unknown tag"),
    "cmsb": DmapTag(read_uint, "unknown tag"),
    "cmsc": DmapTag(read_uint, "unknown tag"),
    "cmsp": DmapTag(read_uint, "unknown tag"),
    "cmsv": DmapTag(read_uint, "unknown tag"),
    "cmte": DmapTag(read_str, "unknown tag"),
    "mscu": DmapTag(read_uint, "unknown tag"),
}


def lookup_tag(name):
    """Look up a tag based on its key. Returns a DmapTag."""
    return next(
        (tag for tag_name, tag in _TAGS.items() if tag_name == name),
        DmapTag(_read_unknown, "unknown tag"),
    )
