# Windows development environment

`make up` from the repository root (or `dev up` if you don't have `make`) starts:

| Piece | How | Where |
|---|---|---|
| MySQL 8 | Docker (`compose.dev.yml`), root/root, `NisarSar` database | `localhost:3306` |
| Spring Boot server | Local JDK 21 in the background; in Docker if there is no JDK 21. **Not started if one is already listening** (e.g. from IntelliJ) | `http://127.0.0.1:8080` |
| Frontend | VS Code Go Live (configured, extension installed automatically) or live-server in Docker, reloading on save and with `/api` forwarded to the server | `http://127.0.0.1:5500` |

The database uses the same defaults as `application.properties`, so the server launched
from IntelliJ connects without changing anything.

## IntelliJ workflow

```
make up            # everything running
make server-stop   # frees port 8080 (stops the server launched by make, by Docker or by IntelliJ)
Run in IntelliJ    # your changes, same DB; the frontend still points at :8080
make status        # who holds each port: PID, origin (make / IntelliJ / Docker) and command
```

## Automatic checks

- No Docker: explains how to install it. Docker Desktop stopped: starts it and waits. Windows
  containers mode: switches it to Linux.
- JDK: looks for a 21 in `JAVA_HOME`, `PATH`, `~\.jdks` (the ones IntelliJ downloads) and the
  usual install paths. If there is none, the server runs in Docker. It must be 21: Lombok
  1.18.30 does not compile on 22 or later.
- Maven: `server\mvnw.cmd`, otherwise `mvn` on PATH, otherwise the one bundled with IntelliJ.
- VS Code without Live Server: installs `ritwickdey.LiveServer`. No VS Code: live-server in Docker.
- Busy ports: tells this server (reused) apart from an unrelated process (warns;
  `FORCE=1` to stop it) and from a Windows MySQL on 3306 (`DB_PORT=3307`).

`make help` lists every target and variable; `make doctor` checks the machine.

Go Live cannot be started from the command line: `make up` opens VS Code and waits for you
to click **Go Live**. To have everything start without clicking: `make up FRONT_MODE=docker`.
