/* ************************************************************************** */
/*                                                                            */
/*                                                      :::      ::::::::   */
/*   app.c                                              :+:      :+:    :+:   */
/*                                                  +:+ +:+         +:+     */
/*   By: sanxez <desanchezmunoz02@gmail.com>        +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2026/10/25 12:00:00 by sanxez            #+#    #+#             */
/*   Updated: 2026/10/29 12:00:00 by sanxez           ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#include <locale.h>
#include <string.h>
#include "app.h"
#include "ui.h"

void	app_init(t_app *app)
{
	memset(app, 0, sizeof(*app));
	field_reset(app->values);
	app->running = 1;
	app->zoom = NO_ZOOM;
	app->focus = PANEL_TERM;
	app->prev_focus = PANEL_PARAMS;
	app_log(app, "Fractal Model Lab listo. Escribe 'help' o pulsa Tab.");
	report_generate(app);
}

t_params	app_params(t_app *app)
{
	return (field_params(app->values));
}

t_tree	app_tree(t_app *app)
{
	return (prune_tree(app_prune(app)));
}

static void	curses_start(void)
{
	setlocale(LC_ALL, "");
	setlocale(LC_NUMERIC, "C");
	initscr();
	cbreak();
	noecho();
	curs_set(0);
	set_escdelay(25);
	keypad(stdscr, TRUE);
	ui_init_colors();
}

void	app_run(t_app *app)
{
	int	key;

	curses_start();
	layout_build(app);
	while (app->running)
	{
		ui_draw(app);
		key = wgetch(app->status);
		handle_input(app, key);
	}
	layout_destroy(app);
	endwin();
	prune_clear(&app->prune);
}
