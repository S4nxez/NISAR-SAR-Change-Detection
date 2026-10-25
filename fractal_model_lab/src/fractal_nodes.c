/* ************************************************************************** */
/*                                                                            */
/*                                                      :::      ::::::::   */
/*   fractal_nodes.c                                    :+:      :+:    :+:   */
/*                                                  +:+ +:+         +:+     */
/*   By: sanxez <desanchezmunoz02@gmail.com>        +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2026/10/25 12:00:00 by sanxez            #+#    #+#             */
/*   Updated: 2026/10/25 12:00:00 by sanxez           ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#include "view.h"

static void	draw_dense(t_view *view, int level)
{
	t_span	span;
	t_u64	groups;
	t_u64	index;
	chtype	glyph;
	int		group_level;

	group_level = view_group_level(view, level);
	groups = tree_level_nodes(view->params, group_level);
	glyph = view_density(view, level) | view_attr(view->params, level);
	index = 0;
	while (index < groups)
	{
		view_group_span(view, group_level, index, &span);
		mvwhline(view->win, view_row(view, level), span.first, glyph,
			span.last - span.first + 1);
		index++;
	}
}

void	view_draw_level(t_view *view, int level)
{
	t_u64	nodes;
	t_u64	index;
	chtype	glyph;
	int		y;

	if (!view_fits(view, level))
	{
		draw_dense(view, level);
		return ;
	}
	nodes = tree_level_nodes(view->params, level);
	glyph = view_glyph(view->params, level) | view_attr(view->params, level);
	y = view_row(view, level);
	index = 0;
	while (index < nodes)
	{
		mvwaddch(view->win, y, view_node_x(view, level, index), glyph);
		index++;
	}
}
