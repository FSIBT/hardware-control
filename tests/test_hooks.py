"""Test internal hooks"""
import hardware_control as hc


class TestHooks:
    def test_call_hooks(self):
        """check that the call_hooks works as expected"""

        # no hook should leave value as is
        out = hc.hooks.call_hooks([], "test")
        assert out == "test"

        # hooks should change value
        def hook1(value):
            return "test1"

        def hook2(value):
            return "test2"

        def hook3(value):
            return "test3"

        out = hc.hooks.call_hooks([hook1, hook2, hook3], "test")
        assert out == "test3"

        # a None return value should break the chain of functions called
        def hook_stop(value):
            return None

        out = hc.hooks.call_hooks([hook1, hook_stop, hook3], "test")
        assert out is None

    def test_add_offset(self):
        func = hc.hooks.add_offset(3)

        assert func("1") == 4
        assert func("2") == 5

    def test_lookup_table(self):
        lookup = {"1": "one", "2": "two"}
        func = hc.hooks.create_converter(lookup)

        assert func("1") == "one"
        assert func("2") == "two"
        assert func("doesn't exist") == None

    def test_format_bool(self):
        func = hc.hooks.format_bool

        assert func("True") == "1"
        assert func("False") == "0"
        assert func("garbage") == "0"

    def test_format_float(self):
        func = hc.hooks.format_float(".1E")
        assert func("1") == "1.0E+00"

        func = hc.hooks.format_float(".2E")
        assert func("1") == "1.00E+00"

    def test_format_int(self):
        func = hc.hooks.format_int

        assert func("1.0") == "1"
        assert func("1.7") == "1"

    def test_last_n_values_converter(self):
        func = hc.hooks.last_n_values_converter(3)

        assert func([1]) == [1]
        assert func([1, 2]) == [1, 2]
        assert func([1, 2, 3]) == [1, 2, 3]
        assert func([1, 2, 3, 4]) == [2, 3, 4]
        assert func([1, 2, 3, 4, 5]) == [3, 4, 5]

    def test_make_negative(self):
        func = hc.hooks.make_negative

        assert func("1") == "-1.0"
        assert func("-1") == "1.0"

    def test_max_len(self):
        func = hc.hooks.max_len_converter(5)

        assert func("1") == "1"
        assert func("12") == "12"
        assert func("123") == "123"
        assert func("1234") == "1234"
        assert func("12345") == "12345"
        assert func("123456") == "12345"
        assert func("1234567") == "12345"

    def test_scaling_converter(self):
        func = hc.hooks.scaling_converter(2)

        assert func("1") == "2.0"
        assert func("1.5") == "3.0"

    def test_substring_hook(self):
        func = hc.hooks.substring_hook(2, 5)
        assert func("0123456789") == "234"

        func = hc.hooks.substring_hook(2, -1)
        assert func("0123456") == "2345"

    def test_uppercaser(self):
        func = hc.hooks.uppercase

        assert func("1") == "1"
        assert func("ABC") == "ABC"
        assert func("abc") == "ABC"
        assert func("aBc") == "ABC"

    def test_expected_input_validator(self):
        func = hc.hooks.expected_input_validator(["A", "B"])

        assert func("A") == "A"
        assert func("B") == "B"

        func = hc.hooks.expected_input_validator(["A", "B"], default_val="C")

        assert func("A") == "A"
        assert func("B") == "B"
        assert func("1") == "C"

    def test_range_validator(self):
        func = hc.hooks.range_validator(0, 10)

        assert func("-1") == 0.0
        assert func("0") == 0.0
        assert func("1") == 1.0
        assert func("5") == 5.0
        assert func("10") == 10.0
        assert func("11") == 10.0
