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



def _settings_path():
    import os
    xdg = os.environ.get("XDG_CONFIG_HOME", os.path.expanduser("~/.config"))
    d = os.path.join(xdg, "langpack-inspector")
    os.makedirs(d, exist_ok=True)
    return os.path.join(d, "settings.json")

def _load_settings():
    import os, json
    p = _settings_path()
    if os.path.exists(p):
        with open(p) as f:
            return json.load(f)
    return {}

def _save_settings(s):
    import json
    with open(_settings_path(), "w") as f:
        json.dump(s, f, indent=2)

class LangpackInspectorApp(Adw.Application):
    """Main application class."""

    def __init__(self):
        super().__init__(
            application_id=__app_id__,
            flags=Gio.ApplicationFlags.DEFAULT_FLAGS,
        )
        self.set_resource_base_path("/se/danielnylander/LangpackInspector")
        if HAS_NOTIFY:
            _Notify.init("langpack-inspector")

    def do_activate(self):
        self.settings = _load_settings()
        win = self.props.active_window
        if not win:
            win = LangpackInspectorWindow(application=self)
        win.present()
        if not self.settings.get("welcome_shown"):
            self._show_welcome(self if hasattr(self, "set_content") else win)


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

        notif_action = Gio.SimpleAction.new("toggle-notifications", None)
        notif_action.connect("activate", lambda *_: _save_notify_config({"enabled": not _load_notify_config().get("enabled", False)}))
        self.add_action(notif_action)

        quit_action = Gio.SimpleAction.new("quit", None)
        quit_action.connect("activate", lambda *_: self.quit())
        self.add_action(quit_action)
        self.set_accels_for_action("app.quit", ["<Control>q"])
        self.set_accels_for_action("app.export", ["<Control>e"])
        export_action = Gio.SimpleAction.new("export", None)
        export_action.connect("activate", lambda *_: self.props.active_window and self.props.active_window._on_export_clicked())
        self.add_action(export_action)

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
            translator_credits=_("Translate this app: https://www.transifex.com/danielnylander/langpack-inspector/"),
        )
        about.set_debug_info(_get_system_info())
        about.set_debug_info_filename("langpack-inspector-debug.txt")
        about.present(self.props.active_window)



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



def main():
    app = LangpackInspectorApp()
    return app.run(sys.argv)


if __name__ == "__main__":
    sys.exit(main())

    # ── Welcome Dialog ───────────────────────────────────────

    def _show_welcome(self, win):
        dialog = Adw.Dialog()
        dialog.set_title(_("Welcome"))
        dialog.set_content_width(420)
        dialog.set_content_height(480)

        page = Adw.StatusPage()
        page.set_icon_name("system-search-symbolic")
        page.set_title(_("Welcome to Language Pack Inspector"))
        page.set_description(_(
            "Inspect and analyze language packs.\n\n✓ Browse installed language packs\n✓ Check translation coverage\n✓ Find missing translations\n✓ Compare language packs"
        ))

        btn = Gtk.Button(label=_("Get Started"))
        btn.add_css_class("suggested-action")
        btn.add_css_class("pill")
        btn.set_halign(Gtk.Align.CENTER)
        btn.set_margin_top(12)
        btn.connect("clicked", self._on_welcome_close, dialog)
        page.set_child(btn)

        box = Adw.ToolbarView()
        hb = Adw.HeaderBar()
        hb.set_show_title(False)
        box.add_top_bar(hb)
        box.set_content(page)
        dialog.set_child(box)
        dialog.present(win)

    def _on_welcome_close(self, btn, dialog):
        self.settings["welcome_shown"] = True
        _save_settings(self.settings)
        dialog.close()

