# NISAR SAR local development environment for Windows.
#
#   make            -> help with every target and variable
#   make doctor     -> checks Docker, JDK 21, Maven, VS Code + Live Server, IntelliJ and ports
#   make up         -> MySQL in Docker + server (unless already running) + hot-reloading frontend
#   make server-stop-> frees the server port so it can be run from IntelliJ
#
# All the logic lives in tools/dev/dev.ps1 (PowerShell 5.1, bundled with Windows), so the
# recipes are one-liners and behave the same whether make uses cmd.exe or Git Bash's sh.
# Without make installed, dev.cmd accepts the same targets: dev up, dev status...
#
# Variables (make up SERVER_PORT=8081 ...): DB_PORT DB_PASSWORD SERVER_PORT FRONT_PORT
# SERVER_MODE FRONT_MODE SERVER_TIMEOUT FRONT_WAIT OPEN YES FORCE. Described in 'make help'.

ifneq ($(OS),Windows_NT)
$(error This Makefile is for the Windows development environment. On Linux, deployment uses podman-compose.yml)
endif

.DEFAULT_GOAL := help

# powershell.exe exists on every Windows; PWSH=pwsh to use PowerShell 7
PWSH ?= powershell.exe
DEV  := $(PWSH) -NoLogo -NoProfile -ExecutionPolicy Bypass -File tools/dev/dev.ps1

export DB_PORT DB_PASSWORD SERVER_PORT FRONT_PORT SERVER_MODE FRONT_MODE
export SERVER_TIMEOUT FRONT_WAIT OPEN YES FORCE

TARGETS := help doctor status up down restart open \
           db db-stop db-logs db-shell db-reset \
           server server-stop server-restart server-status server-logs server-build \
           front front-stop front-config \
           lab-build lab-test lab-run \
           clean purge install-make

.PHONY: $(TARGETS) all start stop

$(TARGETS):
	@$(DEV) $@

# Aliases
all start: up
stop: down
