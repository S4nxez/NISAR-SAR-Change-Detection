/* ************************************************************************** */
/*                                                                            */
/*                                                      :::      ::::::::   */
/*   report_request.c                                   :+:      :+:    :+:   */
/*                                                  +:+ +:+         +:+     */
/*   By: sanxez <desanchezmunoz02@gmail.com>        +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2026/10/29 02:00:00 by sanxez            #+#    #+#             */
/*   Updated: 2026/10/29 02:00:00 by sanxez           ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#include "app.h"
#include "format.h"
#include "metrics.h"

static void	report_budget(t_app *app, t_check check)
{
	char	money[FMT_LEN];

	fmt_count(check.cost.month_eur, money, FMT_LEN);
	if (check.request.budget == 0)
		app_logf(app, "Coste %s EUR/mes (sin limite de presupuesto)", money);
	else if (check.unmet & REQ_BUDGET)
		app_logf(app, "aviso: coste %s EUR/mes, supera el presupuesto (%d)",
			money, check.request.budget);
	else
		app_logf(app, "Coste %s EUR/mes, dentro del presupuesto (%d)",
			money, check.request.budget);
}

static void	report_estimates(t_app *app, t_check check)
{
	char	accuracy[FMT_LEN];
	char	precision[FMT_LEN];
	char	recall[FMT_LEN];
	int		specificity;

	request_estimate(check, F_ACCURACY, accuracy, FMT_LEN);
	request_estimate(check, F_PRECISION, precision, FMT_LEN);
	request_estimate(check, F_RECALL, recall, FMT_LEN);
	specificity = metrics_permil(check.metrics.specificity);
	app_logf(app, "Estimado: accuracy %s, precision %s, recall %s "
		"(especificidad %d.%d%%)", accuracy, precision, recall,
		specificity / 10, specificity % 10);
}

static void	report_unmet(t_app *app, t_check check)
{
	char	estimate[FMT_LEN];
	int		id;

	id = F_ACCURACY;
	while (id <= F_RECALL)
	{
		request_estimate(check, id, estimate, FMT_LEN);
		if (check.unmet & (1 << (id - F_BUDGET)))
			app_logf(app, "aviso: %s %s, no llega al %d%% pedido",
				field_get(id)->name, estimate, app->values[id]);
		id++;
	}
}

void	report_request(t_app *app)
{
	t_check	check;

	check = request_check(app->values);
	report_budget(app, check);
	report_estimates(app, check);
	if (check.unmet & (REQ_ACCURACY | REQ_PRECISION | REQ_RECALL))
		report_unmet(app, check);
	else
		app_logf(app, "Cumple las metricas pedidas: accuracy >=%d%%, "
			"precision >=%d%%, recall >=%d%%", check.request.accuracy,
			check.request.precision, check.request.recall);
}

void	report_request_field(t_app *app, int id)
{
	t_check		check;
	char		estimate[FMT_LEN];
	const char	*unit;

	check = request_check(app->values);
	request_estimate(check, id, estimate, FMT_LEN);
	unit = "";
	if (id == F_BUDGET)
		unit = " EUR/mes";
	if (check.unmet & (1 << (id - F_BUDGET)))
		app_logf(app, "aviso: estimado %s%s, no cumple", estimate, unit);
	else
		app_logf(app, "  -> estimado %s%s, cumple", estimate, unit);
}
