#!/usr/bin/env python3
"""
Kitten Terminal Remote Control - Control Kitty terminal windows from scripts/agents.

Provides comprehensive access to kitty's remote control capabilities including:
- Listing windows/tabs with process info
- Reading terminal output (screen, scrollback, last command output)
- Sending text and keyboard input
- Launching new windows/tabs
- Window management (focus, close, resize, scroll)
- Appearance control (colors, opacity, fonts)
- Configuration management
"""

import argparse
import json
import subprocess
import sys
import shutil
import time
from datetime import datetime
from typing import Optional, List, Dict, Any


def run_kitten(args: List[str], capture: bool = True) -> tuple[int, str, str]:
    """Run a kitten @ command and return (returncode, stdout, stderr)."""
    cmd = ["kitten", "@"] + args
    try:
        result = subprocess.run(
            cmd,
            capture_output=capture,
            text=True,
            timeout=30
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return 1, "", "Command timed out"
    except FileNotFoundError:
        return 1, "", "kitten command not found. Is Kitty installed?"


def format_size(size_bytes: int) -> str:
    """Format bytes to human readable size."""
    for unit in ['B', 'K', 'M', 'G']:
        if size_bytes < 1024:
            return f"{size_bytes:>4}{unit}"
        size_bytes //= 1024
    return f"{size_bytes:>4}T"


def truncate(text: str, max_len: int = 60) -> str:
    """Truncate text with ellipsis."""
    if not text:
        return ""
    text = text.replace('\n', ' ').replace('\r', '').strip()
    if len(text) > max_len:
        return text[:max_len-3] + "..."
    return text


class KittenController:
    """Controller for kitty terminal remote operations."""

    def __init__(self, to: Optional[str] = None):
        self.to = to
        self.base_args = ["--to", to] if to else []

    def _run(self, args: List[str], capture: bool = True) -> tuple[int, str, str]:
        """Run kitten command with base args."""
        return run_kitten(self.base_args + args, capture)

    # ==================== LISTING ====================

    def ls(self, match: Optional[str] = None, match_tab: Optional[str] = None) -> Dict:
        """List all windows/tabs as JSON structure."""
        args = ["ls"]
        if match:
            args.extend(["--match", match])
        if match_tab:
            args.extend(["--match-tab", match_tab])

        rc, stdout, stderr = self._run(args)
        if rc != 0:
            return {"error": stderr or "Failed to list windows"}

        try:
            return json.loads(stdout)
        except json.JSONDecodeError:
            return {"error": "Invalid JSON response", "raw": stdout}

    def ls_formatted(self, watch: bool = False, interval: int = 5) -> str:
        """List windows in a human-readable format."""
        while True:
            data = self.ls()
            if "error" in data:
                return f"Error: {data['error']}"

            lines = []
            now = datetime.now()
            header = f"╔{'═'*76}╗"
            title = f"║ KITTY TERMINAL MONITOR - {now.strftime('%Y-%m-%d %H:%M:%S')}"
            title += " " * (77 - len(title)) + "║"
            footer = f"╚{'═'*76}╝"

            lines.append(header)
            lines.append(title)
            lines.append(footer)
            lines.append("")

            for os_win in data:
                os_id = os_win.get("id", "?")
                is_focused = os_win.get("is_focused", False)
                os_state = "🟢" if is_focused else "⚪"

                lines.append(f"┌── OS Window {os_id} {os_state}")

                for tab in os_win.get("tabs", []):
                    tab_id = tab.get("id", "?")
                    tab_title = truncate(tab.get("title", ""), 30)
                    is_active = tab.get("is_active", False)
                    tab_state = "●" if is_active else "○"
                    layout = tab.get("layout", "unknown")

                    lines.append(f"│  ├── Tab {tab_id} {tab_state} [{layout}] {tab_title}")

                    for win in tab.get("windows", []):
                        win_id = win.get("id", "?")
                        win_title = truncate(win.get("title", ""), 25)
                        cwd = win.get("cwd", "")
                        if cwd:
                            cwd = cwd.replace("/Users/" + cwd.split("/")[2] if cwd.startswith("/Users/") else "", "~") if "/Users/" in cwd else cwd
                            cwd = truncate(cwd, 20)

                        pid = win.get("pid", "?")
                        is_focused = win.get("is_focused", False)
                        is_active = win.get("is_active", False)
                        is_self = win.get("is_self", False)

                        # Determine status
                        if is_self:
                            status = "🔵 SELF"
                        elif is_focused:
                            status = "🟢 FOCUS"
                        elif is_active:
                            status = "🟡 ACTIVE"
                        else:
                            status = "⚪ IDLE"

                        # Get foreground process info
                        fg_procs = win.get("foreground_processes", [])
                        fg_cmd = ""
                        if fg_procs:
                            cmdline = fg_procs[0].get("cmdline", [])
                            if cmdline:
                                fg_cmd = truncate(" ".join(cmdline), 25)

                        lines.append(f"│  │   └── Window {win_id} │ {status:12} │ pid:{pid}")
                        if win_title:
                            lines.append(f"│  │       Title: {win_title}")
                        if cwd:
                            lines.append(f"│  │       CWD: {cwd}")
                        if fg_cmd:
                            lines.append(f"│  │       Cmd: {fg_cmd}")

                lines.append("│")

            lines.append("└" + "─" * 76)

            output = "\n".join(lines)

            if not watch:
                return output

            # Clear screen and print
            print("\033[2J\033[H", end="")
            print(output)
            time.sleep(interval)

    # ==================== TEXT OPERATIONS ====================

    def get_text(self, match: Optional[str] = None, extent: str = "screen",
                 ansi: bool = False, window_id: Optional[int] = None) -> str:
        """Get text from a window."""
        args = ["get-text"]

        if window_id:
            args.extend(["--match", f"id:{window_id}"])
        elif match:
            args.extend(["--match", match])

        args.extend(["--extent", extent])

        if ansi:
            args.append("--ansi")

        rc, stdout, stderr = self._run(args)
        if rc != 0:
            return f"Error: {stderr}"
        return stdout

    def send_text(self, text: str, match: Optional[str] = None,
                  window_id: Optional[int] = None, enter: bool = False,
                  bracketed: bool = False, all_windows: bool = False) -> bool:
        """Send text to a window."""
        args = ["send-text"]

        if window_id:
            args.extend(["--match", f"id:{window_id}"])
        elif match:
            args.extend(["--match", match])

        if all_windows:
            args.append("--all")

        if bracketed:
            args.extend(["--bracketed-paste", "enable"])

        # Add Enter key if requested
        if enter:
            text = text + "\\r"

        args.append(text)

        rc, stdout, stderr = self._run(args)
        return rc == 0

    def send_key(self, keys: List[str], match: Optional[str] = None,
                 window_id: Optional[int] = None) -> bool:
        """Send keyboard keys to a window."""
        args = ["send-key"]

        if window_id:
            args.extend(["--match", f"id:{window_id}"])
        elif match:
            args.extend(["--match", match])

        args.extend(keys)

        rc, stdout, stderr = self._run(args)
        return rc == 0

    # ==================== WINDOW MANAGEMENT ====================

    def launch(self, cmd: Optional[List[str]] = None, window_type: str = "window",
               title: Optional[str] = None, cwd: Optional[str] = None,
               hold: bool = False, env: Optional[Dict[str, str]] = None) -> Optional[int]:
        """Launch a new window/tab and return window ID."""
        args = ["launch", "--type", window_type]

        if title:
            args.extend(["--title", title])
        if cwd:
            args.extend(["--cwd", cwd])
        if hold:
            args.append("--hold")
        if env:
            for k, v in env.items():
                args.extend(["--env", f"{k}={v}"])

        if cmd:
            args.extend(cmd)

        rc, stdout, stderr = self._run(args)
        if rc != 0:
            return None

        try:
            return int(stdout.strip())
        except ValueError:
            return None

    def focus_window(self, window_id: Optional[int] = None, match: Optional[str] = None) -> bool:
        """Focus a specific window."""
        args = ["focus-window"]

        if window_id:
            args.extend(["--match", f"id:{window_id}"])
        elif match:
            args.extend(["--match", match])

        rc, stdout, stderr = self._run(args)
        return rc == 0

    def focus_tab(self, tab_id: Optional[int] = None, match: Optional[str] = None) -> bool:
        """Focus a specific tab."""
        args = ["focus-tab"]

        if tab_id:
            args.extend(["--match", f"id:{tab_id}"])
        elif match:
            args.extend(["--match", match])

        rc, stdout, stderr = self._run(args)
        return rc == 0

    def close_window(self, window_id: Optional[int] = None, match: Optional[str] = None,
                     ignore_no_match: bool = False) -> bool:
        """Close a window."""
        args = ["close-window"]

        if window_id:
            args.extend(["--match", f"id:{window_id}"])
        elif match:
            args.extend(["--match", match])

        if ignore_no_match:
            args.append("--ignore-no-match")

        rc, stdout, stderr = self._run(args)
        return rc == 0

    def close_tab(self, tab_id: Optional[int] = None, match: Optional[str] = None) -> bool:
        """Close a tab."""
        args = ["close-tab"]

        if tab_id:
            args.extend(["--match", f"id:{tab_id}"])
        elif match:
            args.extend(["--match", match])

        rc, stdout, stderr = self._run(args)
        return rc == 0

    def resize_window(self, increment: int = 1, axis: str = "horizontal",
                      window_id: Optional[int] = None, match: Optional[str] = None) -> bool:
        """Resize a window."""
        args = ["resize-window", "--increment", str(increment), "--axis", axis]

        if window_id:
            args.extend(["--match", f"id:{window_id}"])
        elif match:
            args.extend(["--match", match])

        rc, stdout, stderr = self._run(args)
        return rc == 0

    def scroll_window(self, amount: str = "1", window_id: Optional[int] = None,
                      match: Optional[str] = None) -> bool:
        """Scroll a window. Amount can be: page-up, page-down, line-up, line-down, home, end, or a number."""
        args = ["scroll-window", amount]

        if window_id:
            args.extend(["--match", f"id:{window_id}"])
        elif match:
            args.extend(["--match", match])

        rc, stdout, stderr = self._run(args)
        return rc == 0

    # ==================== TITLES & APPEARANCE ====================

    def set_window_title(self, title: str, window_id: Optional[int] = None,
                         match: Optional[str] = None) -> bool:
        """Set window title."""
        args = ["set-window-title", title]

        if window_id:
            args.extend(["--match", f"id:{window_id}"])
        elif match:
            args.extend(["--match", match])

        rc, stdout, stderr = self._run(args)
        return rc == 0

    def set_tab_title(self, title: str, tab_id: Optional[int] = None,
                      match: Optional[str] = None) -> bool:
        """Set tab title."""
        args = ["set-tab-title", title]

        if tab_id:
            args.extend(["--match", f"id:{tab_id}"])
        elif match:
            args.extend(["--match", match])

        rc, stdout, stderr = self._run(args)
        return rc == 0

    def set_colors(self, colors: Dict[str, str] = None, config_file: Optional[str] = None,
                   window_id: Optional[int] = None, match: Optional[str] = None,
                   all_windows: bool = False) -> bool:
        """Set terminal colors."""
        args = ["set-colors"]

        if window_id:
            args.extend(["--match", f"id:{window_id}"])
        elif match:
            args.extend(["--match", match])

        if all_windows:
            args.append("--all")

        if config_file:
            args.append(config_file)
        elif colors:
            for name, value in colors.items():
                args.append(f"{name}={value}")

        rc, stdout, stderr = self._run(args)
        return rc == 0

    def get_colors(self, window_id: Optional[int] = None, match: Optional[str] = None) -> Dict[str, str]:
        """Get current colors."""
        args = ["get-colors"]

        if window_id:
            args.extend(["--match", f"id:{window_id}"])
        elif match:
            args.extend(["--match", match])

        rc, stdout, stderr = self._run(args)
        if rc != 0:
            return {"error": stderr}

        colors = {}
        for line in stdout.strip().split('\n'):
            if line and not line.startswith('#'):
                parts = line.split(None, 1)
                if len(parts) == 2:
                    colors[parts[0]] = parts[1]
        return colors

    def set_background_opacity(self, opacity: float, all_windows: bool = False) -> bool:
        """Set background opacity (0.0 to 1.0)."""
        args = ["set-background-opacity", str(opacity)]
        if all_windows:
            args.append("--all")

        rc, stdout, stderr = self._run(args)
        return rc == 0

    def set_font_size(self, size: float, all_windows: bool = False,
                      increment: bool = False) -> bool:
        """Set font size. Use increment=True for relative change."""
        args = ["set-font-size"]
        if all_windows:
            args.append("--all")

        size_str = str(size)
        if increment and size > 0:
            size_str = f"+{size}"
        args.append(size_str)

        rc, stdout, stderr = self._run(args)
        return rc == 0

    # ==================== LAYOUT ====================

    def goto_layout(self, layout: str, window_id: Optional[int] = None,
                    match: Optional[str] = None) -> bool:
        """Change window layout. Layouts: tall, fat, stack, grid, splits, horizontal, vertical."""
        args = ["goto-layout", layout]

        if window_id:
            args.extend(["--match", f"id:{window_id}"])
        elif match:
            args.extend(["--match", match])

        rc, stdout, stderr = self._run(args)
        return rc == 0

    def last_used_layout(self) -> bool:
        """Switch to last used layout."""
        rc, stdout, stderr = self._run(["last-used-layout"])
        return rc == 0

    # ==================== MARKERS ====================

    def create_marker(self, marker_spec: str, window_id: Optional[int] = None,
                      match: Optional[str] = None) -> bool:
        """Create a text marker. marker_spec format: 'text 1 pattern' or 'regex 1 pattern'."""
        args = ["create-marker"]

        if window_id:
            args.extend(["--match", f"id:{window_id}"])
        elif match:
            args.extend(["--match", match])

        args.extend(marker_spec.split())

        rc, stdout, stderr = self._run(args)
        return rc == 0

    def remove_marker(self, window_id: Optional[int] = None, match: Optional[str] = None) -> bool:
        """Remove markers from a window."""
        args = ["remove-marker"]

        if window_id:
            args.extend(["--match", f"id:{window_id}"])
        elif match:
            args.extend(["--match", match])

        rc, stdout, stderr = self._run(args)
        return rc == 0

    # ==================== CONFIG & MISC ====================

    def load_config(self, config_file: Optional[str] = None) -> bool:
        """Reload kitty configuration."""
        args = ["load-config"]
        if config_file:
            args.append(config_file)

        rc, stdout, stderr = self._run(args)
        return rc == 0

    def signal_child(self, signal: str = "SIGINT", window_id: Optional[int] = None,
                     match: Optional[str] = None) -> bool:
        """Send signal to child process (e.g., SIGINT, SIGTERM, SIGKILL)."""
        args = ["signal-child", signal]

        if window_id:
            args.extend(["--match", f"id:{window_id}"])
        elif match:
            args.extend(["--match", match])

        rc, stdout, stderr = self._run(args)
        return rc == 0

    def run(self, cmd: List[str]) -> tuple[int, str]:
        """Run a command in kitty's context and return exit code + output."""
        args = ["run"] + cmd
        rc, stdout, stderr = self._run(args)
        return rc, stdout + stderr

    def action(self, action_name: str, *action_args) -> bool:
        """Execute a kitty mappable action."""
        args = ["action", action_name] + list(action_args)
        rc, stdout, stderr = self._run(args)
        return rc == 0

    # ==================== SUMMARY ====================

    def summary(self, lines: int = 20, extent: str = "screen",
                exclude_self: bool = True) -> str:
        """Get a markdown-formatted summary of all terminal windows with their recent output.

        Args:
            lines: Number of lines to show from each window
            extent: What text to get (screen, all, last_cmd_output, etc.)
            exclude_self: Skip the window running this command

        Returns:
            Markdown formatted string with all window contents
        """
        data = self.ls()
        if "error" in data:
            return f"Error: {data['error']}"

        output_parts = []
        output_parts.append("# Kitty Terminal Summary\n")
        output_parts.append(f"*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n")
        output_parts.append(f"*Showing last {lines} lines from each window (extent: {extent})*\n")
        output_parts.append("---\n")

        window_count = 0

        for os_win in data:
            os_id = os_win.get("id", "?")
            is_os_focused = os_win.get("is_focused", False)

            for tab in os_win.get("tabs", []):
                tab_id = tab.get("id", "?")
                tab_title = tab.get("title", "Untitled")
                is_tab_active = tab.get("is_active", False)
                layout = tab.get("layout", "unknown")

                for win in tab.get("windows", []):
                    win_id = win.get("id", "?")
                    is_self = win.get("is_self", False)

                    # Skip self if requested
                    if exclude_self and is_self:
                        continue

                    window_count += 1

                    win_title = win.get("title", "Untitled")
                    cwd = win.get("cwd", "unknown")
                    pid = win.get("pid", "?")
                    is_focused = win.get("is_focused", False)
                    is_active = win.get("is_active", False)

                    # Get foreground process info
                    fg_procs = win.get("foreground_processes", [])
                    fg_cmd = "shell"
                    fg_cwd = cwd
                    if fg_procs:
                        cmdline = fg_procs[0].get("cmdline", [])
                        if cmdline:
                            fg_cmd = " ".join(cmdline)
                        fg_cwd = fg_procs[0].get("cwd", cwd)

                    # Determine status emoji
                    if is_focused:
                        status = "🟢 FOCUSED"
                    elif is_active:
                        status = "🟡 ACTIVE"
                    else:
                        status = "⚪ IDLE"

                    # Build header
                    output_parts.append(f"## Window {win_id} | {status}\n")
                    output_parts.append(f"| Property | Value |")
                    output_parts.append(f"|----------|-------|")
                    output_parts.append(f"| **Window ID** | `{win_id}` |")
                    output_parts.append(f"| **Tab** | {tab_id} ({tab_title}) |")
                    output_parts.append(f"| **OS Window** | {os_id} |")
                    output_parts.append(f"| **Title** | {win_title} |")
                    output_parts.append(f"| **CWD** | `{fg_cwd}` |")
                    output_parts.append(f"| **PID** | {pid} |")
                    output_parts.append(f"| **Command** | `{truncate(fg_cmd, 50)}` |")
                    output_parts.append("")

                    # Quick reference for commands
                    output_parts.append(f"**Quick commands:**")
                    output_parts.append(f"- Send text: `send-text -w {win_id} -e \"your command\"`")
                    output_parts.append(f"- Send Ctrl+C: `send-key -w {win_id} ctrl+c`")
                    output_parts.append(f"- Get more output: `get-text -w {win_id} -e all`")
                    output_parts.append(f"- Focus: `focus -w {win_id}`")
                    output_parts.append("")

                    # Get terminal content
                    text = self.get_text(window_id=win_id, extent=extent)

                    if text and not text.startswith("Error:"):
                        # Get last N lines
                        text_lines = text.rstrip('\n').split('\n')
                        if len(text_lines) > lines:
                            text_lines = text_lines[-lines:]
                            output_parts.append(f"*(...truncated, showing last {lines} lines)*\n")

                        output_parts.append("```")
                        output_parts.append('\n'.join(text_lines))
                        output_parts.append("```")
                    else:
                        output_parts.append("*No output available*")

                    output_parts.append("\n---\n")

        if window_count == 0:
            output_parts.append("*No windows found (or all windows excluded)*")
        else:
            output_parts.append(f"\n**Total: {window_count} windows**")

        return '\n'.join(output_parts)

    # ==================== DETACH/MOVE ====================

    def detach_window(self, window_id: Optional[int] = None, match: Optional[str] = None,
                      target_tab: Optional[str] = None) -> bool:
        """Detach window to a new tab or specified target."""
        args = ["detach-window"]

        if window_id:
            args.extend(["--match", f"id:{window_id}"])
        elif match:
            args.extend(["--match", match])

        if target_tab:
            args.extend(["--target-tab", target_tab])

        rc, stdout, stderr = self._run(args)
        return rc == 0

    def detach_tab(self, tab_id: Optional[int] = None, match: Optional[str] = None,
                   target: Optional[str] = None) -> bool:
        """Detach tab to a new OS window."""
        args = ["detach-tab"]

        if tab_id:
            args.extend(["--match", f"id:{tab_id}"])
        elif match:
            args.extend(["--match", match])

        if target:
            args.extend(["--target-tab", target])

        rc, stdout, stderr = self._run(args)
        return rc == 0


def main():
    parser = argparse.ArgumentParser(
        description="Control Kitty terminal windows remotely",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s ls                                    # List all windows
  %(prog)s ls -w                                 # Watch mode (continuous)
  %(prog)s summary                               # Markdown summary of all windows (20 lines each)
  %(prog)s summary -n 50                         # Summary with 50 lines per window
  %(prog)s summary -e last_cmd_output            # Summary showing last command output
  %(prog)s get-text --window-id 1                # Get screen content
  %(prog)s get-text --extent last_cmd_output     # Get last command output
  %(prog)s send-text --window-id 1 "echo hi"     # Send text
  %(prog)s send-text --window-id 1 -e "ls -la"   # Send command with Enter
  %(prog)s send-key --window-id 1 ctrl+c         # Send Ctrl+C
  %(prog)s launch --type tab --title "Dev"       # Launch new tab
  %(prog)s focus --window-id 1                   # Focus window
  %(prog)s close --window-id 1                   # Close window
  %(prog)s signal --window-id 1 SIGINT           # Send interrupt signal
"""
    )

    parser.add_argument("--to", help="Kitty socket address")
    parser.add_argument("--json", "-j", action="store_true", help="Output in JSON format")

    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # ls command
    ls_parser = subparsers.add_parser("ls", help="List windows/tabs")
    ls_parser.add_argument("-w", "--watch", action="store_true", help="Watch mode")
    ls_parser.add_argument("-n", "--interval", type=int, default=5, help="Watch interval (seconds)")
    ls_parser.add_argument("-m", "--match", help="Window match pattern")
    ls_parser.add_argument("-t", "--match-tab", help="Tab match pattern")

    # get-text command
    get_parser = subparsers.add_parser("get-text", help="Get text from window")
    get_parser.add_argument("--window-id", "-w", type=int, help="Window ID")
    get_parser.add_argument("-m", "--match", help="Window match pattern")
    get_parser.add_argument("--extent", "-e", default="screen",
                           choices=["screen", "all", "selection", "first_cmd_output_on_screen",
                                   "last_cmd_output", "last_non_empty_output", "last_visited_cmd_output"],
                           help="What text to get")
    get_parser.add_argument("--ansi", "-a", action="store_true", help="Include ANSI codes")

    # send-text command
    send_parser = subparsers.add_parser("send-text", help="Send text to window")
    send_parser.add_argument("text", nargs="?", help="Text to send")
    send_parser.add_argument("--window-id", "-w", type=int, help="Window ID")
    send_parser.add_argument("-m", "--match", help="Window match pattern")
    send_parser.add_argument("-e", "--enter", action="store_true", help="Press Enter after text")
    send_parser.add_argument("-b", "--bracketed", action="store_true", help="Use bracketed paste")
    send_parser.add_argument("-a", "--all", action="store_true", help="Send to all windows")
    send_parser.add_argument("--stdin", action="store_true", help="Read text from stdin")

    # send-key command
    key_parser = subparsers.add_parser("send-key", help="Send keyboard keys")
    key_parser.add_argument("keys", nargs="+", help="Keys to send (e.g., ctrl+c, escape, enter)")
    key_parser.add_argument("--window-id", "-w", type=int, help="Window ID")
    key_parser.add_argument("-m", "--match", help="Window match pattern")

    # launch command
    launch_parser = subparsers.add_parser("launch", help="Launch new window/tab")
    launch_parser.add_argument("cmd", nargs="*", help="Command to run")
    launch_parser.add_argument("--type", "-t", default="window",
                              choices=["window", "tab", "os-window", "overlay", "overlay-main", "background"],
                              help="Window type")
    launch_parser.add_argument("--title", help="Window title")
    launch_parser.add_argument("--cwd", help="Working directory")
    launch_parser.add_argument("--hold", action="store_true", help="Keep window after command exits")
    launch_parser.add_argument("--env", action="append", help="Environment variable (KEY=VALUE)")

    # focus command
    focus_parser = subparsers.add_parser("focus", help="Focus a window")
    focus_parser.add_argument("--window-id", "-w", type=int, help="Window ID")
    focus_parser.add_argument("--tab-id", "-t", type=int, help="Tab ID (use focus-tab)")
    focus_parser.add_argument("-m", "--match", help="Match pattern")

    # close command
    close_parser = subparsers.add_parser("close", help="Close a window/tab")
    close_parser.add_argument("--window-id", "-w", type=int, help="Window ID")
    close_parser.add_argument("--tab-id", "-t", type=int, help="Tab ID")
    close_parser.add_argument("-m", "--match", help="Match pattern")
    close_parser.add_argument("--ignore-no-match", action="store_true")

    # resize command
    resize_parser = subparsers.add_parser("resize", help="Resize a window")
    resize_parser.add_argument("--window-id", "-w", type=int, help="Window ID")
    resize_parser.add_argument("-m", "--match", help="Match pattern")
    resize_parser.add_argument("--increment", "-i", type=int, default=1, help="Resize increment")
    resize_parser.add_argument("--axis", "-a", default="horizontal",
                              choices=["horizontal", "vertical", "reset"], help="Resize axis")

    # scroll command
    scroll_parser = subparsers.add_parser("scroll", help="Scroll a window")
    scroll_parser.add_argument("amount", nargs="?", default="page-down",
                              help="Scroll amount (page-up, page-down, home, end, or number)")
    scroll_parser.add_argument("--window-id", "-w", type=int, help="Window ID")
    scroll_parser.add_argument("-m", "--match", help="Match pattern")

    # set-title command
    title_parser = subparsers.add_parser("set-title", help="Set window/tab title")
    title_parser.add_argument("title", help="New title")
    title_parser.add_argument("--window-id", "-w", type=int, help="Window ID")
    title_parser.add_argument("--tab-id", "-t", type=int, help="Tab ID")
    title_parser.add_argument("-m", "--match", help="Match pattern")

    # colors command
    colors_parser = subparsers.add_parser("colors", help="Get or set colors")
    colors_parser.add_argument("--get", "-g", action="store_true", help="Get current colors")
    colors_parser.add_argument("--set", "-s", nargs="+", help="Set colors (name=value)")
    colors_parser.add_argument("--file", "-f", help="Load colors from file")
    colors_parser.add_argument("--window-id", "-w", type=int, help="Window ID")
    colors_parser.add_argument("-m", "--match", help="Match pattern")
    colors_parser.add_argument("-a", "--all", action="store_true", help="Apply to all windows")

    # opacity command
    opacity_parser = subparsers.add_parser("opacity", help="Set background opacity")
    opacity_parser.add_argument("value", type=float, help="Opacity (0.0-1.0)")
    opacity_parser.add_argument("-a", "--all", action="store_true", help="Apply to all windows")

    # font-size command
    font_parser = subparsers.add_parser("font-size", help="Set font size")
    font_parser.add_argument("size", type=float, help="Font size (or increment if prefixed with +/-)")
    font_parser.add_argument("-a", "--all", action="store_true", help="Apply to all windows")
    font_parser.add_argument("--increment", "-i", action="store_true", help="Treat as increment")

    # layout command
    layout_parser = subparsers.add_parser("layout", help="Change window layout")
    layout_parser.add_argument("layout", nargs="?",
                              choices=["tall", "fat", "stack", "grid", "splits", "horizontal", "vertical", "last"],
                              help="Layout name (or 'last' for previous)")
    layout_parser.add_argument("--window-id", "-w", type=int, help="Window ID")
    layout_parser.add_argument("-m", "--match", help="Match pattern")

    # marker command
    marker_parser = subparsers.add_parser("marker", help="Create or remove text markers")
    marker_parser.add_argument("spec", nargs="*", help="Marker spec: type num pattern (e.g., 'text 1 ERROR')")
    marker_parser.add_argument("--remove", "-r", action="store_true", help="Remove markers")
    marker_parser.add_argument("--window-id", "-w", type=int, help="Window ID")
    marker_parser.add_argument("-m", "--match", help="Match pattern")

    # signal command
    signal_parser = subparsers.add_parser("signal", help="Send signal to child process")
    signal_parser.add_argument("signal", nargs="?", default="SIGINT",
                              help="Signal name (SIGINT, SIGTERM, SIGKILL, etc.)")
    signal_parser.add_argument("--window-id", "-w", type=int, help="Window ID")
    signal_parser.add_argument("-m", "--match", help="Match pattern")

    # reload command
    reload_parser = subparsers.add_parser("reload", help="Reload kitty config")
    reload_parser.add_argument("config", nargs="?", help="Config file path")

    # action command
    action_parser = subparsers.add_parser("action", help="Execute a kitty action")
    action_parser.add_argument("action_name", help="Action name")
    action_parser.add_argument("args", nargs="*", help="Action arguments")

    # detach command
    detach_parser = subparsers.add_parser("detach", help="Detach window or tab")
    detach_parser.add_argument("--window-id", "-w", type=int, help="Window ID")
    detach_parser.add_argument("--tab-id", "-t", type=int, help="Tab ID")
    detach_parser.add_argument("-m", "--match", help="Match pattern")
    detach_parser.add_argument("--target", help="Target tab/OS window")

    # summary command
    summary_parser = subparsers.add_parser("summary", help="Get markdown summary of all windows with output")
    summary_parser.add_argument("-n", "--lines", type=int, default=20,
                               help="Number of lines to show from each window (default: 20)")
    summary_parser.add_argument("-e", "--extent", default="screen",
                               choices=["screen", "all", "last_cmd_output", "last_non_empty_output"],
                               help="What text to get from each window")
    summary_parser.add_argument("--include-self", action="store_true",
                               help="Include the window running this command")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    controller = KittenController(to=args.to)

    # Execute command
    if args.command == "ls":
        if args.json or (args.match or args.match_tab):
            result = controller.ls(match=args.match, match_tab=args.match_tab)
            print(json.dumps(result, indent=2))
        else:
            output = controller.ls_formatted(watch=args.watch, interval=args.interval)
            if output:
                print(output)

    elif args.command == "get-text":
        text = controller.get_text(
            window_id=args.window_id,
            match=args.match,
            extent=args.extent,
            ansi=args.ansi
        )
        print(text)

    elif args.command == "send-text":
        text = args.text
        if args.stdin or not text:
            text = sys.stdin.read()

        success = controller.send_text(
            text=text,
            window_id=args.window_id,
            match=args.match,
            enter=args.enter,
            bracketed=args.bracketed,
            all_windows=args.all
        )
        if not success:
            print("Failed to send text", file=sys.stderr)
            sys.exit(1)
        print("Text sent successfully")

    elif args.command == "send-key":
        success = controller.send_key(
            keys=args.keys,
            window_id=args.window_id,
            match=args.match
        )
        if not success:
            print("Failed to send keys", file=sys.stderr)
            sys.exit(1)
        print("Keys sent successfully")

    elif args.command == "launch":
        env = {}
        if args.env:
            for e in args.env:
                k, v = e.split("=", 1)
                env[k] = v

        window_id = controller.launch(
            cmd=args.cmd if args.cmd else None,
            window_type=args.type,
            title=args.title,
            cwd=args.cwd,
            hold=args.hold,
            env=env if env else None
        )
        if window_id:
            print(f"Launched window ID: {window_id}")
        else:
            print("Failed to launch window", file=sys.stderr)
            sys.exit(1)

    elif args.command == "focus":
        if args.tab_id:
            success = controller.focus_tab(tab_id=args.tab_id, match=args.match)
        else:
            success = controller.focus_window(window_id=args.window_id, match=args.match)

        if not success:
            print("Failed to focus", file=sys.stderr)
            sys.exit(1)
        print("Focused successfully")

    elif args.command == "close":
        if args.tab_id:
            success = controller.close_tab(tab_id=args.tab_id, match=args.match)
        else:
            success = controller.close_window(
                window_id=args.window_id,
                match=args.match,
                ignore_no_match=args.ignore_no_match
            )

        if not success:
            print("Failed to close", file=sys.stderr)
            sys.exit(1)
        print("Closed successfully")

    elif args.command == "resize":
        success = controller.resize_window(
            window_id=args.window_id,
            match=args.match,
            increment=args.increment,
            axis=args.axis
        )
        if not success:
            print("Failed to resize", file=sys.stderr)
            sys.exit(1)
        print("Resized successfully")

    elif args.command == "scroll":
        success = controller.scroll_window(
            amount=args.amount,
            window_id=args.window_id,
            match=args.match
        )
        if not success:
            print("Failed to scroll", file=sys.stderr)
            sys.exit(1)

    elif args.command == "set-title":
        if args.tab_id:
            success = controller.set_tab_title(title=args.title, tab_id=args.tab_id, match=args.match)
        else:
            success = controller.set_window_title(title=args.title, window_id=args.window_id, match=args.match)

        if not success:
            print("Failed to set title", file=sys.stderr)
            sys.exit(1)
        print("Title set successfully")

    elif args.command == "colors":
        if args.get:
            colors = controller.get_colors(window_id=args.window_id, match=args.match)
            if args.json:
                print(json.dumps(colors, indent=2))
            else:
                for name, value in colors.items():
                    print(f"{name}: {value}")
        elif args.file:
            success = controller.set_colors(config_file=args.file, window_id=args.window_id,
                                           match=args.match, all_windows=args.all)
            print("Colors set" if success else "Failed to set colors")
        elif args.set:
            colors = {}
            for c in args.set:
                k, v = c.split("=", 1)
                colors[k] = v
            success = controller.set_colors(colors=colors, window_id=args.window_id,
                                           match=args.match, all_windows=args.all)
            print("Colors set" if success else "Failed to set colors")

    elif args.command == "opacity":
        success = controller.set_background_opacity(opacity=args.value, all_windows=args.all)
        print("Opacity set" if success else "Failed to set opacity")

    elif args.command == "font-size":
        success = controller.set_font_size(size=args.size, all_windows=args.all, increment=args.increment)
        print("Font size set" if success else "Failed to set font size")

    elif args.command == "layout":
        if args.layout == "last":
            success = controller.last_used_layout()
        else:
            success = controller.goto_layout(layout=args.layout, window_id=args.window_id, match=args.match)
        print("Layout changed" if success else "Failed to change layout")

    elif args.command == "marker":
        if args.remove:
            success = controller.remove_marker(window_id=args.window_id, match=args.match)
            print("Markers removed" if success else "Failed to remove markers")
        else:
            spec = " ".join(args.spec)
            success = controller.create_marker(marker_spec=spec, window_id=args.window_id, match=args.match)
            print("Marker created" if success else "Failed to create marker")

    elif args.command == "signal":
        success = controller.signal_child(signal=args.signal, window_id=args.window_id, match=args.match)
        print(f"Signal {args.signal} sent" if success else "Failed to send signal")

    elif args.command == "reload":
        success = controller.load_config(config_file=args.config)
        print("Config reloaded" if success else "Failed to reload config")

    elif args.command == "action":
        success = controller.action(args.action_name, *args.args)
        print("Action executed" if success else "Failed to execute action")

    elif args.command == "detach":
        if args.tab_id:
            success = controller.detach_tab(tab_id=args.tab_id, match=args.match, target=args.target)
        else:
            success = controller.detach_window(window_id=args.window_id, match=args.match, target_tab=args.target)
        print("Detached successfully" if success else "Failed to detach")

    elif args.command == "summary":
        output = controller.summary(
            lines=args.lines,
            extent=args.extent,
            exclude_self=not args.include_self
        )
        print(output)


if __name__ == "__main__":
    main()
