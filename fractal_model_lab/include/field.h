/* ************************************************************************** */
/*                                                                            */
/*                                                      :::      ::::::::   */
/*   field.h                                            :+:      :+:    :+:   */
/*                                                  +:+ +:+         +:+     */
/*   By: sanxez <desanchezmunoz02@gmail.com>        +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2026/10/25 12:00:00 by sanxez            #+#    #+#             */
/*   Updated: 2026/10/29 12:00:00 by sanxez           ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#ifndef FIELD_H
# define FIELD_H

# include "tree.h"
# include "cost.h"

typedef enum e_field_id
{
	F_LEVELS,
	F_DEPTH,
	F_EXPONENT,
	F_RANDOM,
	F_RANDOM_PCT,
	F_SEED,
	F_RUNTIME_MIB,
	F_LEAF_MIB,
	F_VOTER_MIB,
	F_DISK_PCT,
	F_LEAF_US,
	F_VOTER_US,
	F_TARGET_MS,
	F_HEADROOM_PCT,
	FIELD_COUNT
}	t_field_id;

# define FRACTAL_FIELDS 6

typedef struct s_field
{
	const char	*name;
	const char	*alias;
	const char	*label;
	int			min;
	int			max;
	int			initial;
}	t_field;

const t_field	*field_get(int id);
int				field_find(const char *name);
void			field_reset(int *values);
t_params		field_params(const int *values);
t_profile		field_profile(const int *values);

#endif
