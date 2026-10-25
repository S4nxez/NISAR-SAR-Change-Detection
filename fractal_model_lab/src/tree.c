/* ************************************************************************** */
/*                                                                            */
/*                                                      :::      ::::::::   */
/*   tree.c                                             :+:      :+:    :+:   */
/*                                                  +:+ +:+         +:+     */
/*   By: sanxez <desanchezmunoz02@gmail.com>        +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2026/10/25 12:00:00 by sanxez            #+#    #+#             */
/*   Updated: 2026/10/25 12:00:00 by sanxez           ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#include "tree.h"

int	tree_total_levels(t_params params)
{
	return ((params.levels - 1) * params.exponent + 1);
}

t_u64	tree_level_nodes(t_params params, int level)
{
	t_u64	count;
	int		i;

	count = 1;
	i = 0;
	while (i < level && count != U64_MAX)
	{
		count = sat_mul(count, (t_u64)params.depth);
		i++;
	}
	return (count);
}

t_tree	tree_build(t_params params)
{
	t_tree	tree;
	int		level;

	tree.total_levels = tree_total_levels(params);
	tree.voters = 0;
	level = 0;
	while (level < tree.total_levels - 1)
	{
		tree.voters = sat_add(tree.voters,
				tree_level_nodes(params, level));
		level++;
	}
	tree.leaves = tree_level_nodes(params, tree.total_levels - 1);
	tree.nodes = sat_add(tree.voters, tree.leaves);
	tree.saturated = (tree.nodes == U64_MAX);
	return (tree);
}
