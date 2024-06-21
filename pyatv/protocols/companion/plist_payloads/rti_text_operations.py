"""Helper function to generate payloads for RTI service.

In the absence of a robust NSKeyedArchiver implementation, these are pre-
encoded.
"""

import plistlib

__ALL__ = ["get_rti_clear_text_payload", "get_rti_input_text_payload"]


def get_rti_clear_text_payload(session_uuid: bytes) -> bytes:
    """Prepare an NSKeyedArchiver encoded payload for clearing the RTI text.

    Un-encoded format:
        {
            'textOperations': {
                '$class': {'$classname': 'RTITextOperations', '$classes': ['RTITextOperations', 'NSObject']},   # pylint: disable=line-too-long # noqa
                'targetSessionUUID': {
                    '$class': {'$classname': 'NSUUID', '$classes': ['NSUUID', 'NSObject']},                     # pylint: disable=line-too-long # noqa
                    'NS.uuidbytes': b'<session_bytes>'
                },
                'keyboardOutput': {
                    '$class': {'$classname': 'TIKeyboardOutput', '$classes': ['TIKeyboardOutput', 'NSObject']}  # pylint: disable=line-too-long # noqa
                },
                'textToAssert': ''
            }
        }
    """
    return plistlib.dumps(
        {
            "$version": 100000,
            "$archiver": "RTIKeyedArchiver",
            "$top": {
                "textOperations": plistlib.UID(1),
            },
            "$objects": [
                "$null",
                {
                    "$class": plistlib.UID(7),
                    "targetSessionUUID": plistlib.UID(5),
                    "keyboardOutput": plistlib.UID(2),
                    "textToAssert": plistlib.UID(4),
                },
                {
                    "$class": plistlib.UID(3),
                },
                {
                    "$classname": "TIKeyboardOutput",
                    "$classes": [
                        "TIKeyboardOutput",
                        "NSObject",
                    ],
                },
                "",
                {
                    "NS.uuidbytes": session_uuid,
                    "$class": plistlib.UID(6),
                },
                {
                    "$classname": "NSUUID",
                    "$classes": [
                        "NSUUID",
                        "NSObject",
                    ],
                },
                {
                    "$classname": "RTITextOperations",
                    "$classes": [
                        "RTITextOperations",
                        "NSObject",
                    ],
                },
            ],
        },
        fmt=plistlib.PlistFormat.FMT_BINARY,
        sort_keys=False,
    )


def get_rti_input_text_payload(session_uuid: bytes, text: str) -> bytes:
    """Prepare an NSKeyedArchiver encoded payload for RTI text input.

    Un-encoded format:
        {
            'textOperations': {
                '$class': {'$classname': 'RTITextOperations', '$classes': ['RTITextOperations', 'NSObject']},    # pylint: disable=line-too-long # noqa
                'targetSessionUUID': {
                    '$class': {'$classname': 'NSUUID', '$classes': ['NSUUID', 'NSObject']},                      # pylint: disable=line-too-long # noqa
                    'NS.uuidbytes': b'<session_bytes>',
                },
                'keyboardOutput': {
                    '$class': {'$classname': 'TIKeyboardOutput', '$classes': ['TIKeyboardOutput', 'NSObject']},  # pylint: disable=line-too-long # noqa
                    'insertionText': '<input_text>'
                }
            }
        }
    """
    return plistlib.dumps(
        {
            "$version": 100000,
            "$archiver": "RTIKeyedArchiver",
            "$top": {
                "textOperations": plistlib.UID(1),
            },
            "$objects": [
                "$null",
                {
                    "keyboardOutput": plistlib.UID(2),
                    "$class": plistlib.UID(7),
                    "targetSessionUUID": plistlib.UID(5),
                },
                {
                    "insertionText": plistlib.UID(3),
                    "$class": plistlib.UID(4),
                },
                text,
                {
                    "$classname": "TIKeyboardOutput",
                    "$classes": [
                        "TIKeyboardOutput",
                        "NSObject",
                    ],
                },
                {
                    "NS.uuidbytes": session_uuid,
                    "$class": plistlib.UID(6),
                },
                {
                    "$classname": "NSUUID",
                    "$classes": [
                        "NSUUID",
                        "NSObject",
                    ],
                },
                {
                    "$classname": "RTITextOperations",
                    "$classes": [
                        "RTITextOperations",
                        "NSObject",
                    ],
                },
            ],
        },
        fmt=plistlib.PlistFormat.FMT_BINARY,
        sort_keys=False,
    )
