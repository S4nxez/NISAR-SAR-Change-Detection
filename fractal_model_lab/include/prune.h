/* ************************************************************************** */
/*                                                                            */
/*                                                      :::      ::::::::   */
/*   prune.h                                            :+:      :+:    :+:   */
/*                                                  +:+ +:+         +:+     */
/*   By: sanxez <desanchezmunoz02@gmail.com>        +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2026/10/29 12:00:00 by sanxez            #+#    #+#             */
/*   Updated: 2026/10/29 12:00:00 by sanxez           ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#ifndef PRUNE_H
# define PRUNE_H

# include "tree.h"

# define PRUNE_MAX_NODES 1048576
# define PRUNE_LEVELS 64
# define PRUNE_OFF 0
# define PRUNE_DONE 1
# define PRUNE_TOO_BIG 2
# define PRUNE_NO_MEMORY 3
# define NODE_ON 0
# define NODE_CUT 1
# define NODE_OFF 2

/*
** Random shutdown of models (random, random_pct and seed in t_params).
** state holds a NODE_* per node in level order: the root is 0 and the
** children of node i are i * depth + 1 to i * depth + depth. NODE_CUT is a
** shut down model and NODE_OFF a model disabled under one. A t_prune must
** start zeroed; prune_clear frees it.
*/
typedef struct s_prune
{
	unsigned char	*state;
	t_params		params;
	t_u64			offset[PRUNE_LEVELS];
	t_u64			active[PRUNE_LEVELS];
	t_u64			nodes;
	t_u64			target;
	t_u64			removed;
	t_u64			cuts;
	int				levels;
	int				ready;
	int				status;
}	t_prune;

int		prune_update(t_prune *prune, t_params params);
void	prune_clear(t_prune *prune);
int		prune_build(t_prune *prune);
void	prune_try(t_prune *prune, t_u64 node);
t_tree	prune_tree(const t_prune *prune);
t_u64	prune_level_nodes(const t_prune *prune, int level);
int		prune_state(const t_prune *prune, int level, t_u64 index);

#endif
