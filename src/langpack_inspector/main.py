#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright 2024 Daniel Nylander <daniel@danielnylander.se>

"""Main entry point for Language Pack Inspector."""

import sys
import locale
import gettext

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
# Optional desktop notifications
try:
    gi.require_version("Notify", "0.7")
    from gi.repository import Gtk, Notify as _Notify
    HAS_NOTIFY = True
except (ValueError, ImportError):
    HAS_NOTIFY = False
from gi.repository import Gtk, Adw, Gio, GLib

from langpack_inspector import __version__, __app_id__
from langpack_inspector.window import LangpackInspectorWindow

# i18n
LOCALE_DIR = "/usr/share/locale"
gettext.bindtextdomain("langpack-inspector", LOCALE_DIR)
gettext.textdomain("langpack-inspector")
_ = gettext.gettext



import json as _json
import platform as _platform
from pathlib import Path as _Path

_NOTIFY_APP = "langpack-inspector"


def _notify_config_path():
    return _Path(GLib.get_user_config_dir()) / _NOTIFY_APP / "notifications.json"


def _load_notify_config():
    try:
        return _json.loads(_notify_config_path().read_text())
    except Exception:
        return {"enabled": False}


def _save_notify_config(config):
    p = _notify_config_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(_json.dumps(config))


def _send_notification(summary, body="", icon="dialog-information"):
    if HAS_NOTIFY and _load_notify_config().get("enabled"):
        try:
            n = _Notify.Notification.new(summary, body, icon)
            n.show()
        except Exception:
            pass


def _get_system_info():
    return "\n".join([
        f"App: Language Pack Inspector",
        f"Version: {__version__}",
        f"GTK: {Gtk.get_major_version()}.{Gtk.get_minor_version()}.{Gtk.get_micro_version()}",
        f"Adw: {Adw.get_major_version()}.{Adw.get_minor_version()}.{Adw.get_micro_version()}",
        f"Python: {_platform.python_version()}",
        f"OS: {_platform.system()} {_platform.release()} ({_platform.machine()})",
    ])


class LangpackInspectorApp(Adw.Application):
    """Main application class."""

    def __init__(self):
        super().__init__(
            application_id=__app_id__,
            flags=Gio.ApplicationFlags.DEFAULT_FLAGS,
        )
        self.set_resource_base_path("/se/danielnylander/LangpackInspector")

    def do_activate(self):
        win = self.props.active_window
        if not win:
            win = LangpackInspectorWindow(application=self)
        win.present()

    def do_startup(self):
        Adw.Application.do_startup(self)
        self._setup_actions()

        self.set_accels_for_action("app.refresh", ["F5"])
        self.set_accels_for_action("app.shortcuts", ["<Control>slash"])
        refresh_action = Gio.SimpleAction.new("refresh", None)
        refresh_action.connect("activate", lambda *_: self._do_refresh())
        self.add_action(refresh_action)
        shortcuts_action = Gio.SimpleAction.new("shortcuts", None)
        shortcuts_action.connect("activate", self._show_shortcuts_window)
        self.add_action(shortcuts_action)

    def _setup_actions(self):
        about_action = Gio.SimpleAction.new("about", None)
        about_action.connect("activate", self._on_about)
        self.add_action(about_action)

        quit_action = Gio.SimpleAction.new("quit", None)
        quit_action.connect("activate", lambda *_: self.quit())
        self.add_action(quit_action)
        self.set_accels_for_action("app.quit", ["<Control>q"])

    def _on_about(self, action, param):
        about = Adw.AboutDialog(
            application_name=_("Language Pack Inspector"),
            application_icon="langpack-inspector",
            developer_name="Daniel Nylander",
            version=__version__,
            developers=["Daniel Nylander <daniel@danielnylander.se>"],
            copyright="© 2024 Daniel Nylander",
            license_type=Gtk.License.GPL_3_0,
            website="https://github.com/yeager/langpack-inspector",
            issue_url="https://github.com/yeager/langpack-inspector/issues",
            translate_url="https://app.transifex.com/danielnylander/langpack-inspector/",
            comments=_("A localization tool by Daniel Nylander"),
            translator_credits=_("Translate this app: https://app.transifex.com/danielnylander/langpack-inspector/"),
        )
        about.present(self.props.active_window)


def main():
    app = LangpackInspectorApp()
    return app.run(sys.argv)


if __name__ == "__main__":
    sys.exit(main())

    def _do_refresh(self):
        w = self.get_active_window()
        if w and hasattr(w, '_load_data'): w._load_data(force=True)
        elif w and hasattr(w, '_on_refresh'): w._on_refresh(None)

    def _show_shortcuts_window(self, *_args):
        win = Gtk.ShortcutsWindow(transient_for=self.get_active_window(), modal=True)
        section = Gtk.ShortcutsSection(visible=True, max_height=10)
        group = Gtk.ShortcutsGroup(visible=True, title="General")
        for accel, title in [("<Control>q", "Quit"), ("F5", "Refresh"), ("<Control>slash", "Keyboard shortcuts")]:
            s = Gtk.ShortcutsShortcut(visible=True, accelerator=accel, title=title)
            group.append(s)
        section.append(group)
        win.add_child(section)
        win.present()

