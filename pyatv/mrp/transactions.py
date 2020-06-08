"""Module responsible for keeping track of transactions."""

import logging

from pyatv.mrp import protobuf


_LOGGER = logging.getLogger(__name__)


class TransactionContext:

    def __init__(self, identifier: str, total_size: int) -> None:
        self.buffer: bytes = b""
        self.identifier: str = identifier
        self.total_size: int = total_size

    def merge(self, packet: protobuf.TransactionPacket) -> bool:
        self.buffer += packet.packetData
        return self.complete

    @property
    def complete(self):
        return len(self.buffer) == self.total_size

    def __str__(self):
        return f"({self.buffer}, {self.identifier}, {self.total_size})"


class Transactions:
    """Manages active transactions."""

    def __init__(self):
        """Initialize a new Transactions instance."""
        self._transactions = {}  # Dict[str, TransactionContext]

    @property
    def pending_count(self) -> int:
        return len([t for t in self._transactions.values() if not t.complete])

    def merge(self, transaction: protobuf.TransactionMessage):
        for packet in transaction.packets.packets:
            context = self._transactions.setdefault(packet.key.identifier,
                TransactionContext(packet.identifier, packet.totalLength))

            if context.merge(packet):
                yield packet.key.identifier, context