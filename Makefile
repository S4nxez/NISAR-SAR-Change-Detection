# Entorno de desarrollo local de NISAR SAR para Windows.
#
#   make            -> ayuda con todos los objetivos y variables
#   make doctor     -> comprueba Docker, JDK 21, Maven, VS Code + Live Server, IntelliJ y puertos
#   make up         -> MySQL en Docker + servidor (si no está ya arrancado) + frontend con recarga
#   make server-stop-> libera el puerto del servidor para ejecutarlo desde IntelliJ
#
# Toda la lógica está en tools/dev/dev.ps1 (PowerShell 5.1, incluido en Windows): así las
# recetas son de una sola línea y funcionan igual tanto si make usa cmd.exe como el sh de
# Git Bash. Sin make instalado, dev.cmd acepta los mismos objetivos: dev up, dev status...
#
# Variables (make up SERVER_PORT=8081 ...): DB_PORT DB_PASSWORD SERVER_PORT FRONT_PORT
# SERVER_MODE FRONT_MODE SERVER_TIMEOUT FRONT_WAIT OPEN YES FORCE. Descritas en 'make help'.

ifneq ($(OS),Windows_NT)
$(error Este Makefile es para el entorno de desarrollo en Windows. En Linux el despliegue usa podman-compose.yml)
endif

.DEFAULT_GOAL := help

# powershell.exe existe en cualquier Windows; PWSH=pwsh para usar PowerShell 7
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

# Alias
all start: up
stop: down
