---
name: kitten
description: Control and interact with Kitty terminal windows - list windows, read output, send commands, and launch new terminals
user_invocable: true
---

# Kitten Terminal Remote Control

Control your Kitty terminal windows directly from the agent. This skill provides comprehensive access to kitty's remote control capabilities.

## Requirements

- Kitty terminal emulator with `allow_remote_control` enabled in kitty.conf
- The `kitten` command available in PATH

## Usage

```bash
# List all windows with their status
python3 {{skill_dir}}/scripts/kitten_control.py ls

# Get screen content from a specific window
python3 {{skill_dir}}/scripts/kitten_control.py get-text --window-id <id>

# Get the last command output from a window
python3 {{skill_dir}}/scripts/kitten_control.py get-text --window-id <id> --extent last_cmd_output

# Send text/commands to a window
python3 {{skill_dir}}/scripts/kitten_control.py send-text --window-id <id> "echo hello"

# Send text with Enter key
python3 {{skill_dir}}/scripts/kitten_control.py send-text --window-id <id> --enter "ls -la"

# Send special keys (Ctrl+C, etc.)
python3 {{skill_dir}}/scripts/kitten_control.py send-key --window-id <id> ctrl+c

# Launch a new window
python3 {{skill_dir}}/scripts/kitten_control.py launch --cwd /path/to/dir

# Launch a new tab
python3 {{skill_dir}}/scripts/kitten_control.py launch --type tab --title "My Tab"

# Focus a window
python3 {{skill_dir}}/scripts/kitten_control.py focus --window-id <id>

# Close a window
python3 {{skill_dir}}/scripts/kitten_control.py close --window-id <id>

# Watch mode - continuously monitor windows
python3 {{skill_dir}}/scripts/kitten_control.py ls -w
```

## Commands

### ls
List all OS windows, tabs, and terminal windows with their IDs, titles, working directories, and process info.

### get-text
Retrieve text content from a window. Options:
- `--window-id`: Target window ID
- `--extent`: What to get (screen, all, last_cmd_output, first_cmd_output_on_screen, selection)
- `--ansi`: Include ANSI formatting codes

### send-text
Send text to a window. Options:
- `--window-id`: Target window ID
- `--enter`: Append Enter key after text
- `--bracketed`: Use bracketed paste mode

### send-key
Send keyboard input to a window. Options:
- `--window-id`: Target window ID
- Supports key names like: ctrl+c, ctrl+d, escape, enter, tab, up, down, left, right

### launch
Launch a new window/tab. Options:
- `--type`: window, tab, os-window, overlay
- `--title`: Window title
- `--cwd`: Working directory
- `--hold`: Keep window open after command exits

### focus
Focus a specific window.
- `--window-id`: Target window ID

### close
Close a specific window.
- `--window-id`: Target window ID
