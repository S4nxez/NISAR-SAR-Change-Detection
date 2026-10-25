/* ************************************************************************** */
/*                                                                            */
/*                                                      :::      ::::::::   */
/*   layout.c                                           :+:      :+:    :+:   */
/*                                                  +:+ +:+         +:+     */
/*   By: sanxez <desanchezmunoz02@gmail.com>        +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2026/10/25 12:00:00 by sanxez            #+#    #+#             */
/*   Updated: 2026/10/25 12:00:00 by sanxez           ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#include "app.h"

static WINDOW	*panel_window(int rows, int cols, int y, int x)
{
	WINDOW	*win;

	win = newwin(rows, cols, y, x);
	if (win)
		keypad(win, TRUE);
	return (win);
}

static void	place_quadrants(t_app *app, int rows, int cols)
{
	int	top;
	int	split_top;
	int	split_bottom;

	top = rows * 3 / 5;
	split_top = cols * 3 / 5;
	split_bottom = cols / 2;
	app->panels[PANEL_FRACTAL] = panel_window(top, split_top, 0, 0);
	app->panels[PANEL_PARAMS] = panel_window(top, cols - split_top,
			0, split_top);
	app->panels[PANEL_COST] = panel_window(rows - top, split_bottom, top, 0);
	app->panels[PANEL_TERM] = panel_window(rows - top, cols - split_bottom,
			top, split_bottom);
}

void	layout_build(t_app *app)
{
	int	rows;
	int	cols;

	getmaxyx(stdscr, rows, cols);
	app->status = panel_window(1, cols, rows - 1, 0);
	app->too_small = (rows < MIN_HEIGHT || cols < MIN_WIDTH);
	if (app->too_small)
		return ;
	if (app->zoom != NO_ZOOM)
		app->panels[app->zoom] = panel_window(rows - 1, cols, 0, 0);
	else
		place_quadrants(app, rows - 1, cols);
}

void	layout_destroy(t_app *app)
{
	int	i;

	i = 0;
	while (i < PANEL_COUNT)
	{
		if (app->panels[i])
			delwin(app->panels[i]);
		app->panels[i] = 0;
		i++;
	}
	if (app->status)
		delwin(app->status);
	app->status = 0;
}

void	layout_rebuild(t_app *app)
{
	layout_destroy(app);
	layout_build(app);
}
