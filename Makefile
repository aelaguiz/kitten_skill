# Kitten Terminal Remote Control Skill
# Install/uninstall targets for ~/.clawdbot/skills/

SKILL_NAME := kitten
SKILL_DIR := $(HOME)/.clawdbot/skills/$(SKILL_NAME)

.PHONY: install uninstall clean test

install:
	@echo "Installing $(SKILL_NAME) skill to $(SKILL_DIR)..."
	@mkdir -p $(SKILL_DIR)/scripts
	@cp SKILL.md $(SKILL_DIR)/
	@cp scripts/kitten_control.py $(SKILL_DIR)/scripts/
	@chmod +x $(SKILL_DIR)/scripts/kitten_control.py
	@echo "✓ Installed successfully!"
	@echo ""
	@echo "Usage: /kitten in Claude Code or Codex CLI"
	@echo ""
	@echo "Make sure you have 'allow_remote_control yes' in your kitty.conf"

uninstall:
	@echo "Uninstalling $(SKILL_NAME) skill..."
	@rm -rf $(SKILL_DIR)
	@echo "✓ Uninstalled successfully!"

clean:
	@rm -rf __pycache__ *.pyc

test:
	@echo "Testing kitten remote control..."
	@python3 scripts/kitten_control.py ls -j 2>/dev/null && echo "✓ ls command works" || echo "✗ ls command failed (is Kitty running with remote control enabled?)"
	@echo ""
	@echo "Listing windows:"
	@python3 scripts/kitten_control.py ls 2>/dev/null || echo "(no output - Kitty may not be running)"
