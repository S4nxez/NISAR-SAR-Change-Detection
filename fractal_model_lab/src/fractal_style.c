/* ************************************************************************** */
/*                                                                            */
/*                                                      :::      ::::::::   */
/*   fractal_style.c                                    :+:      :+:    :+:   */
/*                                                  +:+ +:+         +:+     */
/*   By: sanxez <desanchezmunoz02@gmail.com>        +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2026/10/25 12:00:00 by sanxez            #+#    #+#             */
/*   Updated: 2026/10/29 12:00:00 by sanxez           ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#include "ui.h"
#include "view.h"

chtype	view_attr(t_params params, int level)
{
	int	pairs[3];
	int	pair;

	pairs[0] = CP_VOTER_A;
	pairs[1] = CP_VOTER_B;
	pairs[2] = CP_VOTER_C;
	if (tree_is_leaf(params, level))
		return (COLOR_PAIR(CP_LEAF) | A_BOLD);
	if (level == 0)
		return (COLOR_PAIR(CP_ROOT) | A_BOLD);
	pair = pairs[tree_iteration(params, level) % 3];
	if (tree_is_copy_root(params, level))
		return (COLOR_PAIR(pair) | A_BOLD);
	return (COLOR_PAIR(pair));
}

chtype	view_glyph(t_params params, int level)
{
	if (tree_is_leaf(params, level))
		return ('D');
	return ('V');
}

chtype	view_density(t_view *view, t_u64 nodes)
{
	t_u64	per_column;

	per_column = nodes / (t_u64)view->width;
	if (per_column < 4)
		return (':');
	if (per_column < 32)
		return ('+');
	if (per_column < 256)
		return ('*');
	return ('#');
}

int	view_group_level(t_view *view, int level)
{
	while (level > 0 && tree_level_nodes(view->params, level) * 3
		> (t_u64)view->width)
		level--;
	return (level);
}

int	view_fits(t_view *view, int level)
{
	return (tree_level_nodes(view->params, level) <= (t_u64)view->width);
}
