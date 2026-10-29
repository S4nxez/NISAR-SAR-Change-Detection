/* ************************************************************************** */
/*                                                                            */
/*                                                      :::      ::::::::   */
/*   input_params.c                                     :+:      :+:    :+:   */
/*                                                  +:+ +:+         +:+     */
/*   By: sanxez <desanchezmunoz02@gmail.com>        +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2026/10/25 12:00:00 by sanxez            #+#    #+#             */
/*   Updated: 2026/10/29 02:00:00 by sanxez           ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#include <stdio.h>
#include "app.h"
#include "format.h"

static void	log_tree(t_app *app)
{
	char	nodes[FMT_LEN];
	t_tree	tree;

	tree = app_tree(app);
	fmt_count(tree.nodes, nodes, FMT_LEN);
	app_logf(app, "  -> %d niveles, %s nodos", tree.total_levels, nodes);
	if (tree.saturated)
		app_log(app, "aviso: el recuento supera 2^64 (saturado)");
}

int	field_change(t_app *app, int id, int value)
{
	const t_field	*field;
	int				last;

	field = field_get(id);
	if (value < field->min || value > field->max)
	{
		app_logf(app, "error: %s fuera de rango (%d-%d)",
			field->name, field->min, field->max);
		return (0);
	}
	app->values[id] = value;
	app_logf(app, "%s = %d", field->name, value);
	if (id >= FRACTAL_FIELDS && id < PARAM_FIELDS)
		report_request_field(app, id);
	if (id >= FRACTAL_FIELDS)
		return (1);
	last = tree_total_levels(app_params(app)) - 1;
	if (app->fractal_top > last)
		app->fractal_top = last;
	log_tree(app);
	return (1);
}

static void	start_edit(t_app *app)
{
	const t_field	*field;

	field = field_get(app->selected);
	app->cmd_len = snprintf(app->cmd, CMD_LEN, "set %s ", field->name);
	app_focus(app, PANEL_TERM);
}

void	params_key(t_app *app, int key)
{
	int	value;

	value = app->values[app->selected];
	if (key == KEY_UP)
		app->selected = (app->selected + PARAM_FIELDS - 1) % PARAM_FIELDS;
	else if (key == KEY_DOWN)
		app->selected = (app->selected + 1) % PARAM_FIELDS;
	else if (key == KEY_LEFT || key == '-')
		field_change(app, app->selected, value - 1);
	else if (key == KEY_RIGHT || key == '+' || key == '=')
		field_change(app, app->selected, value + 1);
	else if (key == '\n' || key == '\r' || key == KEY_ENTER)
		start_edit(app);
}
