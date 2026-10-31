"""Bedrock packets for client-side floating texts, written for protocol 2225 (26.60)."""

import struct

PACKET_ADD_ACTOR = 13
PACKET_REMOVE_ACTOR = 14

FIRST_RUNTIME_ID = 0x7F000000
AIR_BLOCK_HASH = -604749536
FLAG_NO_AI = 16

DATA_FLAGS = 0
DATA_VARIANT = 2
DATA_NAMETAG = 4
DATA_SCALE = 38
DATA_BOX_WIDTH = 53
DATA_BOX_HEIGHT = 54
DATA_ALWAYS_SHOW = 81

TYPE_BYTE, TYPE_INT, TYPE_FLOAT, TYPE_STRING, TYPE_LONG = 0, 2, 3, 4, 7


def uvarint(value: int) -> bytes:
    out = bytearray()
    while True:
        byte = value & 0x7F
        value >>= 7
        if value:
            out.append(byte | 0x80)
        else:
            out.append(byte)
            return bytes(out)


def zigzag(value: int) -> bytes:
    return uvarint((value << 1) ^ (value >> 63))


def string(value: str) -> bytes:
    raw = value.encode("utf-8")
    return uvarint(len(raw)) + raw


def metadata_entry(key: int, value_type: int) -> bytes:
    # Since 26.60 the value type is written twice.
    return uvarint(key) + uvarint(value_type) + uvarint(value_type)


def add_text(runtime_id: int, text: str, x: float, y: float, z: float) -> bytes:
    """Build an AddActor payload for an invisible falling block carrying a name tag."""
    metadata = [
        metadata_entry(DATA_FLAGS, TYPE_LONG) + zigzag(1 << FLAG_NO_AI),
        metadata_entry(DATA_NAMETAG, TYPE_STRING) + string(text),
        metadata_entry(DATA_VARIANT, TYPE_INT) + zigzag(AIR_BLOCK_HASH),
        metadata_entry(DATA_SCALE, TYPE_FLOAT) + struct.pack("<f", 0.01),
        metadata_entry(DATA_BOX_WIDTH, TYPE_FLOAT) + struct.pack("<f", 0.0),
        metadata_entry(DATA_BOX_HEIGHT, TYPE_FLOAT) + struct.pack("<f", 0.0),
        metadata_entry(DATA_ALWAYS_SHOW, TYPE_BYTE) + bytes([1]),
    ]
    return (
        zigzag(runtime_id)
        + uvarint(runtime_id)
        + string("minecraft:falling_block")
        + struct.pack("<3f", x, y, z)
        + struct.pack("<3f", 0.0, 0.0, 0.0)
        + struct.pack("<4f", 0.0, 0.0, 0.0, 0.0)
        + uvarint(0)  # attributes
        + uvarint(len(metadata))
        + b"".join(metadata)
        + uvarint(0)  # synced int properties
        + uvarint(0)  # synced float properties
        + uvarint(0)  # links
        + bytes(1)  # no passenger-of-block entry
    )


def remove_text(runtime_id: int) -> bytes:
    return zigzag(runtime_id)
