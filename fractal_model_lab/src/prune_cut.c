/* ************************************************************************** */
/*                                                                            */
/*                                                      :::      ::::::::   */
/*   prune_cut.c                                        :+:      :+:    :+:   */
/*                                                  +:+ +:+         +:+     */
/*   By: sanxez <desanchezmunoz02@gmail.com>        +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2026/10/29 12:00:00 by sanxez            #+#    #+#             */
/*   Updated: 2026/10/29 12:00:00 by sanxez           ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#include "prune.h"

static int	keeps_sibling(const t_prune *prune, t_u64 node)
{
	t_u64	depth;
	t_u64	child;
	t_u64	last;

	depth = (t_u64)prune->params.depth;
	child = (node - 1) / depth * depth + 1;
	last = child + depth - 1;
	while (child <= last)
	{
		if (child != node && prune->state[child] == NODE_ON)
			return (1);
		child++;
	}
	return (0);
}

static t_u64	branch_size(const t_prune *prune, t_u64 node, t_u64 limit)
{
	t_u64	depth;
	t_u64	first;
	t_u64	last;
	t_u64	size;
	t_u64	i;

	depth = (t_u64)prune->params.depth;
	first = node;
	last = node;
	size = 0;
	while (first < prune->nodes && size <= limit)
	{
		i = first;
		while (i <= last)
		{
			if (prune->state[i] == NODE_ON)
				size++;
			i++;
		}
		first = first * depth + 1;
		last = last * depth + depth;
	}
	return (size);
}

static void	cut_branch(t_prune *prune, t_u64 node)
{
	t_u64	depth;
	t_u64	first;
	t_u64	last;
	t_u64	i;

	depth = (t_u64)prune->params.depth;
	first = node * depth + 1;
	last = node * depth + depth;
	while (first < prune->nodes)
	{
		i = first;
		while (i <= last)
		{
			if (prune->state[i] == NODE_CUT)
				prune->cuts--;
			prune->state[i] = NODE_OFF;
			i++;
		}
		first = first * depth + 1;
		last = last * depth + depth;
	}
	prune->state[node] = NODE_CUT;
	prune->cuts++;
}

void	prune_try(t_prune *prune, t_u64 node)
{
	t_u64	left;
	t_u64	size;

	if (prune->state[node] != NODE_ON || !keeps_sibling(prune, node))
		return ;
	left = prune->target - prune->removed;
	size = branch_size(prune, node, left);
	if (size > left)
		return ;
	cut_branch(prune, node);
	prune->removed += size;
}
