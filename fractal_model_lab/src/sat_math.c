/* ************************************************************************** */
/*                                                                            */
/*                                                      :::      ::::::::   */
/*   sat_math.c                                         :+:      :+:    :+:   */
/*                                                  +:+ +:+         +:+     */
/*   By: sanxez <desanchezmunoz02@gmail.com>        +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2026/10/25 12:00:00 by sanxez            #+#    #+#             */
/*   Updated: 2026/10/25 12:00:00 by sanxez           ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#include "tree.h"

t_u64	sat_add(t_u64 a, t_u64 b)
{
	if (a > U64_MAX - b)
		return (U64_MAX);
	return (a + b);
}

t_u64	sat_mul(t_u64 a, t_u64 b)
{
	if (a != 0 && b > U64_MAX / a)
		return (U64_MAX);
	return (a * b);
}

t_u64	ceil_div(t_u64 a, t_u64 b)
{
	if (b == 0)
		return (U64_MAX);
	if (a == U64_MAX)
		return (U64_MAX);
	return ((a + b - 1) / b);
}
