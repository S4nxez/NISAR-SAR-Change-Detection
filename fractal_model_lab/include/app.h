/* ************************************************************************** */
/*                                                                            */
/*                                                      :::      ::::::::   */
/*   app.h                                              :+:      :+:    :+:   */
/*                                                  +:+ +:+         +:+     */
/*   By: sanxez <desanchezmunoz02@gmail.com>        +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2026/10/25 12:00:00 by sanxez            #+#    #+#             */
/*   Updated: 2026/10/29 02:00:00 by sanxez           ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#ifndef APP_H
# define APP_H

# include <ncurses.h>
# include "field.h"

# define PANEL_COUNT 4
# define PANEL_FRACTAL 0
# define PANEL_PARAMS 1
# define PANEL_COST 2
# define PANEL_TERM 3
# define NO_ZOOM -1
# define LOG_LINES 256
# define LOG_LEN 160
# define CMD_LEN 128
# define MIN_WIDTH 60
# define MIN_HEIGHT 16

typedef struct s_app
{
	int		values[FIELD_COUNT];
	WINDOW	*panels[PANEL_COUNT];
	WINDOW	*status;
	int		too_small;
	int		focus;
	int		prev_focus;
	int		zoom;
	int		selected;
	int		running;
	int		fractal_top;
	int		log_scroll;
	int		log_count;
	int		cmd_len;
	char	cmd[CMD_LEN];
	char	logs[LOG_LINES][LOG_LEN];
}	t_app;

void		app_init(t_app *app);
void		app_run(t_app *app);
t_params	app_params(t_app *app);
t_tree		app_tree(t_app *app);
void		app_log(t_app *app, const char *message);
void		app_logf(t_app *app, const char *format, ...);
void		app_help(t_app *app);
void		app_clear_logs(t_app *app);
void		app_focus(t_app *app, int panel);
void		layout_build(t_app *app);
void		layout_destroy(t_app *app);
void		layout_rebuild(t_app *app);
void		handle_input(t_app *app, int key);
void		term_key(t_app *app, int key);
void		params_key(t_app *app, int key);
int			field_change(t_app *app, int id, int value);
void		command_execute(t_app *app, char *line);
void		report_generate(t_app *app);
void		report_levels(t_app *app);
void		report_profile(t_app *app);
void		report_request(t_app *app);
void		report_request_field(t_app *app, int id);

#endif
