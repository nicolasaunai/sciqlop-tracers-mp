"""SciQLop entry-point plugin (group `sciqlop.plugins`): adds 'MP ▾' buttons to plot panels."""
from __future__ import annotations

import logging
from types import SimpleNamespace

log = logging.getLogger(__name__)


def load(main_window):
    from .ui.attach import install_attach_buttons
    install_attach_buttons(main_window)
    log.info("TRACERS magnetopause map: attach buttons installed")
    return SimpleNamespace(name="sciqlop_tracers_mp")
