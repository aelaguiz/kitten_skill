# Kitten Terminal Remote Control Skill

Control your Kitty terminal windows from Claude Code, Codex CLI, or any agent. This skill provides comprehensive access to Kitty's remote control capabilities.

## Features

- **List Windows**: See all OS windows, tabs, and terminal windows with process info
- **Read Output**: Get screen content, scrollback, or last command output
- **Send Commands**: Type text, press keys, or run commands in any window
- **Window Management**: Launch, focus, close, resize, and scroll windows
- **Appearance**: Change colors, opacity, font size on the fly
- **Layout Control**: Switch between tall, fat, stack, grid, splits layouts
- **Markers**: Highlight text patterns in terminal output
- **Process Control**: Send signals (SIGINT, SIGTERM, etc.) to processes

## Requirements

- [Kitty terminal emulator](https://sw.kovidgoyal.net/kitty/)
- Python 3.8+
- Enable remote control in `~/.config/kitty/kitty.conf`:
  ```
  allow_remote_control yes
  ```

## Installation

```bash
make install
```

This installs the skill to `~/.clawdbot/skills/kitten/`

## Usage

### From Claude Code / Codex CLI

Use the `/kitten` command to access the skill.

### Direct CLI Usage

```bash
# List all windows with formatted output
python3 scripts/kitten_control.py ls

# List in watch mode (continuous refresh)
python3 scripts/kitten_control.py ls -w

# Get JSON output
python3 scripts/kitten_control.py ls -j

# Get screen content from a window
python3 scripts/kitten_control.py get-text --window-id 1

# Get last command output (requires shell integration)
python3 scripts/kitten_control.py get-text --window-id 1 --extent last_cmd_output

# Get all scrollback
python3 scripts/kitten_control.py get-text --window-id 1 --extent all

# Send text to a window
python3 scripts/kitten_control.py send-text --window-id 1 "echo hello"

# Send command with Enter key
python3 scripts/kitten_control.py send-text --window-id 1 -e "ls -la"

# Send special keys
python3 scripts/kitten_control.py send-key --window-id 1 ctrl+c
python3 scripts/kitten_control.py send-key --window-id 1 escape
python3 scripts/kitten_control.py send-key --window-id 1 ctrl+d

# Launch a new window
python3 scripts/kitten_control.py launch

# Launch a new tab with title
python3 scripts/kitten_control.py launch --type tab --title "Development"

# Launch with specific working directory
python3 scripts/kitten_control.py launch --type window --cwd /path/to/project

# Launch and run a command
python3 scripts/kitten_control.py launch htop

# Focus a window
python3 scripts/kitten_control.py focus --window-id 1

# Close a window
python3 scripts/kitten_control.py close --window-id 1

# Resize a window
python3 scripts/kitten_control.py resize --window-id 1 --increment 2 --axis horizontal

# Scroll a window
python3 scripts/kitten_control.py scroll page-up --window-id 1
python3 scripts/kitten_control.py scroll home --window-id 1

# Set window/tab title
python3 scripts/kitten_control.py set-title "My Window" --window-id 1
python3 scripts/kitten_control.py set-title "My Tab" --tab-id 1

# Change colors
python3 scripts/kitten_control.py colors --get
python3 scripts/kitten_control.py colors --set background=#000000 foreground=#ffffff

# Set opacity
python3 scripts/kitten_control.py opacity 0.9

# Change font size
python3 scripts/kitten_control.py font-size 14
python3 scripts/kitten_control.py font-size 2 --increment  # Increase by 2

# Change layout
python3 scripts/kitten_control.py layout splits
python3 scripts/kitten_control.py layout tall
python3 scripts/kitten_control.py layout last  # Previous layout

# Create markers to highlight text
python3 scripts/kitten_control.py marker text 1 ERROR
python3 scripts/kitten_control.py marker regex 2 "WARN.*"
python3 scripts/kitten_control.py marker --remove --window-id 1

# Send signals to processes
python3 scripts/kitten_control.py signal SIGINT --window-id 1   # Ctrl+C
python3 scripts/kitten_control.py signal SIGTERM --window-id 1  # Terminate
python3 scripts/kitten_control.py signal SIGKILL --window-id 1  # Force kill

# Reload kitty config
python3 scripts/kitten_control.py reload

# Detach window to new tab
python3 scripts/kitten_control.py detach --window-id 1
```

### Window Matching

Instead of `--window-id`, you can use `--match` with patterns:

```bash
# Match by title
python3 scripts/kitten_control.py get-text --match "title:vim"

# Match by working directory
python3 scripts/kitten_control.py send-text --match "cwd:/home/user/project" -e "git status"

# Match by process name
python3 scripts/kitten_control.py focus --match "cmdline:python"

# Match by PID
python3 scripts/kitten_control.py signal SIGINT --match "pid:12345"

# Match recently used
python3 scripts/kitten_control.py focus --match "recent:1"  # Previous window
```

## Agent Integration

This skill is designed for seamless agent integration:

```python
# Example: Run a command and get output
import subprocess
import json

# Get list of windows
result = subprocess.run(
    ["python3", "kitten_control.py", "ls", "-j"],
    capture_output=True, text=True
)
windows = json.loads(result.stdout)

# Find window running in specific directory
for os_win in windows:
    for tab in os_win.get("tabs", []):
        for win in tab.get("windows", []):
            if "/my/project" in win.get("cwd", ""):
                window_id = win["id"]
                break

# Send command and get output
subprocess.run(["python3", "kitten_control.py", "send-text",
                "--window-id", str(window_id), "-e", "make test"])

# Wait and get result
import time
time.sleep(5)
result = subprocess.run(
    ["python3", "kitten_control.py", "get-text",
     "--window-id", str(window_id), "--extent", "last_cmd_output"],
    capture_output=True, text=True
)
print(result.stdout)
```

## Uninstall

```bash
make uninstall
```

## Resources

- [Kitty Remote Control Documentation](https://sw.kovidgoyal.net/kitty/remote-control/)
- [Kitty Remote Control Protocol](https://sw.kovidgoyal.net/kitty/rc_protocol/)
- [Kitty Terminal](https://sw.kovidgoyal.net/kitty/)

## License

MIT
