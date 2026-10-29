/* ************************************************************************** */
/*                                                                            */
/*                                                      :::      ::::::::   */
/*   cost.c                                             :+:      :+:    :+:   */
/*                                                  +:+ +:+         +:+     */
/*   By: sanxez <desanchezmunoz02@gmail.com>        +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2026/10/25 12:00:00 by sanxez            #+#    #+#             */
/*   Updated: 2026/10/29 02:00:00 by sanxez           ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#include "cost.h"

static void	cost_memory(t_cost *cost, t_tree tree, t_profile profile)
{
	t_u64	models_mib;

	cost->leaf_mib = sat_mul(tree.leaves, (t_u64)profile.leaf_mib);
	cost->voter_mib = sat_mul(tree.voters, (t_u64)profile.voter_mib);
	cost->runtime_mib = (t_u64)profile.runtime_mib;
	models_mib = sat_add(cost->leaf_mib, cost->voter_mib);
	cost->ram_mib = sat_add(models_mib, cost->runtime_mib);
	cost->required_mib = sat_add(cost->ram_mib, ceil_div(
				sat_mul(cost->ram_mib, (t_u64)profile.headroom_pct), 100));
	cost->disk_mib = ceil_div(
			sat_mul(models_mib, (t_u64)profile.disk_pct), 100);
}

static void	cost_cpu(t_cost *cost, t_tree tree, t_profile profile)
{
	t_u64	leaf_us;
	t_u64	voter_us;
	t_u64	target_us;

	leaf_us = sat_mul(tree.leaves, (t_u64)profile.leaf_us);
	voter_us = sat_mul(tree.voters, (t_u64)profile.voter_us);
	cost->cpu_us = sat_add(leaf_us, voter_us);
	cost->path_us = sat_add((t_u64)profile.leaf_us,
			sat_mul((t_u64)(tree.total_levels - 1), (t_u64)profile.voter_us));
	target_us = sat_mul((t_u64)profile.target_ms, 1000);
	cost->vcpus = ceil_div(cost->cpu_us, target_us);
	if (cost->vcpus < 1)
		cost->vcpus = 1;
}

static void	cost_month(t_cost *cost, t_profile profile)
{
	const t_tier	*tier;
	t_u64			cents;

	tier = container_tier(cost->tier);
	if (!tier)
		tier = container_tier(TIER_COUNT - 1);
	cents = sat_add(sat_mul((t_u64)tier->vcpus, (t_u64)profile.vcpu_cents),
			sat_mul((t_u64)tier->ram_gib, (t_u64)profile.gib_cents));
	cost->month_eur = ceil_div(sat_mul(cents, cost->replicas), 100);
}

t_cost	cost_estimate(t_tree tree, t_profile profile)
{
	t_cost	cost;

	cost_memory(&cost, tree, profile);
	cost_cpu(&cost, tree, profile);
	cost.tier = container_pick(&cost);
	cost_month(&cost, profile);
	return (cost);
}
