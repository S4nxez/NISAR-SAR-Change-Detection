/* ************************************************************************** */
/*                                                                            */
/*                                                      :::      ::::::::   */
/*   fractal_place.c                                    :+:      :+:    :+:   */
/*                                                  +:+ +:+         +:+     */
/*   By: sanxez <desanchezmunoz02@gmail.com>        +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2026/10/25 12:00:00 by sanxez            #+#    #+#             */
/*   Updated: 2026/10/25 12:00:00 by sanxez           ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#include "view.h"

int	view_span_center(t_view *view, int level, t_u64 index)
{
	t_u64	nodes;
	t_u64	width;
	t_u64	first;
	t_u64	last;

	nodes = tree_level_nodes(view->params, level);
	width = (t_u64)view->width;
	first = index * width / nodes;
	last = (index + 1) * width / nodes - 1;
	return (view->left + (int)((first + last) / 2));
}

int	view_compact_x(t_view *view, int level, t_u64 index)
{
	t_span	span;
	int		depth;
	int		base;

	depth = view->params.depth;
	view_group_span(view, level - 1, index / (t_u64)depth, &span);
	base = span.parent - (depth - 1) / 2;
	if (base + depth - 1 > span.last)
		base = span.last - depth + 1;
	if (base < span.first)
		base = span.first;
	return (base + (int)(index % (t_u64)depth));
}
