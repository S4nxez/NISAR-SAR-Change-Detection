/* ************************************************************************** */
/*                                                                            */
/*                                                      :::      ::::::::   */
/*   prune.c                                            :+:      :+:    :+:   */
/*                                                  +:+ +:+         +:+     */
/*   By: sanxez <desanchezmunoz02@gmail.com>        +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2026/10/29 12:00:00 by sanxez            #+#    #+#             */
/*   Updated: 2026/10/29 12:00:00 by sanxez           ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#include <stdlib.h>
#include "prune.h"

static int	same_params(t_params a, t_params b)
{
	return (a.levels == b.levels && a.depth == b.depth
		&& a.exponent == b.exponent && a.random == b.random
		&& a.random_pct == b.random_pct && a.seed == b.seed);
}

void	prune_clear(t_prune *prune)
{
	free(prune->state);
	prune->state = 0;
	prune->ready = 0;
	prune->status = PRUNE_OFF;
	prune->nodes = 0;
	prune->target = 0;
	prune->removed = 0;
	prune->cuts = 0;
}

int	prune_update(t_prune *prune, t_params params)
{
	t_tree	tree;

	if (prune->ready && same_params(prune->params, params))
		return (prune->status);
	prune_clear(prune);
	prune->params = params;
	prune->ready = 1;
	if (!params.random)
		return (prune->status);
	tree = tree_build(params);
	prune->nodes = tree.nodes;
	prune->levels = tree.total_levels;
	if (tree.nodes > PRUNE_MAX_NODES || tree.total_levels > PRUNE_LEVELS)
		prune->status = PRUNE_TOO_BIG;
	else
		prune->status = prune_build(prune);
	return (prune->status);
}

int	prune_state(const t_prune *prune, int level, t_u64 index)
{
	if (prune->status != PRUNE_DONE)
		return (NODE_ON);
	return (prune->state[prune->offset[level] + index]);
}

t_u64	prune_level_nodes(const t_prune *prune, int level)
{
	if (prune->status != PRUNE_DONE)
		return (tree_level_nodes(prune->params, level));
	return (prune->active[level]);
}
