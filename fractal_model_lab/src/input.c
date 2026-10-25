/* ************************************************************************** */
/*                                                                            */
/*                                                      :::      ::::::::   */
/*   input.c                                            :+:      :+:    :+:   */
/*                                                  +:+ +:+         +:+     */
/*   By: sanxez <desanchezmunoz02@gmail.com>        +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2026/10/25 12:00:00 by sanxez            #+#    #+#             */
/*   Updated: 2026/10/25 12:00:00 by sanxez           ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#include "app.h"

void	app_focus(t_app *app, int panel)
{
	if (panel < 0 || panel >= PANEL_COUNT || panel == app->focus)
		return ;
	if (app->focus != PANEL_TERM)
		app->prev_focus = app->focus;
	app->focus = panel;
	if (app->zoom != NO_ZOOM)
	{
		app->zoom = panel;
		layout_rebuild(app);
	}
}

static void	toggle_zoom(t_app *app)
{
	if (app->zoom == NO_ZOOM)
		app->zoom = app->focus;
	else
		app->zoom = NO_ZOOM;
	layout_rebuild(app);
}

static int	global_key(t_app *app, int key)
{
	if (key == 'q' || key == 'Q')
		app->running = 0;
	else if (key == 'g' || key == 'G')
		report_generate(app);
	else if (key == 'h' || key == '?')
		app_help(app);
	else if (key == 'z' || key == 'Z')
		toggle_zoom(app);
	else if (key == ':' || key == '/')
		app_focus(app, PANEL_TERM);
	else if (key >= '1' && key <= '4')
		app_focus(app, key - '1');
	else
		return (0);
	return (1);
}

static void	fractal_key(t_app *app, int key)
{
	int	last;

	last = tree_total_levels(app_params(app)) - 1;
	if (key == KEY_UP && app->fractal_top > 0)
		app->fractal_top--;
	else if (key == KEY_DOWN && app->fractal_top < last)
		app->fractal_top++;
	else if (key == KEY_HOME)
		app->fractal_top = 0;
	else if (key == KEY_END)
		app->fractal_top = last;
}

void	handle_input(t_app *app, int key)
{
	if (key == KEY_RESIZE)
		layout_rebuild(app);
	else if (key == '\t')
		app_focus(app, (app->focus + 1) % PANEL_COUNT);
	else if (key == KEY_BTAB)
		app_focus(app, (app->focus + PANEL_COUNT - 1) % PANEL_COUNT);
	else if (app->too_small && (key == 'q' || key == 'Q'))
		app->running = 0;
	else if (app->focus == PANEL_TERM)
		term_key(app, key);
	else if (global_key(app, key))
		return ;
	else if (app->focus == PANEL_PARAMS)
		params_key(app, key);
	else if (app->focus == PANEL_FRACTAL)
		fractal_key(app, key);
}
