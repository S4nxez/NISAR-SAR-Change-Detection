/* ************************************************************************** */
/*                                                                            */
/*                                                      :::      ::::::::   */
/*   fractal_view.c                                     :+:      :+:    :+:   */
/*                                                  +:+ +:+         +:+     */
/*   By: sanxez <desanchezmunoz02@gmail.com>        +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2026/10/25 12:00:00 by sanxez            #+#    #+#             */
/*   Updated: 2026/10/25 12:00:00 by sanxez           ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#include "ui.h"
#include "view.h"
#include "format.h"

void	view_init(t_view *view, WINDOW *win, t_params params, int first)
{
	int	rows;
	int	used;

	view->win = win;
	view->params = params;
	view->total = tree_total_levels(params);
	view->first = first;
	rows = getmaxy(win) - 3;
	view->shown = view->total - first;
	if (view->shown > rows)
		view->shown = rows;
	view->gap = 1;
	if (view->shown > 1)
		view->gap = (rows - 1) / (view->shown - 1);
	if (view->gap > VIEW_MAX_GAP)
		view->gap = VIEW_MAX_GAP;
	used = (view->shown - 1) * view->gap + 1;
	view->top = 2 + (rows - used) / 2;
	view->left = VIEW_LABEL_W;
	view->width = getmaxx(win) - VIEW_LABEL_W - VIEW_COUNT_W - 1;
}

int	view_row(t_view *view, int level)
{
	return (view->top + (level - view->first) * view->gap);
}

static void	draw_header(t_view *view, t_tree tree)
{
	char	nodes[FMT_LEN];
	char	leaves[FMT_LEN];

	fmt_count(tree.nodes, nodes, FMT_LEN);
	fmt_count(tree.leaves, leaves, FMT_LEN);
	ui_textf(view->win, 1, "%d niveles  %s nodos  %s decisores",
		view->total, nodes, leaves);
	if (view->first > 0)
		mvwprintw(view->win, getmaxy(view->win) - 1, 2,
			" ^ %d niveles arriba ", view->first);
	if (view->first + view->shown < view->total)
		mvwprintw(view->win, getmaxy(view->win) - 1,
			getmaxx(view->win) - 24, " v %d niveles abajo ",
			view->total - view->first - view->shown);
}

static void	draw_label(t_view *view, int level)
{
	char	count[FMT_LEN];
	chtype	attr;
	int		y;

	y = view_row(view, level);
	attr = view_attr(view->params, level);
	fmt_count(tree_level_nodes(view->params, level), count, FMT_LEN);
	wattron(view->win, attr);
	mvwprintw(view->win, y, 1, "%2d", level + 1);
	if (tree_is_copy_root(view->params, level))
		mvwaddch(view->win, y, 3, '*');
	mvwprintw(view->win, y, view->left + view->width + 1,
		"%*s", VIEW_COUNT_W - 1, count);
	wattroff(view->win, attr);
}

void	draw_fractal(WINDOW *win, t_app *app)
{
	t_view	view;
	int		level;

	ui_frame(win, "[1] FRACTAL  V votante  D decisor  * copia",
		app->focus == PANEL_FRACTAL);
	view_init(&view, win, app_params(app), app->fractal_top);
	draw_header(&view, app_tree(app));
	if (view.width < 4 || view.shown < 1)
		return ;
	level = view.first;
	while (level + 1 < view.first + view.shown)
		view_draw_edges(&view, level++);
	level = view.first;
	while (level < view.first + view.shown)
	{
		view_draw_level(&view, level);
		draw_label(&view, level);
		level++;
	}
}
