"""Unit tests for pyatv.interface."""

import unittest

from pyatv import interface


class TestClass:

    variable = 1234

    def test_method(self):
        """Help text."""
        pass

    def another_method(self):
        """Some other help text. More text here. Test."""
        pass

    @property
    def some_property(self):
        """Property help"""
        pass

    def dev_method(self):
        """Developer help."""
        pass

    def abbrev_help(self):
        """Type, e.g. a, b or c."""
        pass

    def abbrev_help_more_text(self):
        """Type, e.g. a, b or c. Some other text."""
        pass

    def _private_method_ignored(self):
        """Not parsed."""
        pass


class InterfaceTest(unittest.TestCase):

    def setUp(self):
        self.obj = TestClass()
        self.methods = interface.retrieve_commands(self.obj)

    def test_get_commands(self):
        self.assertEqual(5, len(self.methods))
        self.assertTrue('test_method' in self.methods)
        self.assertTrue('another_method' in self.methods)
        self.assertTrue('some_property' in self.methods)
        self.assertTrue('abbrev_help' in self.methods)

    def test_get_developer_command(self):
        methods = interface.retrieve_commands(self.obj, developer=True)
        self.assertEqual(6, len(methods))
        self.assertEqual('Developer help', methods['dev_method'])

    def test_get_first_sentence_without_leading_period_in_pydoc(self):
        self.assertEqual('Help text', self.methods['test_method'])
        self.assertEqual(
            'Some other help text', self.methods['another_method'])
        self.assertEqual('Property help', self.methods['some_property'])

    def test_try_to_be_smart_with_abbreviations(self):
        self.assertEqual(
            'Type, e.g. a, b or c', self.methods['abbrev_help'])
        self.assertEqual(
            'Type, e.g. a, b or c', self.methods['abbrev_help_more_text'])
