/* ************************************************************************** */
/*                                                                            */
/*                                                      :::      ::::::::   */
/*   container.c                                        :+:      :+:    :+:   */
/*                                                  +:+ +:+         +:+     */
/*   By: sanxez <desanchezmunoz02@gmail.com>        +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2026/10/25 12:00:00 by sanxez            #+#    #+#             */
/*   Updated: 2026/10/25 12:00:00 by sanxez           ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#include "cost.h"

const t_tier	*container_tier(int index)
{
	static const t_tier	tiers[TIER_COUNT] = {
	{"micro", 1, 1},
	{"small", 2, 4},
	{"medium", 4, 8},
	{"large", 8, 16},
	{"xlarge", 16, 32},
	{"2xlarge", 32, 64},
	{"4xlarge", 64, 128},
	{"8xlarge", 96, 384}
	};

	if (index < 0 || index >= TIER_COUNT)
		return (0);
	return (&tiers[index]);
}

static int	tier_fits(const t_tier *tier, t_cost *cost)
{
	t_u64	ram_mib;

	ram_mib = (t_u64)tier->ram_gib * 1024;
	return ((t_u64)tier->vcpus >= cost->vcpus
		&& ram_mib >= cost->required_mib);
}

int	container_pick(t_cost *cost)
{
	const t_tier	*largest;
	t_u64			by_ram;
	t_u64			by_cpu;
	int				index;

	index = 0;
	cost->replicas = 1;
	while (index < TIER_COUNT)
	{
		if (tier_fits(container_tier(index), cost))
			return (index);
		index++;
	}
	largest = container_tier(TIER_COUNT - 1);
	by_ram = ceil_div(cost->required_mib, (t_u64)largest->ram_gib * 1024);
	by_cpu = ceil_div(cost->vcpus, (t_u64)largest->vcpus);
	cost->replicas = by_ram;
	if (by_cpu > by_ram)
		cost->replicas = by_cpu;
	return (TIER_CLUSTER);
}

t_u64	container_latency_us(t_cost cost)
{
	const t_tier	*tier;
	t_u64			cores;
	t_u64			latency;

	tier = container_tier(cost.tier);
	if (!tier)
		tier = container_tier(TIER_COUNT - 1);
	cores = sat_mul((t_u64)tier->vcpus, cost.replicas);
	latency = ceil_div(cost.cpu_us, cores);
	if (latency < cost.path_us)
		latency = cost.path_us;
	return (latency);
}
