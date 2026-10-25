/* ************************************************************************** */
/*                                                                            */
/*                                                      :::      ::::::::   */
/*   ui.c                                               :+:      :+:    :+:   */
/*                                                  +:+ +:+         +:+     */
/*   By: sanxez <desanchezmunoz02@gmail.com>        +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2026/10/25 12:00:00 by sanxez            #+#    #+#             */
/*   Updated: 2026/10/25 12:00:00 by sanxez           ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#include "ui.h"

void	ui_init_colors(void)
{
	if (!has_colors())
		return ;
	start_color();
	use_default_colors();
	init_pair(CP_VOTER_A, COLOR_CYAN, -1);
	init_pair(CP_VOTER_B, COLOR_MAGENTA, -1);
	init_pair(CP_VOTER_C, COLOR_BLUE, -1);
	init_pair(CP_LEAF, COLOR_GREEN, -1);
	init_pair(CP_ROOT, COLOR_YELLOW, -1);
	init_pair(CP_FOCUS, COLOR_YELLOW, -1);
	init_pair(CP_WARN, COLOR_RED, -1);
}

void	ui_frame(WINDOW *win, const char *title, int focused)
{
	chtype	attr;

	attr = A_NORMAL;
	if (focused)
		attr = COLOR_PAIR(CP_FOCUS) | A_BOLD;
	wattron(win, attr);
	box(win, 0, 0);
	mvwprintw(win, 0, 2, " %s ", title);
	wattroff(win, attr);
}

static void	status_hint(WINDOW *win, t_app *app)
{
	const char	*names[PANEL_COUNT];

	names[PANEL_FRACTAL] = "Fractal";
	names[PANEL_PARAMS] = "Parametros";
	names[PANEL_COST] = "Recursos";
	names[PANEL_TERM] = "Terminal";
	wprintw(win, " [%s] ", names[app->focus]);
	if (app->focus == PANEL_TERM)
		wprintw(win, "Esc: salir del terminal | Tab: panel | help");
	else
		wprintw(win, "Tab/1-4 panel | z zoom | g gen | h ayuda | q salir");
}

void	draw_status(WINDOW *win, t_app *app)
{
	int	rows;
	int	cols;

	getmaxyx(stdscr, rows, cols);
	werase(win);
	wbkgd(win, A_REVERSE);
	wmove(win, 0, 0);
	if (app->too_small)
		wprintw(win, " Terminal %dx%d: minimo %dx%d. Amplia o pulsa q.",
			cols, rows, MIN_WIDTH, MIN_HEIGHT);
	else
		status_hint(win, app);
	wnoutrefresh(win);
}

void	ui_draw(t_app *app)
{
	t_drawer	draw[PANEL_COUNT];
	int			i;

	draw[PANEL_FRACTAL] = draw_fractal;
	draw[PANEL_PARAMS] = draw_params;
	draw[PANEL_COST] = draw_cost;
	draw[PANEL_TERM] = draw_logs;
	werase(stdscr);
	wnoutrefresh(stdscr);
	i = 0;
	while (!app->too_small && i < PANEL_COUNT)
	{
		if (app->panels[i])
		{
			werase(app->panels[i]);
			draw[i](app->panels[i], app);
			wnoutrefresh(app->panels[i]);
		}
		i++;
	}
	if (app->status)
		draw_status(app->status, app);
	doupdate();
}
