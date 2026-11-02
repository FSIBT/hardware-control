"""Tests for the widgets that change the remote access settings."""

import os
from unittest.mock import MagicMock

import pytest
from PyQt6.QtCore import QPoint
from PyQt6.QtWidgets import QApplication, QStatusBar

from hardware_control.base.HCMainWindow import HCMainWindow
from hardware_control.base.remote_access import AccessMode, RemoteAccess
from hardware_control.base.remote_access_gui import (
    RemoteAccessIndicator,
    RemoteAccessPopup,
)


@pytest.fixture(scope="module")
def qapp():
    # no display is needed, e.g. in CI
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    yield QApplication.instance() or QApplication([])


@pytest.fixture
def app(qapp, tmp_path):
    fake = MagicMock()
    fake.remote_access = RemoteAccess("gui", tmp_path)
    fake.set_remote_access = fake.remote_access.configure
    return fake


@pytest.fixture
def popup(app):
    widget = RemoteAccessPopup(app)
    widget.load()
    return widget


def test_popup_shows_current_settings(app):
    app.remote_access.configure("read-only", "2h", persist=True, token="secret")
    popup = RemoteAccessPopup(app)
    popup.load()
    assert popup.selected_mode() is AccessMode.READ_ONLY
    assert popup.keep.isChecked()
    assert popup.duration.text() == "2h"
    assert popup.token.text() == ""
    assert popup.token.placeholderText() == "set"


def test_popup_defaults(popup):
    assert popup.selected_mode() is AccessMode.OFF
    assert popup.duration.text() == "0"
    assert not popup.keep.isChecked()


def test_apply(app, popup):
    popup.mode_buttons[AccessMode.FULL].setChecked(True)
    popup.duration.setText("1h30m")
    popup.keep.setChecked(True)
    popup.apply()
    assert app.remote_access.mode is AccessMode.FULL
    assert 5300 < app.remote_access.remaining() <= 5400
    assert app.remote_access.persist


def test_apply_invalid_duration_keeps_settings(app, popup):
    popup.mode_buttons[AccessMode.FULL].setChecked(True)
    popup.duration.setText("soon")
    popup.apply()
    assert app.remote_access.mode is AccessMode.OFF
    assert "Invalid duration" in popup.message.text()


def test_generated_token_is_used(app, popup):
    popup.generate()
    token = popup.token.text()
    popup.mode_buttons[AccessMode.FULL].setChecked(True)
    popup.apply()
    assert app.remote_access.check_token(token)
    assert not app.remote_access.check_token("wrong")


def test_apply_keeps_token_unless_cleared(app):
    app.remote_access.configure("full", token="secret")
    popup = RemoteAccessPopup(app)
    popup.load()
    popup.apply()
    assert app.remote_access.token_required
    popup.load()
    popup.clear()
    popup.apply()
    assert not app.remote_access.token_required


def test_indicator(app):
    indicator = RemoteAccessIndicator(app)
    assert indicator.text() == "Remote: Off"
    app.remote_access.configure("read-only", "90")
    indicator.refresh()
    assert indicator.text() == "Remote: Read-only (1h30m)"
    assert "darkorange" in indicator.styleSheet()


def test_indicator_opens_popup(app):
    indicator = RemoteAccessIndicator(app)
    indicator.open_popup()
    assert indicator.popup.isVisible()
    indicator.popup.close()


def main_window(app):
    return HCMainWindow(app=app)


def test_no_status_bar_is_created(app):
    window = main_window(app)
    assert window.remote_access_indicator is None
    assert window.findChild(QStatusBar) is None
    assert "Remote Access" in [a.text() for a in window.bar.actions()]


def test_menu_opens_popup(app):
    window = main_window(app)
    window.remote_access_act.trigger()
    assert window.remote_access_popup.isVisible()
    window.remote_access_popup.close()


def test_indicator_in_own_status_bar(app):
    window = main_window(app)
    statusbar = QStatusBar()
    window.setStatusBar(statusbar)
    assert window.remote_access_indicator.parent() is statusbar


def test_indicator_in_default_status_bar_only_once(app):
    window = main_window(app)
    statusbar = window.statusBar()
    indicator = window.remote_access_indicator
    assert window.statusBar() is statusbar
    assert window.remote_access_indicator is indicator
    assert indicator.parent() is statusbar


def test_show_at_position(popup):
    popup.show_at(QPoint(500, 500))
    assert popup.isVisible()
    popup.close()
