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
from gi.repository import Gtk, Adw, Gio, GLib

from langpack_inspector import __version__, __app_id__
from langpack_inspector.window import LangpackInspectorWindow

# i18n
LOCALE_DIR = "/usr/share/locale"
gettext.bindtextdomain("langpack-inspector", LOCALE_DIR)
gettext.textdomain("langpack-inspector")
_ = gettext.gettext


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
            application_icon="applications-other",
            developer_name="Daniel Nylander",
            version=__version__,
            developers=["Daniel Nylander <daniel@danielnylander.se>"],
            copyright="© 2024 Daniel Nylander",
            license_type=Gtk.License.GPL_3_0,
            website="https://github.com/yeager/langpack-inspector",
            issue_url="https://github.com/yeager/langpack-inspector/issues",
        )
        about.present(self.props.active_window)


def main():
    app = LangpackInspectorApp()
    return app.run(sys.argv)


if __name__ == "__main__":
    sys.exit(main())
