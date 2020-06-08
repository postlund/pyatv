"""Unit tests for pyatv.mrp.transactions."""

import pytest

from pyatv.mrp import protobuf
from pyatv.mrp.transactions import Transactions

@pytest.fixture
def transactions() -> Transactions:
    yield Transactions()


def create_transaction(transaction_id: str, content_id: str, packets: int):
    for packet_no in range(packets):
        transaction = protobuf.TransactionMessage()
        transaction.name = 1
        packet = transaction.packets.packets.add()
        packet.key.identifier = transaction_id
        packet.packetData = b"\xAB"
        packet.identifier = content_id
        packet.totalLength = packets
        packet.totalWritePosition = packet_no
        yield transaction


def test_single_packet(transactions):
    message = create_transaction("id1", "id2", 1)
    key, context = next(transactions.merge(next(message)))
    assert key == "id1"
    assert context.buffer == b"\xAB"
    assert context.identifier == "id2"
    assert context.total_size == 1


def test_three_packets(transactions):
    message = create_transaction("id1", "id2", 3)

    # First two packets just adds to the buffer
    assert not next(transactions.merge(next(message)), None)
    assert not next(transactions.merge(next(message)), None)

    # Last packet makes the buffer complete
    key, context = next(transactions.merge(next(message)))
    assert key == "id1"
    assert context.buffer == 3 * b"\xAB"
    assert context.identifier == "id2"
    assert context.total_size == 3


def test_pending_transactions(transactions):
    t1 = create_transaction("id1", "id2", 2)
    t2 = create_transaction("id3", "id4", 2)

    assert transactions.pending_count == 0

    next(transactions.merge(next(t1)), None)
    assert transactions.pending_count == 1

    next(transactions.merge(next(t2)), None)
    assert transactions.pending_count == 2

    next(transactions.merge(next(t1)), None)
    next(transactions.merge(next(t2)), None)
    assert transactions.pending_count == 0
