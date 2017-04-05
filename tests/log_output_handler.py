"""Captures logging output and print if errors happen."""

import logging
from io import StringIO


class LogOutputHandler:
    """This is a convenience class that captures output to stdout/logging."""

    def __init__(self, testcase):
        """Initialize a new LogOutputHandler."""
        self.testcase = testcase
        self.log = StringIO()
        self.handler = logging.StreamHandler(self.log)

        # Enable all logging
        logging.getLogger().setLevel(logging.DEBUG)
        logging.getLogger().addHandler(self.handler)

    def tearDown(self):
        """Call by tearDown in test.

        This method will print all error produced by the test to stdout.
        """
        logging.getLogger().removeHandler(self.handler)

        # This is not pretty and can be considered a hack, but it works for now
        for method, error in self.testcase._outcome.errors:
            if error:
                print('=' * 70)
                print('stdout and logging from test is below:')
                print('-' * 70)
                print(self.log.getvalue())
                print('=' * 70)
                break
