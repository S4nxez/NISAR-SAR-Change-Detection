/* ************************************************************************** */
/*                                                                            */
/*                                                      :::      ::::::::   */
/*   command_view.c                                     :+:      :+:    :+:   */
/*                                                  +:+ +:+         +:+     */
/*   By: sanxez <desanchezmunoz02@gmail.com>        +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2026/10/25 12:00:00 by sanxez            #+#    #+#             */
/*   Updated: 2026/10/25 12:00:00 by sanxez           ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#include <string.h>
#include "command.h"
#include "format.h"

static int	parse_panel(t_app *app, const char *arg)
{
	int	panel;

	if (!parse_int(arg, &panel) || panel < 1 || panel > PANEL_COUNT)
	{
		app_log(app, "error: panel 1-4 (1 fractal, 2 param, 3 rec, 4 term)");
		return (-1);
	}
	return (panel - 1);
}

int	cmd_focus(t_app *app, int argc, char **argv)
{
	int	panel;

	if (argc != 2)
	{
		app_log(app, "uso: focus <1-4>");
		return (0);
	}
	panel = parse_panel(app, argv[1]);
	if (panel < 0)
		return (0);
	app_focus(app, panel);
	return (1);
}

int	cmd_zoom(t_app *app, int argc, char **argv)
{
	int	panel;

	panel = app->focus;
	if (argc == 2 && !strcmp(argv[1], "off"))
		panel = NO_ZOOM;
	else if (argc == 2)
		panel = parse_panel(app, argv[1]);
	else if (argc == 1 && app->zoom != NO_ZOOM)
		panel = NO_ZOOM;
	if (argc > 2 || (argc == 2 && panel == -1 && strcmp(argv[1], "off")))
		return (0);
	app->zoom = panel;
	if (panel != NO_ZOOM)
		app->focus = panel;
	layout_rebuild(app);
	return (1);
}

int	cmd_scroll(t_app *app, int argc, char **argv)
{
	int	level;
	int	total;

	total = tree_total_levels(app_params(app));
	if (argc != 2 || !parse_int(argv[1], &level)
		|| level < 1 || level > total)
	{
		app_logf(app, "uso: scroll <nivel 1-%d>", total);
		return (0);
	}
	app->fractal_top = level - 1;
	return (1);
}

int	cmd_quit(t_app *app, int argc, char **argv)
{
	(void)argc;
	(void)argv;
	app->running = 0;
	return (1);
}
