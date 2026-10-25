/* ************************************************************************** */
/*                                                                            */
/*                                                      :::      ::::::::   */
/*   tree.h                                             :+:      :+:    :+:   */
/*                                                  +:+ +:+         +:+     */
/*   By: sanxez <desanchezmunoz02@gmail.com>        +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2026/10/25 12:00:00 by sanxez            #+#    #+#             */
/*   Updated: 2026/10/25 12:00:00 by sanxez           ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#ifndef TREE_H
# define TREE_H

# define U64_MAX 18446744073709551615ULL

typedef unsigned long long	t_u64;

typedef struct s_params
{
	int	levels;
	int	depth;
	int	exponent;
}	t_params;

typedef struct s_tree
{
	int		total_levels;
	t_u64	nodes;
	t_u64	leaves;
	t_u64	voters;
	int		saturated;
}	t_tree;

t_u64	sat_add(t_u64 a, t_u64 b);
t_u64	sat_mul(t_u64 a, t_u64 b);
t_u64	ceil_div(t_u64 a, t_u64 b);
int		tree_total_levels(t_params params);
t_u64	tree_level_nodes(t_params params, int level);
t_tree	tree_build(t_params params);
int		tree_is_leaf(t_params params, int level);
int		tree_is_copy_root(t_params params, int level);
int		tree_iteration(t_params params, int level);

#endif
