"""Tests for Dataset functionality."""

import tempfile
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from hardware_control.base.Dataset import Dataset


class TestDataset:
    """Test Dataset class basic functionality."""

    def test_init_basic(self):
        """Test basic Dataset initialization."""
        ds = Dataset("test_dataset")
        assert ds.name == "test_dataset"
        assert len(ds.data) == 0
        assert ds.update_interval == 10.0
        assert ds.autosave_enabled is False

    def test_manual_data_addition(self):
        """Test manually adding data to dataset."""
        ds = Dataset("test")

        # Manually add channels
        ds.data["inst1:voltage"].extend(["5.0", "6.0", "7.0"])
        ds.data["inst1:current"].extend(["0.5", "0.6", "0.7"])

        assert len(ds.data["inst1:voltage"]) == 3
        assert ds.data["inst1:voltage"] == ["5.0", "6.0", "7.0"]
        assert ds.data["inst1:current"] == ["0.5", "0.6", "0.7"]

    def test_to_pandas(self):
        """Test converting data to pandas DataFrame."""
        pandas = pytest.importorskip("pandas")

        ds = Dataset("test")
        ds.data["inst1:voltage"].extend(["5.0", "6.0"])
        ds.data["inst1:current"].extend(["0.5", "0.6"])

        df = ds.to_pandas()
        assert isinstance(df, pandas.DataFrame)
        assert "inst1:voltage" in df.columns
        assert "inst1:current" in df.columns
        assert len(df) == 2

    def test_header_get_instruments(self):
        """Test header generation with instrument names."""
        ds = Dataset("test")
        ds.data["inst1:voltage"].append("5.0")
        ds.data["inst2:temperature"].append("25.0")

        header = ds.header_get_instruments()
        assert "voltage" in header
        assert "temperature" in header

    def test_clear_data(self):
        """Test clearing dataset."""
        ds = Dataset("test")
        ds.data["inst1:voltage"].extend(["5.0", "6.0"])
        ds.data["inst2:current"].extend(["0.5", "0.6"])

        assert len(ds.data["inst1:voltage"]) == 2

        ds.clear()

        assert len(ds.data["inst1:voltage"]) == 0
        assert ds.autosave_next_row == 0

    def test_save_txt(self):
        """Test saving data to text file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / "test_output.txt"
            ds = Dataset("test")

            # Add data
            ds.data["inst1:voltage"].extend(["5.0", "6.0"])
            ds.data["inst1:current"].extend(["0.5", "0.6"])

            ds.save_txt(filepath)

            assert filepath.exists()
            content = filepath.read_text()
            assert "5.0" in content
            assert "6.0" in content
            assert "0.5" in content

    def test_save_json(self):
        """Test saving data to JSON file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / "test_output.json"
            ds = Dataset("test")
            ds.data["inst1:voltage"].extend(["5.0", "6.0"])

            ds.save_json(filepath)

            assert filepath.exists()

    def test_length(self):
        """Test dataset length calculation."""
        ds = Dataset("test")
        assert len(ds) == 0

        ds.data["inst1:voltage"].extend(["1.0", "2.0", "3.0"])

        assert len(ds) == 3

    def test_get_columns(self):
        """Test getting specific columns from dataset."""
        ds = Dataset("test")
        ds.data["inst1:voltage"].extend(["5.0", "6.0"])
        ds.data["inst1:current"].extend(["0.5", "0.6"])
        ds.data["inst1:power"].extend(["2.5", "3.6"])

        columns = ds.get_columns(["inst1:voltage", "inst1:current"])

        assert "inst1:voltage" in columns
        assert "inst1:current" in columns
        assert "inst1:power" not in columns
        assert len(columns["inst1:voltage"]) == 2

    def test_data_order_preservation(self):
        """Test that data order is preserved as added."""
        ds = Dataset("test")
        # Add in specific order
        ds.data["inst3:param3"].append("1")
        ds.data["inst1:param1"].append("2")
        ds.data["inst2:param2"].append("3")

        # Keys should maintain insertion order (Python 3.7+)
        keys = list(ds.data.keys())
        assert keys[0] == "inst3:param3"
        assert keys[1] == "inst1:param1"
        assert keys[2] == "inst2:param2"

    def test_channel_names_dict(self):
        """Test that channel_names dictionary works."""
        ds = Dataset("test")
        ds.channel_names["inst1:voltage"] = "Supply V"
        ds.channel_names["inst2:current"] = "Current A"

        assert ds.channel_names["inst1:voltage"] == "Supply V"
        assert ds.channel_names["inst2:current"] == "Current A"
