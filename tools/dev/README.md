# Entorno de desarrollo en Windows

`make up` desde la raíz del repositorio (o `dev up` si no tienes `make`) levanta:

| Pieza | Cómo | Dónde |
|---|---|---|
| MySQL 8 | Docker (`compose.dev.yml`), root/root, base `NisarSar` | `localhost:3306` |
| Servidor Spring Boot | JDK 21 local en segundo plano; si no hay JDK 21, en Docker. **No se arranca si ya hay uno escuchando** (p. ej. desde IntelliJ) | `http://127.0.0.1:8080` |
| Frontend | Go Live de VS Code (se configura y se instala la extensión sola) o live-server en Docker, con recarga al guardar y `/api` redirigido al servidor | `http://127.0.0.1:5500` |

La base de datos usa los mismos valores por defecto que `application.properties`, así que
el servidor lanzado desde IntelliJ conecta sin tocar nada.

## Flujo con IntelliJ

```
make up            # todo arrancado
make server-stop   # libera el puerto 8080 (para el lanzado por make, por Docker o por IntelliJ)
Run en IntelliJ    # tus cambios, misma BD; el frontend sigue apuntando a :8080
make status        # quién ocupa cada puerto: PID, origen (make / IntelliJ / Docker) y comando
```

## Comprobaciones automáticas

- Sin Docker: indica cómo instalarlo. Docker Desktop parado: lo arranca y espera. En modo
  contenedores Windows: lo cambia a Linux.
- JDK: busca un 21 en `JAVA_HOME`, `PATH`, `~\.jdks` (los que descarga IntelliJ) y las rutas
  de instalación habituales. Si no hay ninguno, el servidor corre en Docker. Tiene que ser
  el 21: Lombok 1.18.30 no compila con 22 o superior.
- Maven: `server\mvnw.cmd`, si no `mvn` del PATH, si no el que incluye IntelliJ.
- VS Code sin Live Server: instala `ritwickdey.LiveServer`. Sin VS Code: live-server en Docker.
- Puertos ocupados: distingue este servidor (se reutiliza) de un proceso ajeno (se avisa;
  `FORCE=1` para pararlo) y de un MySQL de Windows en el 3306 (`DB_PORT=3307`).

`make help` lista todos los objetivos y variables; `make doctor` revisa la máquina.

Go Live no se puede arrancar desde la línea de comandos: `make up` abre VS Code y espera a
que pulses **Go Live**. Para que todo arranque sin pulsar nada: `make up FRONT_MODE=docker`.
