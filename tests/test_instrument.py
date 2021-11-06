"""Test some instrument driver functionality"""
import hardware_control as hc


class TestInstrument:
    def test_read_parameters(self):
        """make sure we can use attributes and [] to access values in an instrument"""
        # setup
        self.instrument = hc.instruments.Alicat_M_Series("alicat", "127.0.0.1:1111")
        self.instrument._dummy = True

        # overwrite dummy output
        for i, name in enumerate(self.instrument.read_commands):
            self.instrument.dummy_returns[name] = i

            # test dictionary access
            assert self.instrument[name] == i
            assert self.instrument.get_value(name) == i

        # overwrite dummy output to a fixed value
        for name in self.instrument.read_commands:
            self.instrument.dummy_returns[name] = 2.2

        # test attribute access
        assert self.instrument.RATE == 2.2
        assert self.instrument.PRESSURE == 2.2
