/* ************************************************************************** */
/*                                                                            */
/*                                                      :::      ::::::::   */
/*   tree_role.c                                        :+:      :+:    :+:   */
/*                                                  +:+ +:+         +:+     */
/*   By: sanxez <desanchezmunoz02@gmail.com>        +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2026/10/25 12:00:00 by sanxez            #+#    #+#             */
/*   Updated: 2026/10/25 12:00:00 by sanxez           ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#include "tree.h"

int	tree_is_leaf(t_params params, int level)
{
	return (level == tree_total_levels(params) - 1);
}

int	tree_is_copy_root(t_params params, int level)
{
	if (params.levels < 2 || level == 0 || tree_is_leaf(params, level))
		return (0);
	return (level % (params.levels - 1) == 0);
}

int	tree_iteration(t_params params, int level)
{
	int	iteration;

	if (params.levels < 2)
		return (0);
	iteration = level / (params.levels - 1);
	if (iteration >= params.exponent)
		iteration = params.exponent - 1;
	return (iteration);
}
