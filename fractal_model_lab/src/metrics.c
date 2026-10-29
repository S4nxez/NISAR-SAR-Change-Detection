/* ************************************************************************** */
/*                                                                            */
/*                                                      :::      ::::::::   */
/*   metrics.c                                          :+:      :+:    :+:   */
/*                                                  +:+ +:+         +:+     */
/*   By: sanxez <desanchezmunoz02@gmail.com>        +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2026/10/29 02:00:00 by sanxez            #+#    #+#             */
/*   Updated: 2026/10/29 02:00:00 by sanxez           ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#include "metrics.h"

static double	binomial(int voters, int right_votes, double right)
{
	double	term;
	int		i;

	term = 1.0;
	i = 0;
	while (i < right_votes)
	{
		term = term * (voters - i) / (i + 1) * right;
		i++;
	}
	while (i < voters)
	{
		term *= 1.0 - right;
		i++;
	}
	return (term);
}

double	metrics_vote(double right, int voters)
{
	double	sum;
	int		votes;

	if (voters < 1)
		return (right);
	sum = 0.0;
	votes = voters / 2 + 1;
	while (votes <= voters)
	{
		sum += binomial(voters, votes, right);
		votes++;
	}
	if (voters % 2 == 0)
		sum += binomial(voters, voters / 2, right) / 2.0;
	return (sum);
}

double	metrics_rate(double leaf, int depth, int levels, double corr)
{
	double	rate;

	rate = leaf;
	while (levels > 0)
	{
		rate = corr * rate + (1.0 - corr) * metrics_vote(rate, depth);
		levels--;
	}
	return (rate);
}

t_metrics	metrics_estimate(t_params params, t_profile profile)
{
	t_metrics	metrics;
	double		corr;
	double		positive;
	double		false_pos;
	int			levels;

	levels = tree_total_levels(params) - 1;
	corr = profile.corr_pct / 100.0;
	positive = profile.positive_pct / 100.0;
	metrics.recall = metrics_rate(profile.leaf_recall / 100.0,
			params.depth, levels, corr);
	false_pos = metrics_rate((100 - profile.leaf_spec) / 100.0,
			params.depth, levels, corr);
	metrics.specificity = 1.0 - false_pos;
	metrics.accuracy = positive * metrics.recall
		+ (1.0 - positive) * metrics.specificity;
	metrics.precision = 0.0;
	if (positive * metrics.recall + (1.0 - positive) * false_pos > 0.0)
		metrics.precision = positive * metrics.recall
			/ (positive * metrics.recall + (1.0 - positive) * false_pos);
	return (metrics);
}

int	metrics_permil(double rate)
{
	if (!(rate > 0.0))
		return (0);
	if (rate >= 1.0)
		return (1000);
	return ((int)(rate * 1000.0 + 0.5 + 1e-9));
}
