#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright 2024 Daniel Nylander <daniel@danielnylander.se>

"""Main application window for Language Pack Inspector."""

import threading
import gettext

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, Gio, GLib, Pango

from langpack_inspector.backend import (
    get_system_language,
    list_installed_langpacks,
    scan_language,
    get_language_stats,
    MoFileInfo,
)

_ = gettext.gettext


class LangpackInspectorWindow(Adw.ApplicationWindow):
    """Main window."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.set_title(_("Language Pack Inspector"))
        self.set_default_size(900, 650)

        self._mo_files: list[MoFileInfo] = []
        self._current_lang = get_system_language()

        self._build_ui()
        GLib.idle_add(self._initial_scan)

    # ── UI Construction ──────────────────────────────────────────

    def _build_ui(self):
        # Main layout
        toolbar_view = Adw.ToolbarView()
        self.set_content(toolbar_view)

        # Header bar
        header = Adw.HeaderBar()
        toolbar_view.add_top_bar(header)

        # About button
        menu_btn = Gtk.MenuButton(icon_name="open-menu-symbolic")
        menu = Gio.Menu()
        menu.append(_("About"), "app.about")
        menu.append(_("Quit"), "app.quit")
        menu_btn.set_menu_model(menu)
        header.pack_end(menu_btn)

        # Refresh button
        refresh_btn = Gtk.Button(icon_name="view-refresh-symbolic")
        refresh_btn.set_tooltip_text(_("Refresh"))
        refresh_btn.connect("clicked", self._on_refresh)
        header.pack_start(refresh_btn)

        # Content
        content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        toolbar_view.set_content(content_box)

        # Language selector bar
        lang_bar = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL,
            spacing=12,
            margin_start=12, margin_end=12, margin_top=12, margin_bottom=6,
        )
        content_box.append(lang_bar)

        lang_label = Gtk.Label(label=_("Language:"))
        lang_bar.append(lang_label)

        self._lang_entry = Gtk.Entry()
        self._lang_entry.set_text(self._current_lang)
        self._lang_entry.set_max_width_chars(10)
        self._lang_entry.set_placeholder_text("sv")
        self._lang_entry.connect("activate", self._on_lang_changed)
        lang_bar.append(self._lang_entry)

        scan_btn = Gtk.Button(label=_("Scan"))
        scan_btn.add_css_class("suggested-action")
        scan_btn.connect("clicked", self._on_lang_changed)
        lang_bar.append(scan_btn)

        # Stats banner
        self._stats_label = Gtk.Label(
            label="", xalign=0,
            margin_start=12, margin_end=12, margin_top=6, margin_bottom=6,
        )
        self._stats_label.add_css_class("dim-label")
        content_box.append(self._stats_label)

        # Installed packs list (collapsible)
        self._packs_expander = Gtk.Expander(label=_("Installed Language Packs"))
        self._packs_expander.set_margin_start(12)
        self._packs_expander.set_margin_end(12)
        self._packs_expander.set_margin_bottom(6)
        self._packs_label = Gtk.Label(label="", xalign=0, wrap=True)
        self._packs_expander.set_child(self._packs_label)
        content_box.append(self._packs_expander)

        # Separator
        content_box.append(Gtk.Separator())

        # Scrolled list of .mo files
        sw = Gtk.ScrolledWindow(vexpand=True)
        content_box.append(sw)

        self._listbox = Gtk.ListBox()
        self._listbox.set_selection_mode(Gtk.SelectionMode.NONE)
        self._listbox.add_css_class("boxed-list")
        self._listbox.set_margin_start(12)
        self._listbox.set_margin_end(12)
        self._listbox.set_margin_top(6)
        self._listbox.set_margin_bottom(12)
        sw.set_child(self._listbox)

        # Search/filter
        self._search_entry = Gtk.SearchEntry()
        self._search_entry.set_placeholder_text(_("Filter domains…"))
        self._search_entry.set_margin_start(12)
        self._search_entry.set_margin_end(12)
        self._search_entry.connect("search-changed", self._on_filter_changed)
        lang_bar.append(self._search_entry)

        # Spinner overlay
        self._spinner = Gtk.Spinner()
        self._spinner.set_halign(Gtk.Align.CENTER)
        self._spinner.set_valign(Gtk.Align.CENTER)
        lang_bar.append(self._spinner)

    # ── Actions ──────────────────────────────────────────────────

    def _initial_scan(self):
        self._start_scan()
        return False

    def _on_refresh(self, *args):
        self._start_scan()

    def _on_lang_changed(self, *args):
        self._current_lang = self._lang_entry.get_text().strip()
        if self._current_lang:
            self._start_scan()

    def _on_filter_changed(self, entry):
        query = entry.get_text().lower()
        self._populate_list(
            [m for m in self._mo_files if query in m.domain.lower()]
            if query else self._mo_files
        )

    def _start_scan(self):
        self._spinner.start()
        self._stats_label.set_text(_("Scanning…"))

        lang = self._current_lang
        thread = threading.Thread(target=self._scan_worker, args=(lang,), daemon=True)
        thread.start()

    def _scan_worker(self, lang: str):
        packs = list_installed_langpacks()
        mo_files = scan_language(lang)
        stats = get_language_stats(mo_files)
        GLib.idle_add(self._scan_done, packs, mo_files, stats, lang)

    def _scan_done(self, packs, mo_files, stats, lang):
        self._spinner.stop()
        self._mo_files = mo_files

        # Update packs list
        lang_packs = [p for p in packs if p.language == lang or lang in p.name]
        if lang_packs:
            txt = "\n".join(f"• {p.name} ({p.version})" for p in lang_packs)
        else:
            txt = _("No language packs found for '%s'") % lang
        self._packs_label.set_text(txt)

        # Update stats
        self._stats_label.set_text(
            _("Language: {lang} — {translated}/{total} strings translated "
              "({pct:.1f}%) — {files} .mo files — {outdated} outdated").format(
                lang=lang,
                translated=stats["translated"],
                total=stats["total_strings"],
                pct=stats["coverage_pct"],
                files=stats["num_mo_files"],
                outdated=stats["outdated_files"],
            )
        )

        self._populate_list(mo_files)
        return False

    def _populate_list(self, mo_files: list[MoFileInfo]):
        # Clear
        while True:
            row = self._listbox.get_row_at_index(0)
            if row is None:
                break
            self._listbox.remove(row)

        for mo in mo_files:
            row = self._create_mo_row(mo)
            self._listbox.append(row)

    def _create_mo_row(self, mo: MoFileInfo) -> Gtk.ListBoxRow:
        row = Adw.ActionRow()
        row.set_title(mo.domain)

        subtitle_parts = []
        if mo.package:
            subtitle_parts.append(mo.package)
        subtitle_parts.append(
            _("{translated}/{total} ({pct:.0f}%)").format(
                translated=mo.translated,
                total=mo.total,
                pct=mo.coverage_pct,
            )
        )
        if mo.mtime:
            subtitle_parts.append(mo.mtime.strftime("%Y-%m-%d"))
        row.set_subtitle(" · ".join(subtitle_parts))

        # Coverage indicator
        if mo.coverage_pct >= 90:
            icon_name = "emblem-ok-symbolic"
            css = "success"
        elif mo.coverage_pct >= 50:
            icon_name = "dialog-warning-symbolic"
            css = "warning"
        else:
            icon_name = "dialog-error-symbolic"
            css = "error"

        icon = Gtk.Image.new_from_icon_name(icon_name)
        icon.add_css_class(css)
        row.add_prefix(icon)

        # Outdated badge
        if mo.is_outdated:
            badge = Gtk.Label(label=_("old"))
            badge.add_css_class("error")
            badge.set_valign(Gtk.Align.CENTER)
            row.add_suffix(badge)

        # Launchpad link button
        if mo.launchpad_url:
            link_btn = Gtk.LinkButton(uri=mo.launchpad_url)
            link_btn.set_label(_("Translate"))
            link_btn.set_valign(Gtk.Align.CENTER)
            row.add_suffix(link_btn)

        return row
