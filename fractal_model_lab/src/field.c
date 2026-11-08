/* ************************************************************************** */
/*                                                                            */
/*                                                      :::      ::::::::   */
/*   field.c                                            :+:      :+:    :+:   */
/*                                                  +:+ +:+         +:+     */
/*   By: sanxez <desanchezmunoz02@gmail.com>        +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2026/10/25 12:00:00 by sanxez            #+#    #+#             */
/*   Updated: 2026/10/25 12:00:00 by sanxez           ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#include <string.h>
#include "field.h"

const t_field	*field_get(int id)
{
	static const t_field	fields[FIELD_COUNT] = {
	{"levels", "Levels", 1, 12, 3},
	{"depth", "Depth", 1, 12, 3},
	{"exponent", "Exponent", 1, 5, 2},
	{"runtime_mib", "Runtime TF (MiB)", 0, 65536, 512},
	{"leaf_mib", "Decider RAM (MiB)", 1, 65536, 48},
	{"voter_mib", "Voter RAM (MiB)", 1, 65536, 6},
	{"disk_pct", "Weights on disk (%RAM)", 0, 1000, 40},
	{"leaf_us", "Decider CPU (us)", 1, 100000000, 5000},
	{"voter_us", "Voter CPU (us)", 1, 100000000, 200},
	{"target_ms", "Target latency (ms)", 1, 600000, 250},
	{"headroom_pct", "RAM headroom (%)", 0, 500, 25}
	};

	if (id < 0 || id >= FIELD_COUNT)
		return (0);
	return (&fields[id]);
}

int	field_find(const char *name)
{
	const t_field	*field;
	int				id;

	id = 0;
	while (name && id < FIELD_COUNT)
	{
		field = field_get(id);
		if (!strcmp(name, field->name))
			return (id);
		id++;
	}
	return (-1);
}

void	field_reset(int *values)
{
	int	id;

	id = 0;
	while (id < FIELD_COUNT)
	{
		values[id] = field_get(id)->initial;
		id++;
	}
}

t_params	field_params(const int *values)
{
	t_params	params;

	params.levels = values[F_LEVELS];
	params.depth = values[F_DEPTH];
	params.exponent = values[F_EXPONENT];
	return (params);
}

t_profile	field_profile(const int *values)
{
	t_profile	profile;

	profile.runtime_mib = values[F_RUNTIME_MIB];
	profile.leaf_mib = values[F_LEAF_MIB];
	profile.voter_mib = values[F_VOTER_MIB];
	profile.disk_pct = values[F_DISK_PCT];
	profile.leaf_us = values[F_LEAF_US];
	profile.voter_us = values[F_VOTER_US];
	profile.target_ms = values[F_TARGET_MS];
	profile.headroom_pct = values[F_HEADROOM_PCT];
	return (profile);
}
