"""Tests for GUI helpers."""

from __future__ import annotations

import tkinter as tk

from pypi_profile.gui import maximize_window


class FakeWindow:
    """Minimal stand-in for a Tk window."""

    def __init__(self, fail_zoom: bool = False) -> None:
        self.fail_zoom = fail_zoom
        self.state_calls: list[str] = []
        self.geometry_calls: list[str] = []

    def state(self, newstate: str | None = None) -> str:
        if newstate is None:
            return ""
        self.state_calls.append(newstate)
        if self.fail_zoom:
            raise tk.TclError("zoom unsupported")
        return newstate

    def geometry(self, new_geometry: str | None = None) -> str:
        if new_geometry is None:
            return ""
        self.geometry_calls.append(new_geometry)
        return new_geometry

    def winfo_screenwidth(self) -> int:
        return 1920

    def winfo_screenheight(self) -> int:
        return 1080


def test_maximize_window_prefers_zoomed_state() -> None:
    window = FakeWindow()

    maximize_window(window)

    assert window.state_calls == ["zoomed"]
    assert window.geometry_calls == []


def test_maximize_window_falls_back_to_screen_geometry() -> None:
    window = FakeWindow(fail_zoom=True)

    maximize_window(window)

    assert window.state_calls == ["zoomed"]
    assert window.geometry_calls == ["1920x1080+0+0"]
