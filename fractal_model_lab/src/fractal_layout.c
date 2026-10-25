/* ************************************************************************** */
/*                                                                            */
/*                                                      :::      ::::::::   */
/*   fractal_layout.c                                   :+:      :+:    :+:   */
/*                                                  +:+ +:+         +:+     */
/*   By: sanxez <desanchezmunoz02@gmail.com>        +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2026/10/25 12:00:00 by sanxez            #+#    #+#             */
/*   Updated: 2026/10/25 12:00:00 by sanxez           ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#include "view.h"

int	view_sparse(t_view *view, int level)
{
	t_u64	nodes;

	nodes = tree_level_nodes(view->params, level);
	return (nodes <= (t_u64)((view->width + 2) / 3));
}

static void	span_bounds(t_view *view, int level, t_u64 index, t_span *span)
{
	t_u64	nodes;
	t_u64	width;

	nodes = tree_level_nodes(view->params, level);
	width = (t_u64)view->width;
	span->first = view->left + (int)(index * width / nodes);
	span->last = view->left + (int)((index + 1) * width / nodes) - 1;
	if (nodes > 1 && span->last - span->first >= 2)
		span->last--;
	span->hits_child = 0;
}

int	view_node_x(t_view *view, int level, t_u64 index)
{
	if (level == 0 || view_sparse(view, level))
		return (view_span_center(view, level, index));
	return (view_compact_x(view, level, index));
}

void	view_group_span(t_view *view, int level, t_u64 index, t_span *span)
{
	span_bounds(view, level, index, span);
	span->parent = view_node_x(view, level, index);
}
