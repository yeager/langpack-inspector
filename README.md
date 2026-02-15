# Language Pack Inspector

A GTK4/Adwaita application for inspecting Ubuntu language packs and finding missing or outdated translations.

![License: GPL-3.0](https://img.shields.io/badge/License-GPL--3.0-blue.svg)

## Features

- List installed language packs (`language-pack-*`)
- Show contents: which `.mo` files are included per package
- Compare with available templates on Launchpad (via API)
- Display translated/untranslated string counts per `.mo` file
- Flag old/outdated translations (by date comparison)
- Language chooser (defaults to system language)
- Statistics: total coverage per language
- Direct links to Launchpad for translating missing strings

## Installation

### From .deb (Ubuntu/Debian)

```bash
# Add the repository
curl -fsSL https://yeager.github.io/debian-repo/pubkey.gpg | sudo gpg --dearmor -o /usr/share/keyrings/yeager.gpg
echo "deb [signed-by=/usr/share/keyrings/yeager.gpg] https://yeager.github.io/debian-repo stable main" | sudo tee /etc/apt/sources.list.d/yeager.list
sudo apt update
sudo apt install langpack-inspector
```

### From source

```bash
pip install .
langpack-inspector
```

## Requirements

- Python 3.10+
- GTK 4
- libadwaita 1
- PyGObject

On Ubuntu/Debian:

```bash
sudo apt install python3-gi gir1.2-gtk-4.0 gir1.2-adw-1 python3-gi-cairo
```

## 🌍 Contributing Translations

Help translate this app into your language! All translations are managed via Transifex.

**→ [Translate on Transifex](https://app.transifex.com/danielnylander/langpack-inspector/)**

### How to contribute:
1. Visit the [Transifex project page](https://app.transifex.com/danielnylander/langpack-inspector/)
2. Create a free account (or log in)
3. Select your language and start translating

### Currently supported languages:
Arabic, Czech, Danish, German, Spanish, Finnish, French, Italian, Japanese, Korean, Norwegian Bokmål, Dutch, Polish, Brazilian Portuguese, Russian, Swedish, Ukrainian, Chinese (Simplified)

### Notes:
- Please do **not** submit pull requests with .po file changes — they are synced automatically from Transifex
- Source strings are pushed to Transifex daily via GitHub Actions
- Translations are pulled back and included in releases

New language? Open an [issue](https://github.com/yeager/langpack-inspector/issues) and we'll add it!
## License

GPL-3.0-or-later. See [LICENSE](LICENSE).

## Author

Daniel Nylander <daniel@danielnylander.se>
