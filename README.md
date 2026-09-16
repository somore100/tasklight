# TaskLight

**A cross-platform macro automation tool** — inspired by classic tools like TinyTask, built with real Linux support in mind.

![Status](https://img.shields.io/badge/status-beta-yellow)
![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20Linux-lightgrey)

Record keyboard and mouse actions, replay them, and automate repetitive tasks — with extra customization most macro tools don't offer.

<p align="center">
  <img width="49%" alt="TaskLight main window" src="https://github.com/user-attachments/assets/4587b1ff-2e74-4bed-abb9-0483a6269ed6" />
  <img width="49%" alt="TaskLight macro editor" src="https://github.com/user-attachments/assets/c9e2e92e-0d7f-4763-acd1-2fa443cb04b5" />
</p>
<p align="center">
  <img width="70%" alt="TaskLight system tools" src="https://github.com/user-attachments/assets/a44c1e7b-62b3-4dfe-a676-12d863c74014" />
</p>

## Features

**Macro Recording**
- Record keyboard and mouse actions
- Replay recorded actions
- Save and reuse macros

**Automation Tools**
- Auto clicker
- Click duplication
- Custom keybinds
- Movement modification tools:
  - Smoothing
  - Jitter effects
  - Recorded movement adjustments

**System Tools**
- FPS monitor
- Ping monitor
- Performance tweaks

## Linux Support

Unlike many macro tools, TaskLight supports Linux natively — not just as an afterthought.

- **Best compatibility:** X11 sessions
- **Session switching** included for compatibility across different environments

## Supported Platforms

- Windows
- Linux

## Current Status

🟡 Close to finished — BETA

Main goals right now:
- Better reliability
- Improved Wayland compatibility

## Roadmap

- [ ] Better GUI
- [ ] More macro editing options
- [ ] Improved Linux compatibility
- [ ] Better profile management
- [ ] Export/import macro system

## Installation

```bash
git clone https://github.com/somore100/tasklight.git
cd tasklight
```

Install dependencies:
```bash
pip install -r requirements.txt
```

Run:
```bash
python main.py
```

## Contributing

Issues and pull requests are welcome — Wayland compatibility and macro editing are the areas most in need of help right now.

## License

This project is source-available software.

You are free to view, study, modify, fork, and share the project for non-commercial purposes. Addons, plugins, extensions, and integrations are also permitted under the license terms.

Commercial distribution of this project, or substantially derived versions of it, is not permitted without permission from the copyright holder.

See the [LICENSE](LICENSE) file for the full terms.

