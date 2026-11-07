# fractal_model_lab (C TUI with ncursesw) for Windows: it is built and run on Linux.
# Build context: fractal_model_lab/ (launched by 'make lab-build'). The sources are copied into
# the image, so the repository's obj/ and binary are left untouched.
FROM docker.io/library/gcc:14

RUN apt-get update \
 && apt-get install -y --no-install-recommends libncurses-dev jq \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /lab
COPY . .
RUN make fclean && make

ENV TERM=xterm-256color
CMD ["./fractal_lab"]
