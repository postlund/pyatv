"""Shared test helper code."""

from pyatv.const import PowerState
from pyatv.interface import PowerListener


class SavingPowerListener(PowerListener):
    def __init__(self):
        self.last_update = None
        self.all_updates = []

    def powerstate_update(self, old_state: PowerState, new_state: PowerState):
        """Device power state was updated."""
        self.last_update = new_state
        self.all_updates.append(new_state)
