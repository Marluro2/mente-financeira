import inspect

import flet as ft

from main import select_app_view
from mente_financeira.ui.theme import PALETTES
from mente_financeira.ui.whiteboard import Whiteboard


def test_whiteboard_uses_current_drag_event_coordinates() -> None:
    source = inspect.getsource(Whiteboard._start_stroke) + inspect.getsource(Whiteboard._draw_stroke)
    assert "local_x" not in source
    assert "local_y" not in source
    assert "event.local_position" in source


def test_whiteboard_control_tree_can_be_created() -> None:
    board = Whiteboard(PALETTES["kids"], dark_mode=False)
    assert isinstance(board.panel, ft.Container)
    assert board.canvas.shapes == []
    assert len(board.tools.controls) == 8


def test_windows_uses_browser_without_starting_desktop_client() -> None:
    assert select_app_view(platform="win32", configured_view="") == ft.AppView.WEB_BROWSER


def test_launch_mode_can_be_overridden() -> None:
    assert select_app_view(platform="win32", configured_view="desktop") == ft.AppView.FLET_APP
    assert select_app_view(platform="linux", configured_view="web") == ft.AppView.WEB_BROWSER
