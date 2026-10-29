/* ************************************************************************** */
/*                                                                            */
/*                                                      :::      ::::::::   */
/*   fractal_prune.c                                    :+:      :+:    :+:   */
/*                                                  +:+ +:+         +:+     */
/*   By: sanxez <desanchezmunoz02@gmail.com>        +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2026/10/29 12:00:00 by sanxez            #+#    #+#             */
/*   Updated: 2026/10/29 12:00:00 by sanxez           ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#include "ui.h"
#include "view.h"

chtype	view_node_glyph(t_view *view, int level, t_u64 index)
{
	int	state;

	state = prune_state(view->prune, level, index);
	if (state == NODE_OFF)
		return (0);
	if (state == NODE_CUT)
		return ('x' | COLOR_PAIR(CP_WARN) | A_BOLD);
	return (view_glyph(view->params, level) | view_attr(view->params, level));
}

static t_u64	group_active(t_view *view, int level, int top, t_u64 group)
{
	t_u64	width;
	t_u64	index;
	t_u64	active;

	width = tree_level_nodes(view->params, level - top);
	index = group * width;
	active = 0;
	while (index < (group + 1) * width)
	{
		if (prune_state(view->prune, level, index) == NODE_ON)
			active++;
		index++;
	}
	return (active);
}

chtype	view_dense_glyph(t_view *view, int level, int top, t_u64 group)
{
	t_u64	nodes;

	nodes = tree_level_nodes(view->params, level);
	if (view->prune->status == PRUNE_DONE)
	{
		if (prune_state(view->prune, top, group) != NODE_ON)
			return (0);
		nodes = sat_mul(group_active(view, level, top, group),
				tree_level_nodes(view->params, top));
	}
	return (view_density(view, nodes) | view_attr(view->params, level));
}
