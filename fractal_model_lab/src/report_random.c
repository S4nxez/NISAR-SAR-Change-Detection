/* ************************************************************************** */
/*                                                                            */
/*                                                      :::      ::::::::   */
/*   report_random.c                                    :+:      :+:    :+:   */
/*                                                  +:+ +:+         +:+     */
/*   By: sanxez <desanchezmunoz02@gmail.com>        +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2026/10/29 12:00:00 by sanxez            #+#    #+#             */
/*   Updated: 2026/10/29 12:00:00 by sanxez           ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#include <stdio.h>
#include "app.h"
#include "format.h"

t_prune	*app_prune(t_app *app)
{
	prune_update(&app->prune, app_params(app));
	return (&app->prune);
}

static void	report_short(t_app *app, t_prune *prune)
{
	char	removed[FMT_LEN];
	char	target[FMT_LEN];

	fmt_count(prune->removed, removed, FMT_LEN);
	fmt_count(prune->target, target, FMT_LEN);
	app_logf(app, "aviso: apagados %s de los %s pedidos, ninguna otra rama "
		"cabe sin dejar un votante sin hijos", removed, target);
}

void	report_random(t_app *app)
{
	t_prune	*prune;
	char	removed[FMT_LEN];
	char	nodes[FMT_LEN];
	char	cuts[FMT_LEN];

	prune = app_prune(app);
	fmt_count(PRUNE_MAX_NODES, nodes, FMT_LEN);
	if (prune->status == PRUNE_TOO_BIG)
		app_logf(app, "aviso: aleatorio sin aplicar, el esquema supera %s "
			"nodos", nodes);
	else if (prune->status == PRUNE_NO_MEMORY)
		app_log(app, "aviso: aleatorio sin aplicar, no hay memoria");
	if (prune->status != PRUNE_DONE)
		return ;
	fmt_count(prune->removed, removed, FMT_LEN);
	fmt_count(prune->nodes, nodes, FMT_LEN);
	fmt_count(prune->cuts, cuts, FMT_LEN);
	app_logf(app, "Aleatorio %d%% (semilla %d): %s de %s modelos apagados "
		"(%.1f%%) en %s cortes", prune->params.random_pct,
		prune->params.seed, removed, nodes,
		100.0 * prune->removed / prune->nodes, cuts);
	if (prune->removed < prune->target)
		report_short(app, prune);
}

void	report_level_count(t_app *app, int level, char *buf, size_t size)
{
	t_prune	*prune;
	char	active[FMT_LEN];
	char	full[FMT_LEN];

	prune = app_prune(app);
	fmt_count(prune_level_nodes(prune, level), active, FMT_LEN);
	if (prune->status != PRUNE_DONE)
	{
		snprintf(buf, size, "%s", active);
		return ;
	}
	fmt_count(tree_level_nodes(prune->params, level), full, FMT_LEN);
	snprintf(buf, size, "%s de %s", active, full);
}
