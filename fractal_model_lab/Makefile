NAME		= fractal_lab

CC			= cc
CFLAGS		= -Wall -Wextra -Werror
CPPFLAGS	= -Iinclude -MMD -MP
LDLIBS		= -lncursesw

SRC_DIR		= src
OBJ_DIR		= obj

SRC			= main.c app.c log.c layout.c field.c format.c \
			  sat_math.c tree.c tree_role.c cost.c container.c \
			  prune.c prune_build.c prune_cut.c \
			  ui.c ui_text.c ui_bar.c ui_params.c ui_cost.c ui_logs.c ui_wrap.c \
			  fractal_view.c fractal_layout.c fractal_place.c \
			  fractal_nodes.c fractal_edges.c \
			  fractal_span.c fractal_style.c fractal_prune.c \
			  input.c input_term.c input_params.c \
			  command.c command_basic.c command_view.c command_set.c \
			  report.c report_random.c

OBJ			= $(addprefix $(OBJ_DIR)/, $(SRC:.c=.o))
DEP			= $(OBJ:.o=.d)

TESTS		= $(OBJ_DIR)/prune_tests
TEST_OBJ	= $(addprefix $(OBJ_DIR)/, field.o sat_math.o tree.o \
			  prune.o prune_build.o prune_cut.o)

all: $(NAME)

$(NAME): $(OBJ)
	$(CC) $(CFLAGS) $(OBJ) $(LDLIBS) -o $(NAME)

$(OBJ_DIR)/%.o: $(SRC_DIR)/%.c | $(OBJ_DIR)
	$(CC) $(CFLAGS) $(CPPFLAGS) -c $< -o $@

$(OBJ_DIR):
	mkdir -p $(OBJ_DIR)

unit: $(TESTS)
	@for test in $(TESTS); do $$test || exit 1; done

$(OBJ_DIR)/%_tests: tests/%_tests.c $(TEST_OBJ)
	$(CC) $(CFLAGS) -Iinclude $< $(TEST_OBJ) -o $@

clean:
	rm -rf $(OBJ_DIR)

fclean: clean
	rm -f $(NAME)

re: fclean all

-include $(DEP)

.PHONY: all clean fclean re unit
