"""Test internal hooks"""
import pytest

import hardware_control as hc


class TestHooks:
    def test_lookup_table(self):
        lookup = {"1": "one", "2": "two"}
        func = hc.hooks.create_converter(lookup)

        assert func("1") == "one"
        assert func("2") == "two"
        assert func("doesn't exist") == None

    def test_max_len(self):
        func = hc.hooks.max_len_converter(5)

        assert func("1") == "1"
        assert func("12") == "12"
        assert func("123") == "123"
        assert func("1234") == "1234"
        assert func("12345") == "12345"
        assert func("123456") == "12345"
        assert func("1234567") == "12345"

    def test_last_n_values_converter(self):
        func = hc.hooks.last_n_values_converter(3)

        assert func([1]) == [1]
        assert func([1, 2]) == [1, 2]
        assert func([1, 2, 3]) == [1, 2, 3]
        assert func([1, 2, 3, 4]) == [2, 3, 4]
        assert func([1, 2, 3, 4, 5]) == [3, 4, 5]

    def test_substring_hook(self):
        func = hc.hooks.substring_hook(2, 5)
        assert func("0123456789") == "234"

        func = hc.hooks.substring_hook(2, -1)
        assert func("0123456") == "2345"
