"""Test internal hooks"""

import hardware_control as hc


class TestSimpleHooks:
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


class MockApp:
    def __init__(self):
        self.data = [0]

    def get_instrument_parameter(self, inst, parameter):
        return self.data[-1]

    def set_instrument_parameter(self, inst, parameter, value, priority=2):
        self.data.append(value)


class MockConnection:
    def __init__(self):
        self.func = None

    def connect(self, func):
        self.func = func


class MockTimer:
    def __init__(self):
        self.timeout = MockConnection()

    def start(self, dt=1):
        for i in range(5):
            self.timeout.func()

    def stop(self):
        pass


class TestRampHook:
    def test_steps_and_min_value(self):
        app = MockApp()
        ramp = hc.hooks.Ramp(
            app,
            "instrument_dummy",
            "parameter_dummy",
            ramp_speed=1,
            timer_step=1000,
            min_value=10,
            epsilon=1,
        )

        ramp.timer = MockTimer()
        ramp.timer.timeout.connect(ramp.do_step)

        ramp(20)
        assert app.data == [0, 10, 11, 12, 13, 14]

        app = MockApp()
        ramp = hc.hooks.Ramp(
            app,
            "instrument_dummy",
            "parameter_dummy",
            ramp_speed=1,
            timer_step=500,
            min_value=10,
            epsilon=1,
        )

        ramp.timer = MockTimer()
        ramp.timer.timeout.connect(ramp.do_step)

        ramp(20)
        assert app.data == [0, 10, 10.5, 11, 11.5, 12]

        app = MockApp()
        ramp = hc.hooks.Ramp(
            app,
            "instrument_dummy",
            "parameter_dummy",
            ramp_speed=2,
            timer_step=500,
            min_value=10,
            epsilon=1,
        )

        ramp.timer = MockTimer()
        ramp.timer.timeout.connect(ramp.do_step)

        ramp(20)
        assert app.data == [0, 10, 11, 12, 13, 14]

    def test_call_function(self):
        app = MockApp()
        ramp = hc.hooks.Ramp(
            app,
            "instrument_dummy",
            "parameter_dummy",
            ramp_speed=1,
            timer_step=1000,
            min_value=10,
            epsilon=1,
        )
        ramp.timer = MockTimer()
        ramp.timer.timeout.connect(ramp.do_step)

        # no ramps below min_value
        ramp.next_value = 10
        assert ramp("10") == "10"
        assert ramp("10.2") == "10.2"
        assert ramp("9.8") == "9.8"
        assert ramp("0") == "0"

        # no ramps near next_value
        ramp.next_value = 15
        assert ramp("15") == "15"
        assert ramp("15.2") == "15.2"
        assert ramp("14.8") == "14.8"

        # this should start the ramp
        ramp("20")
        assert app.data == [0, 10, 11, 12, 13, 14]


class TestHookCombinations:
    """Test combinations of multiple hooks."""

    def test_multiple_hooks_in_sequence(self):
        """Test chaining multiple hooks together."""
        # Create a chain: add_offset(5) -> scaling_converter(2)
        hook1 = hc.hooks.add_offset(5)
        hook2 = hc.hooks.scaling_converter(2)

        result = hc.hooks.call_hooks([hook1, hook2], "10")
        # 10 + 5 = 15, then 15 * 2 = 30
        assert result == "30.0"

    def test_hook_chain_with_formatter(self):
        """Test hook chain ending with formatter."""
        # Chain: scaling_converter(2) -> format_float(".2f")
        hook1 = hc.hooks.scaling_converter(2)
        hook2 = hc.hooks.format_float(".2f")

        result = hc.hooks.call_hooks([hook1, hook2], "3.14159")
        # 3.14159 * 2 = 6.28318, formatted to .2f = "6.28"
        assert result == "6.28"

    def test_hook_chain_with_validation(self):
        """Test hook chain with validator."""
        # Chain: add_offset(10) -> range_validator(0, 100)
        hook1 = hc.hooks.add_offset(10)
        hook2 = hc.hooks.range_validator(0, 100)

        result = hc.hooks.call_hooks([hook1, hook2], "50")
        # 50 + 10 = 60, within range
        assert result == 60.0

        result = hc.hooks.call_hooks([hook1, hook2], "95")
        # 95 + 10 = 105, clamped to 100
        assert result == 100.0

    def test_hook_chain_breaking_early(self):
        """Test that None breaks the chain."""
        hook1 = hc.hooks.add_offset(5)
        hook2 = hc.hooks.expected_input_validator(["A", "B"])  # Will return None
        hook3 = hc.hooks.scaling_converter(2)  # Should not be called

        result = hc.hooks.call_hooks([hook1, hook2, hook3], "10")
        # hook1: 10 + 5 = 15
        # hook2: "15" not in ["A", "B"], returns None
        # hook3: never called
        assert result is None

    def test_string_manipulation_chain(self):
        """Test chaining string manipulation hooks."""
        # Chain: substring_hook -> uppercase
        hook1 = hc.hooks.substring_hook(0, 3)
        hook2 = hc.hooks.uppercase

        result = hc.hooks.call_hooks([hook1, hook2], "hello world")
        # Substring [0:3] = "hel", uppercase = "HEL"
        assert result == "HEL"

    def test_numeric_conversion_chain(self):
        """Test numeric conversion and formatting."""
        # Chain: format_int -> add_offset(10) -> format_float(".1f")
        hook1 = hc.hooks.format_int  # "3.7" -> "3"
        hook2 = hc.hooks.add_offset(10)  # "3" + 10 -> 13
        hook3 = hc.hooks.format_float(".1f")  # 13 -> "13.0"

        result = hc.hooks.call_hooks([hook1, hook2, hook3], "3.7")
        assert result == "13.0"

    def test_lookup_with_fallback(self):
        """Test lookup table with default value."""
        lookup = {"on": "1", "off": "0"}
        hook1 = hc.hooks.create_converter(lookup)
        # If lookup returns None, we'd want a default

        result = hc.hooks.call_hooks([hook1], "on")
        assert result == "1"

        result = hc.hooks.call_hooks([hook1], "off")
        assert result == "0"

        result = hc.hooks.call_hooks([hook1], "invalid")
        assert result is None

    def test_scaling_and_clamping(self):
        """Test scaling followed by range validation."""
        # Scale by 0.5, then clamp to [0, 5]
        hook1 = hc.hooks.scaling_converter(0.5)
        hook2 = hc.hooks.range_validator(0, 5)

        result = hc.hooks.call_hooks([hook1, hook2], "8")
        # 8 * 0.5 = 4.0, within [0, 5]
        assert result == 4.0

        result = hc.hooks.call_hooks([hook1, hook2], "20")
        # 20 * 0.5 = 10.0, clamped to 5.0
        assert result == 5.0

    def test_negative_and_scale(self):
        """Test make_negative followed by scaling."""
        hook1 = hc.hooks.make_negative
        hook2 = hc.hooks.scaling_converter(2)

        result = hc.hooks.call_hooks([hook1, hook2], "5")
        # 5 -> -5.0, then -5.0 * 2 = -10.0
        assert result == "-10.0"

    def test_empty_hook_list(self):
        """Test that empty hook list returns value unchanged."""
        result = hc.hooks.call_hooks([], "test_value")
        assert result == "test_value"

        result = hc.hooks.call_hooks([], "123")
        assert result == "123"

    def test_single_hook(self):
        """Test single hook in list."""
        hook = hc.hooks.add_offset(100)
        result = hc.hooks.call_hooks([hook], "50")
        assert result == 150

    def test_max_len_with_formatting(self):
        """Test max_len combined with formatting."""
        hook1 = hc.hooks.format_float(".6f")  # Format to 6 decimals
        hook2 = hc.hooks.max_len_converter(5)  # Truncate to 5 chars

        result = hc.hooks.call_hooks([hook1, hook2], "3.14159")
        # "3.14159" -> "3.141590", truncate to "3.141"
        assert len(result) <= 5

    def test_bool_conversion_chain(self):
        """Test boolean conversion and validation."""
        hook1 = hc.hooks.format_bool  # Convert to "1" or "0"
        hook2 = hc.hooks.expected_input_validator(["0", "1"])

        result = hc.hooks.call_hooks([hook1, hook2], "True")
        assert result == "1"

        result = hc.hooks.call_hooks([hook1, hook2], "False")
        assert result == "0"

    def test_offset_then_format_int(self):
        """Test adding offset then formatting as int."""
        hook1 = hc.hooks.add_offset(5.7)
        hook2 = hc.hooks.format_int

        result = hc.hooks.call_hooks([hook1, hook2], "10.2")
        # 10.2 + 5.7 = 15.9, format_int -> "15"
        assert result == "15"
