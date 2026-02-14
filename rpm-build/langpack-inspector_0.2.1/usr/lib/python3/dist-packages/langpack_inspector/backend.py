#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright 2024 Daniel Nylander <daniel@danielnylander.se>

"""Backend logic for scanning language packs, .mo files, and Launchpad API."""

import os
import subprocess
import struct
import locale
import gettext
import datetime
import json
import urllib.request
import urllib.error
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional

_ = gettext.gettext

LAUNCHPAD_API = "https://api.launchpad.net/devel"


@dataclass
class MoFileInfo:
    """Information about a single .mo file."""
    path: str
    domain: str
    package: str
    translated: int = 0
    untranslated: int = 0
    total: int = 0
    mtime: Optional[datetime.datetime] = None
    launchpad_url: str = ""

    @property
    def coverage_pct(self) -> float:
        if self.total == 0:
            return 0.0
        return (self.translated / self.total) * 100.0

    @property
    def is_outdated(self) -> bool:
        """Consider outdated if older than 180 days."""
        if self.mtime is None:
            return False
        age = datetime.datetime.now() - self.mtime
        return age.days > 180


@dataclass
class LanguagePackInfo:
    """Information about an installed language pack."""
    name: str
    version: str = ""
    language: str = ""
    mo_files: list = field(default_factory=list)

    @property
    def total_translated(self) -> int:
        return sum(m.translated for m in self.mo_files)

    @property
    def total_strings(self) -> int:
        return sum(m.total for m in self.mo_files)

    @property
    def coverage_pct(self) -> float:
        if self.total_strings == 0:
            return 0.0
        return (self.total_translated / self.total_strings) * 100.0


def get_system_language() -> str:
    """Get system language code (e.g. 'sv', 'de', 'fr')."""
    lang = locale.getdefaultlocale()[0]
    if lang:
        return lang.split("_")[0]
    return "en"


def list_installed_langpacks() -> list[LanguagePackInfo]:
    """List installed language-pack-* packages using dpkg."""
    packs = []
    try:
        result = subprocess.run(
            ["dpkg-query", "-W", "-f", "${Package}\t${Version}\t${Status}\n",
             "language-pack-*"],
            capture_output=True, text=True, timeout=10
        )
        for line in result.stdout.strip().splitlines():
            parts = line.split("\t")
            if len(parts) >= 3 and "installed" in parts[2]:
                name = parts[0]
                version = parts[1]
                # Extract language code from package name
                lang = name.replace("language-pack-gnome-", "").replace(
                    "language-pack-kde-", "").replace("language-pack-", "")
                packs.append(LanguagePackInfo(
                    name=name, version=version, language=lang
                ))
    except (subprocess.SubprocessError, FileNotFoundError):
        pass
    return packs


def list_mo_files_for_language(lang: str) -> list[str]:
    """Find all .mo files for a given language under /usr/share/locale."""
    locale_dir = Path(f"/usr/share/locale/{lang}/LC_MESSAGES")
    mo_files = []
    if locale_dir.exists():
        mo_files.extend(str(p) for p in locale_dir.glob("*.mo"))
    # Also check locale variants like sv_SE
    for variant_dir in Path("/usr/share/locale").glob(f"{lang}_*/LC_MESSAGES"):
        mo_files.extend(str(p) for p in variant_dir.glob("*.mo"))
    return sorted(set(mo_files))


def parse_mo_file(path: str) -> tuple[int, int]:
    """Parse a .mo file and return (translated, total) string counts.

    Returns (translated, total). Untranslated = total - translated.
    """
    try:
        with open(path, "rb") as f:
            data = f.read()

        # MO file magic number
        magic = struct.unpack("<I", data[:4])[0]
        if magic == 0x950412de:
            fmt = "<"
        elif magic == 0xde120495:
            fmt = ">"
        else:
            return (0, 0)

        # Number of strings
        nstrings = struct.unpack(f"{fmt}I", data[8:12])[0]
        orig_offset = struct.unpack(f"{fmt}I", data[12:16])[0]
        trans_offset = struct.unpack(f"{fmt}I", data[16:20])[0]

        translated = 0
        total = 0

        for i in range(nstrings):
            # Skip the metadata entry (empty msgid)
            o_len = struct.unpack(
                f"{fmt}I", data[orig_offset + i * 8: orig_offset + i * 8 + 4]
            )[0]
            t_len = struct.unpack(
                f"{fmt}I", data[trans_offset + i * 8: trans_offset + i * 8 + 4]
            )[0]

            if o_len == 0:
                continue  # metadata entry

            total += 1
            if t_len > 0:
                translated += 1

        return (translated, total)
    except Exception:
        return (0, 0)


def get_mo_file_info(path: str, lang: str, package: str = "") -> MoFileInfo:
    """Get detailed info about a .mo file."""
    domain = Path(path).stem
    translated, total = parse_mo_file(path)

    mtime = None
    try:
        stat = os.stat(path)
        mtime = datetime.datetime.fromtimestamp(stat.st_mtime)
    except OSError:
        pass

    lp_url = (
        f"https://translations.launchpad.net/ubuntu/+source/{domain}/+pots/"
        f"{domain}/{lang}/+translate"
    )

    return MoFileInfo(
        path=path,
        domain=domain,
        package=package,
        translated=translated,
        untranslated=total - translated,
        total=total,
        mtime=mtime,
        launchpad_url=lp_url,
    )


def scan_language(lang: str) -> list[MoFileInfo]:
    """Scan all .mo files for a language and return info list."""
    mo_paths = list_mo_files_for_language(lang)
    results = []

    # Try to map .mo files to packages
    mo_to_pkg = {}
    try:
        result = subprocess.run(
            ["dpkg", "-S"] + mo_paths[:50],  # limit to avoid arg too long
            capture_output=True, text=True, timeout=15
        )
        for line in result.stdout.strip().splitlines():
            if ": " in line:
                pkg, fpath = line.split(": ", 1)
                mo_to_pkg[fpath.strip()] = pkg.strip()
    except (subprocess.SubprocessError, FileNotFoundError):
        pass

    for mo_path in mo_paths:
        pkg = mo_to_pkg.get(mo_path, "")
        info = get_mo_file_info(mo_path, lang, package=pkg)
        results.append(info)

    return results


def get_language_stats(mo_files: list[MoFileInfo]) -> dict:
    """Compute aggregate statistics for a list of MoFileInfo."""
    total = sum(m.total for m in mo_files)
    translated = sum(m.translated for m in mo_files)
    outdated = sum(1 for m in mo_files if m.is_outdated)
    return {
        "total_strings": total,
        "translated": translated,
        "untranslated": total - translated,
        "coverage_pct": (translated / total * 100) if total > 0 else 0,
        "num_mo_files": len(mo_files),
        "outdated_files": outdated,
    }


def fetch_launchpad_templates(source_package: str, series: str = "noble") -> list[dict]:
    """Fetch translation template info from Launchpad API for a source package."""
    url = (
        f"{LAUNCHPAD_API}/ubuntu/{series}/+source/{source_package}"
        f"/+pot"
    )
    try:
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
            if "entries" in data:
                return data["entries"]
            return [data]
    except (urllib.error.URLError, json.JSONDecodeError, Exception):
        return []
