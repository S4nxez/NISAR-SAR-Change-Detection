NAME		= fractal_lab

CC			= cc
CFLAGS		= -Wall -Wextra -Werror
CPPFLAGS	= -Iinclude -MMD -MP
LDLIBS		= -lncursesw

SRC_DIR		= src
OBJ_DIR		= obj

SRC			= main.c app.c log.c layout.c field.c format.c \
			  sat_math.c tree.c tree_role.c cost.c container.c \
			  ui.c ui_text.c ui_bar.c ui_params.c ui_cost.c ui_logs.c ui_wrap.c \
			  fractal_view.c fractal_layout.c fractal_place.c \
			  fractal_nodes.c fractal_edges.c \
			  fractal_span.c fractal_style.c \
			  input.c input_term.c input_params.c \
			  command.c command_basic.c command_view.c command_set.c \
			  report.c

OBJ			= $(addprefix $(OBJ_DIR)/, $(SRC:.c=.o))
DEP			= $(OBJ:.o=.d)

all: $(NAME)

$(NAME): $(OBJ)
	$(CC) $(CFLAGS) $(OBJ) $(LDLIBS) -o $(NAME)

$(OBJ_DIR)/%.o: $(SRC_DIR)/%.c | $(OBJ_DIR)
	$(CC) $(CFLAGS) $(CPPFLAGS) -c $< -o $@

$(OBJ_DIR):
	mkdir -p $(OBJ_DIR)

clean:
	rm -rf $(OBJ_DIR)

fclean: clean
	rm -f $(NAME)

re: fclean all

-include $(DEP)

.PHONY: all clean fclean re
