/* ************************************************************************** */
/*                                                                            */
/*                                                      :::      ::::::::   */
/*   ui_params.c                                        :+:      :+:    :+:   */
/*                                                  +:+ +:+         +:+     */
/*   By: sanxez <desanchezmunoz02@gmail.com>        +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2026/10/25 12:00:00 by sanxez            #+#    #+#             */
/*   Updated: 2026/10/29 12:00:00 by sanxez           ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#include <stdio.h>
#include "ui.h"
#include "format.h"

static void	draw_field(WINDOW *win, t_app *app, int id, int y)
{
	const t_field	*field;
	chtype			attr;
	char			marker;

	field = field_get(id);
	marker = ' ';
	if (app->selected == id)
		marker = '>';
	attr = A_NORMAL;
	if (app->selected == id && app->focus == PANEL_PARAMS)
		attr = A_REVERSE | A_BOLD;
	else if (app->selected == id)
		attr = A_BOLD;
	wattron(win, attr);
	ui_textf(win, y, "%c %-12s %3d   (%d-%d)",
		marker, field->label, app->values[id],
		field->min, field->max);
	wattroff(win, attr);
}

static void	draw_levels_line(WINDOW *win, t_app *app, int y)
{
	char	line[256];
	char	count[FMT_LEN];
	int		len;
	int		level;
	int		total;

	total = tree_total_levels(app_params(app));
	len = snprintf(line, sizeof(line), "Por nivel:");
	level = 0;
	while (level < total && len < getmaxx(win) - 8)
	{
		fmt_count(prune_level_nodes(app_prune(app), level), count, FMT_LEN);
		len += snprintf(line + len, sizeof(line) - len, " %s", count);
		level++;
	}
	if (level < total)
		snprintf(line + len, sizeof(line) - len, " ..");
	ui_text(win, y, 2, line);
}

static void	draw_random(WINDOW *win, t_prune *prune, int y)
{
	char	removed[FMT_LEN];
	char	nodes[FMT_LEN];

	if (prune->status == PRUNE_OFF)
		return ;
	fmt_count(prune->removed, removed, FMT_LEN);
	fmt_count(prune->nodes, nodes, FMT_LEN);
	wattron(win, COLOR_PAIR(CP_WARN));
	if (prune->status == PRUNE_DONE)
		ui_textf(win, y, "Apagados  %s de %s (%.1f%%)", removed, nodes,
			100.0 * prune->removed / prune->nodes);
	else if (prune->status == PRUNE_TOO_BIG)
	{
		fmt_count(PRUNE_MAX_NODES, nodes, FMT_LEN);
		ui_textf(win, y, "Aleatorio sin aplicar: >%s nodos", nodes);
	}
	else
		ui_text(win, y, 2, "Aleatorio sin aplicar: sin memoria");
	wattroff(win, COLOR_PAIR(CP_WARN));
}

static void	draw_derived(WINDOW *win, t_app *app, int y)
{
	char	nodes[FMT_LEN];
	char	leaves[FMT_LEN];
	char	voters[FMT_LEN];
	t_tree	tree;

	tree = app_tree(app);
	fmt_count(tree.nodes, nodes, FMT_LEN);
	fmt_count(tree.leaves, leaves, FMT_LEN);
	fmt_count(tree.voters, voters, FMT_LEN);
	ui_textf(win, y, "Niveles   (L-1)*E+1 = %d", tree.total_levels);
	ui_textf(win, y + 1, "Nodos     %s", nodes);
	wattron(win, COLOR_PAIR(CP_LEAF));
	ui_textf(win, y + 2, "Decisores %s  (hojas D)", leaves);
	wattroff(win, COLOR_PAIR(CP_LEAF));
	wattron(win, COLOR_PAIR(CP_VOTER_A));
	ui_textf(win, y + 3, "Votantes  %s  (nodos V)", voters);
	wattroff(win, COLOR_PAIR(CP_VOTER_A));
	draw_levels_line(win, app, y + 4);
	if (tree.saturated)
		ui_text(win, y + 5, 2, "Aviso: >2^64, valores saturados");
	else
		draw_random(win, app_prune(app), y + 5);
}

void	draw_params(WINDOW *win, t_app *app)
{
	int	id;

	ui_frame(win, "[2] PARAMETROS", app->focus == PANEL_PARAMS);
	id = 0;
	while (id < FRACTAL_FIELDS)
	{
		draw_field(win, app, id, id + 1);
		id++;
	}
	draw_derived(win, app, FRACTAL_FIELDS + 2);
	if (app->focus == PANEL_PARAMS && getmaxy(win) - 2 > FRACTAL_FIELDS + 7)
		ui_text(win, getmaxy(win) - 2, 2, "-/+ cambia  Enter edita");
}
