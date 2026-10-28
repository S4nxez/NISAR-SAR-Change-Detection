/* ************************************************************************** */
/*                                                                            */
/*                                                      :::      ::::::::   */
/*   cli_json.c                                         :+:      :+:    :+:   */
/*                                                  +:+ +:+         +:+     */
/*   By: sanxez <desanchezmunoz02@gmail.com>        +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2026/10/28 21:00:00 by sanxez            #+#    #+#             */
/*   Updated: 2026/10/28 21:00:00 by sanxez           ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#include "cli.h"

static void	json_fields(t_app *app, const char *key, int first, int last)
{
	int	id;

	printf("  \"%s\": {", key);
	id = first;
	while (id < last)
	{
		if (id > first)
			printf(", ");
		printf("\"%s\": %d", field_get(id)->name, app->values[id]);
		id++;
	}
	printf("},\n");
}

static void	json_resources(t_cost cost)
{
	printf("  \"resources\": {\"leaves_mib\": %llu, \"voters_mib\": %llu, "
		"\"runtime_mib\": %llu,\n", cost.leaf_mib, cost.voter_mib,
		cost.runtime_mib);
	printf("    \"ram_mib\": %llu, \"required_mib\": %llu, "
		"\"disk_mib\": %llu,\n", cost.ram_mib, cost.required_mib,
		cost.disk_mib);
	printf("    \"cpu_us\": %llu, \"path_us\": %llu, \"vcpus\": %llu, "
		"\"latency_us\": %llu},\n", cost.cpu_us, cost.path_us, cost.vcpus,
		container_latency_us(cost));
}

static void	json_container(t_cost cost)
{
	const t_tier	*tier;

	tier = container_tier(cost.tier);
	if (cost.tier == TIER_CLUSTER)
		tier = container_tier(TIER_COUNT - 1);
	printf("  \"container\": {\"tier\": \"%s\", \"vcpus\": %d, "
		"\"ram_gib\": %d, \"replicas\": %llu, \"cluster\": %s}\n",
		tier->name, tier->vcpus, tier->ram_gib, cost.replicas,
		cli_json_bool(cost.tier == TIER_CLUSTER));
}

void	cli_json(t_app *app)
{
	t_cost	cost;

	cost = cost_estimate(app_tree(app), field_profile(app->values));
	printf("{\n");
	json_fields(app, "params", 0, FRACTAL_FIELDS);
	json_fields(app, "profile", FRACTAL_FIELDS, FIELD_COUNT);
	cli_json_tree(app);
	json_resources(cost);
	json_container(cost);
	printf("}\n");
}
