/* ************************************************************************** */
/*                                                                            */
/*                                                      :::      ::::::::   */
/*   request.c                                          :+:      :+:    :+:   */
/*                                                  +:+ +:+         +:+     */
/*   By: sanxez <desanchezmunoz02@gmail.com>        +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2026/10/29 02:00:00 by sanxez            #+#    #+#             */
/*   Updated: 2026/10/29 02:00:00 by sanxez           ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#include <stdio.h>
#include "field.h"
#include "format.h"
#include "metrics.h"

t_request	field_request(const int *values)
{
	t_request	request;

	request.budget = values[F_BUDGET];
	request.accuracy = values[F_ACCURACY];
	request.precision = values[F_PRECISION];
	request.recall = values[F_RECALL];
	return (request);
}

static int	below(double rate, int requested_pct)
{
	return (metrics_permil(rate) < requested_pct * 10);
}

int	request_unmet(t_request request, t_metrics metrics, t_cost cost)
{
	int	unmet;

	unmet = 0;
	if (request.budget > 0 && cost.month_eur > (t_u64)request.budget)
		unmet |= REQ_BUDGET;
	if (below(metrics.accuracy, request.accuracy))
		unmet |= REQ_ACCURACY;
	if (below(metrics.precision, request.precision))
		unmet |= REQ_PRECISION;
	if (below(metrics.recall, request.recall))
		unmet |= REQ_RECALL;
	return (unmet);
}

t_check	request_check(const int *values)
{
	t_check		check;
	t_params	params;
	t_profile	profile;

	params = field_params(values);
	profile = field_profile(values);
	check.cost = cost_estimate(tree_build(params), profile);
	check.metrics = metrics_estimate(params, profile);
	check.request = field_request(values);
	check.unmet = request_unmet(check.request, check.metrics, check.cost);
	return (check);
}

void	request_estimate(t_check check, int id, char *buf, size_t size)
{
	int	permil;

	if (id == F_BUDGET)
	{
		fmt_count(check.cost.month_eur, buf, size);
		return ;
	}
	permil = metrics_permil(check.metrics.accuracy);
	if (id == F_PRECISION)
		permil = metrics_permil(check.metrics.precision);
	else if (id == F_RECALL)
		permil = metrics_permil(check.metrics.recall);
	snprintf(buf, size, "%d.%d%%", permil / 10, permil % 10);
}
