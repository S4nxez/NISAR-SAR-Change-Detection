/* ************************************************************************** */
/*                                                                            */
/*                                                      :::      ::::::::   */
/*   fractal_edges.c                                    :+:      :+:    :+:   */
/*                                                  +:+ +:+         +:+     */
/*   By: sanxez <desanchezmunoz02@gmail.com>        +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2026/10/25 12:00:00 by sanxez            #+#    #+#             */
/*   Updated: 2026/10/25 12:00:00 by sanxez           ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#include "view.h"

static void	edge_vline(t_view *view, int x, int from, int to)
{
	chtype	attr;

	attr = view_edge_attr(view, from);
	while (from <= to)
	{
		mvwaddch(view->win, from, x, ACS_VLINE | attr);
		from++;
	}
}

static void	sparse_edges(t_view *view, int level, t_u64 parent)
{
	t_span	span;
	int		bar_y;
	int		tees;

	bar_y = view_row(view, level + 1) - 1;
	tees = view_child_extent(view, level, parent, &span);
	edge_vline(view, span.parent, view_row(view, level) + 1, bar_y - 1);
	view_draw_span(view, bar_y, span);
	if (tees)
		span.hits_child = view_child_tees(view, level + 1,
				parent * (t_u64)view->params.depth, span);
	view_draw_junction(view, bar_y, span);
}

static void	dense_edges(t_view *view, int level)
{
	t_span	span;
	t_u64	groups;
	t_u64	index;
	int		group_level;

	group_level = view_group_level(view, level);
	groups = tree_level_nodes(view->params, group_level);
	index = 0;
	while (index < groups)
	{
		view_group_span(view, group_level, index, &span);
		edge_vline(view, (span.first + span.last) / 2,
			view_row(view, level) + 1, view_row(view, level + 1) - 1);
		index++;
	}
}

void	view_draw_edges(t_view *view, int level)
{
	t_u64	nodes;
	t_u64	parent;

	if (view->gap < 2)
		return ;
	if (!view_sparse(view, level))
	{
		dense_edges(view, level);
		return ;
	}
	nodes = tree_level_nodes(view->params, level);
	parent = 0;
	while (parent < nodes)
		sparse_edges(view, level, parent++);
}
