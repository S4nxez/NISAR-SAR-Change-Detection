/* ************************************************************************** */
/*                                                                            */
/*                                                      :::      ::::::::   */
/*   report.c                                           :+:      :+:    :+:   */
/*                                                  +:+ +:+         +:+     */
/*   By: sanxez <desanchezmunoz02@gmail.com>        +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2026/10/25 12:00:00 by sanxez            #+#    #+#             */
/*   Updated: 2026/10/29 02:00:00 by sanxez           ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#include "app.h"
#include "format.h"

static void	report_resources(t_app *app, t_cost cost)
{
	char	ram[FMT_LEN];
	char	need[FMT_LEN];
	char	disk[FMT_LEN];
	char	cpu[FMT_LEN];

	fmt_mib(cost.ram_mib, ram, FMT_LEN);
	fmt_mib(cost.required_mib, need, FMT_LEN);
	fmt_mib(cost.disk_mib, disk, FMT_LEN);
	fmt_time_us(cost.cpu_us, cpu, FMT_LEN);
	app_logf(app, "RAM %s (con margen %s), disco %s", ram, need, disk);
	fmt_time_us(container_latency_us(cost), ram, FMT_LEN);
	fmt_count(cost.vcpus, need, FMT_LEN);
	app_logf(app, "CPU %s/inferencia -> %s vCPU, latencia %s",
		cpu, need, ram);
}

static void	report_container(t_app *app, t_cost cost)
{
	const t_tier	*tier;
	char			count[FMT_LEN];

	if (cost.tier == TIER_CLUSTER)
	{
		tier = container_tier(TIER_COUNT - 1);
		fmt_count(cost.replicas, count, FMT_LEN);
		app_logf(app, "aviso: no cabe en un contenedor; cluster de %s x %s",
			count, tier->name);
		return ;
	}
	tier = container_tier(cost.tier);
	app_logf(app, "Contenedor: %s (%d vCPU / %d GiB)",
		tier->name, tier->vcpus, tier->ram_gib);
}

void	report_generate(t_app *app)
{
	t_params	params;
	t_tree		tree;
	t_cost		cost;
	char		nodes[FMT_LEN];
	char		leaves[FMT_LEN];

	params = app_params(app);
	tree = tree_build(params);
	cost = cost_estimate(tree, field_profile(app->values));
	fmt_count(tree.nodes, nodes, FMT_LEN);
	fmt_count(tree.leaves, leaves, FMT_LEN);
	app_logf(app, "--- esquema L=%d D=%d E=%d ---",
		params.levels, params.depth, params.exponent);
	app_logf(app, "%d niveles, %s nodos, %s decisores",
		tree.total_levels, nodes, leaves);
	report_resources(app, cost);
	report_container(app, cost);
	report_request(app);
}

void	report_levels(t_app *app)
{
	t_params	params;
	char		count[FMT_LEN];
	int			level;
	int			total;

	params = app_params(app);
	total = tree_total_levels(params);
	app_log(app, "--- nodos por nivel ---");
	level = 0;
	while (level < total)
	{
		fmt_count(tree_level_nodes(params, level), count, FMT_LEN);
		if (tree_is_leaf(params, level))
			app_logf(app, "N%-2d decisores %s", level + 1, count);
		else
			app_logf(app, "N%-2d votantes  %s  (copia %d)", level + 1,
				count, tree_iteration(params, level) + 1);
		level++;
	}
}

void	report_profile(t_app *app)
{
	const t_field	*field;
	int				id;

	app_log(app, "--- perfil de modelo (profile <campo> <n>) ---");
	id = PARAM_FIELDS;
	while (id < FIELD_COUNT)
	{
		field = field_get(id);
		app_logf(app, "%-12s %d  %s", field->name, app->values[id],
			field->label);
		id++;
	}
}
