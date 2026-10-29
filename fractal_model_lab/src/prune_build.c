/* ************************************************************************** */
/*                                                                            */
/*                                                      :::      ::::::::   */
/*   prune_build.c                                      :+:      :+:    :+:   */
/*                                                  +:+ +:+         +:+     */
/*   By: sanxez <desanchezmunoz02@gmail.com>        +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2026/10/29 12:00:00 by sanxez            #+#    #+#             */
/*   Updated: 2026/10/29 12:00:00 by sanxez           ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#include <stdlib.h>
#include "prune.h"

static t_u64	prune_rand(t_u64 *seed)
{
	t_u64	mix;

	*seed += 0x9E3779B97F4A7C15ULL;
	mix = *seed;
	mix = (mix ^ (mix >> 30)) * 0xBF58476D1CE4E5B9ULL;
	mix = (mix ^ (mix >> 27)) * 0x94D049BB133111EBULL;
	return (mix ^ (mix >> 31));
}

static unsigned int	*prune_order(t_prune *prune)
{
	unsigned int	*order;
	t_u64			seed;
	t_u64			done;
	t_u64			pick;

	order = calloc(prune->nodes - 1, sizeof(*order));
	if (!order)
		return (0);
	seed = (t_u64)prune->params.seed;
	done = 0;
	while (done < prune->nodes - 1)
	{
		pick = prune_rand(&seed) % (done + 1);
		order[done] = order[pick];
		order[pick] = (unsigned int)(done + 1);
		done++;
	}
	return (order);
}

static void	prune_count(t_prune *prune)
{
	t_u64	node;
	t_u64	end;
	int		level;

	node = 0;
	level = 0;
	while (level < prune->levels)
	{
		prune->offset[level] = node;
		prune->active[level] = 0;
		end = node + tree_level_nodes(prune->params, level);
		while (node < end)
		{
			if (prune->state[node] == NODE_ON)
				prune->active[level]++;
			node++;
		}
		level++;
	}
}

int	prune_build(t_prune *prune)
{
	unsigned int	*order;
	t_u64			next;
	int				shuffle;

	prune->target = (prune->nodes * (t_u64)prune->params.random_pct + 50)
		/ 100;
	prune->state = calloc(prune->nodes, 1);
	shuffle = (prune->target > 0 && prune->nodes > 1);
	order = 0;
	if (prune->state && shuffle)
		order = prune_order(prune);
	if (!prune->state || (shuffle && !order))
		return (PRUNE_NO_MEMORY);
	next = 0;
	while (order && next < prune->nodes - 1 && prune->removed < prune->target)
	{
		prune_try(prune, order[next]);
		next++;
	}
	free(order);
	prune_count(prune);
	return (PRUNE_DONE);
}

t_tree	prune_tree(const t_prune *prune)
{
	t_tree	tree;

	tree = tree_build(prune->params);
	if (prune->status != PRUNE_DONE)
		return (tree);
	tree.leaves = prune->active[tree.total_levels - 1];
	tree.nodes = prune->nodes - prune->removed;
	tree.voters = tree.nodes - tree.leaves;
	return (tree);
}
