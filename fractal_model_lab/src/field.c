/* ************************************************************************** */
/*                                                                            */
/*                                                      :::      ::::::::   */
/*   field.c                                            :+:      :+:    :+:   */
/*                                                  +:+ +:+         +:+     */
/*   By: sanxez <desanchezmunoz02@gmail.com>        +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2026/10/25 12:00:00 by sanxez            #+#    #+#             */
/*   Updated: 2026/10/29 02:00:00 by sanxez           ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#include <string.h>
#include "field.h"

static const t_field	g_fields[FIELD_COUNT] = {
{"levels", "niveles", "Niveles", 1, 12, 3},
{"depth", "profundidad", "Profundidad", 1, 12, 3},
{"exponent", "exponencial", "Exponencial", 1, 5, 2},
{"budget", "presupuesto", "Presupuesto", 0, 10000000, 200},
{"accuracy", "exactitud", "Accuracy", 0, 100, 90},
{"precision", "precision", "Precision", 0, 100, 80},
{"recall", "sensibilidad", "Recall", 0, 100, 80},
{"runtime_mib", "runtime", "Runtime TF (MiB)", 0, 65536, 512},
{"leaf_mib", "hoja_mib", "RAM decisor (MiB)", 1, 65536, 48},
{"voter_mib", "voto_mib", "RAM votante (MiB)", 1, 65536, 6},
{"disk_pct", "disco_pct", "Pesos en disco (%RAM)", 0, 1000, 40},
{"leaf_us", "hoja_us", "CPU decisor (us)", 1, 100000000, 5000},
{"voter_us", "voto_us", "CPU votante (us)", 1, 100000000, 200},
{"target_ms", "objetivo_ms", "Latencia objetivo (ms)", 1, 600000, 250},
{"headroom_pct", "margen", "Margen RAM (%)", 0, 500, 25},
{"vcpu_cents", "precio_vcpu", "Precio vCPU (cent/mes)", 0, 10000000, 2700},
{"gib_cents", "precio_gib", "Precio GiB (cent/mes)", 0, 10000000, 300},
{"leaf_recall", "hoja_recall", "Recall decisor (%)", 0, 100, 80},
{"leaf_spec", "hoja_espec", "Especificidad decisor (%)", 0, 100, 90},
{"positive_pct", "positivos", "Muestras positivas (%)", 1, 99, 10},
{"corr_pct", "correlacion", "Correlacion de errores (%)", 0, 100, 50}
};

const t_field	*field_get(int id)
{
	if (id < 0 || id >= FIELD_COUNT)
		return (0);
	return (&g_fields[id]);
}

int	field_find(const char *name)
{
	const t_field	*field;
	int				id;

	id = 0;
	while (name && id < FIELD_COUNT)
	{
		field = field_get(id);
		if (!strcmp(name, field->name) || !strcmp(name, field->alias))
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
	profile.vcpu_cents = values[F_VCPU_CENTS];
	profile.gib_cents = values[F_GIB_CENTS];
	profile.leaf_recall = values[F_LEAF_RECALL];
	profile.leaf_spec = values[F_LEAF_SPEC];
	profile.positive_pct = values[F_POSITIVE_PCT];
	profile.corr_pct = values[F_CORR_PCT];
	return (profile);
}
