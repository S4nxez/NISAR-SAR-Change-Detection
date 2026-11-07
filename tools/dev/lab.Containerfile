# fractal_model_lab (TUI en C con ncursesw) para Windows: se compila y ejecuta en Linux.
# Contexto de build: fractal_model_lab/ (lo lanza 'make lab-build'). Los fuentes se copian a
# la imagen, así que no se tocan los obj/ ni el binario del repositorio.
FROM docker.io/library/gcc:14

RUN apt-get update \
 && apt-get install -y --no-install-recommends libncurses-dev jq \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /lab
COPY . .
RUN make fclean && make

ENV TERM=xterm-256color
CMD ["./fractal_lab"]
