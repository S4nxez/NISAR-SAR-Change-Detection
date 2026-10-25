/* ************************************************************************** */
/*                                                                            */
/*                                                      :::      ::::::::   */
/*   ui_cost.c                                          :+:      :+:    :+:   */
/*                                                  +:+ +:+         +:+     */
/*   By: sanxez <desanchezmunoz02@gmail.com>        +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2026/10/25 12:00:00 by sanxez            #+#    #+#             */
/*   Updated: 2026/10/25 12:00:00 by sanxez           ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#include "ui.h"
#include "format.h"

static void	draw_memory(WINDOW *win, t_tree tree, t_cost cost, int margin)
{
	char	a[FMT_LEN];
	char	b[FMT_LEN];
	char	c[FMT_LEN];

	fmt_count(tree.nodes, a, FMT_LEN);
	fmt_count(tree.leaves, b, FMT_LEN);
	fmt_count(tree.voters, c, FMT_LEN);
	ui_textf(win, 1, "Modelos %s  (%s D + %s V)", a, b, c);
	fmt_mib(cost.ram_mib, a, FMT_LEN);
	fmt_mib(cost.required_mib, b, FMT_LEN);
	ui_textf(win, 2, "RAM %s (+%d%%: %s)", a, margin, b);
	ui_bar(win, 3, cost);
	ui_bar_legend(win, 4, cost);
}

static void	draw_cpu(WINDOW *win, t_cost cost, int target_ms)
{
	char	disk[FMT_LEN];
	char	cpu[FMT_LEN];
	char	latency[FMT_LEN];
	char	vcpus[FMT_LEN];

	fmt_mib(cost.disk_mib, disk, FMT_LEN);
	fmt_time_us(cost.cpu_us, cpu, FMT_LEN);
	fmt_time_us(container_latency_us(cost), latency, FMT_LEN);
	fmt_count(cost.vcpus, vcpus, FMT_LEN);
	ui_textf(win, 5, "Disco %s  CPU %s/inf", disk, cpu);
	ui_textf(win, 6, "vCPU %s (<%d ms)  latencia %s",
		vcpus, target_ms, latency);
}

static void	draw_container(WINDOW *win, t_cost cost)
{
	const t_tier	*tier;
	char			count[FMT_LEN];

	if (cost.tier == TIER_CLUSTER)
	{
		tier = container_tier(TIER_COUNT - 1);
		fmt_count(cost.replicas, count, FMT_LEN);
		wattron(win, COLOR_PAIR(CP_WARN) | A_BOLD);
		ui_textf(win, 7, "Cluster %s x %s %d vCPU/%d GiB",
			count, tier->name, tier->vcpus, tier->ram_gib);
		wattroff(win, COLOR_PAIR(CP_WARN) | A_BOLD);
		ui_text(win, 8, 2, "Reparte subarboles entre nodos");
		return ;
	}
	tier = container_tier(cost.tier);
	wattron(win, COLOR_PAIR(CP_LEAF) | A_BOLD);
	ui_textf(win, 7, "Contenedor %s %d vCPU/%d GiB",
		tier->name, tier->vcpus, tier->ram_gib);
	wattroff(win, COLOR_PAIR(CP_LEAF) | A_BOLD);
	ui_textf(win, 8, "docker run --cpus=%d --memory=%dg",
		tier->vcpus, tier->ram_gib);
}

static void	draw_profile(WINDOW *win, t_profile profile)
{
	wattron(win, A_DIM);
	ui_text(win, 10, 2, "Perfil (comando 'profile'):");
	ui_textf(win, 11, "  decisor %d MiB, %d us/inferencia",
		profile.leaf_mib, profile.leaf_us);
	ui_textf(win, 12, "  votante %d MiB, %d us/voto",
		profile.voter_mib, profile.voter_us);
	ui_textf(win, 13, "  runtime TF %d MiB, pesos %d%% RAM",
		profile.runtime_mib, profile.disk_pct);
	wattroff(win, A_DIM);
}

void	draw_cost(WINDOW *win, t_app *app)
{
	t_profile	profile;
	t_tree		tree;
	t_cost		cost;

	profile = field_profile(app->values);
	tree = app_tree(app);
	cost = cost_estimate(tree, profile);
	ui_frame(win, "[3] RECURSOS / CONTENEDOR", app->focus == PANEL_COST);
	draw_memory(win, tree, cost, profile.headroom_pct);
	draw_cpu(win, cost, profile.target_ms);
	draw_container(win, cost);
	draw_profile(win, profile);
}
