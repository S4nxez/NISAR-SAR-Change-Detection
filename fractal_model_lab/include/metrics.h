/* ************************************************************************** */
/*                                                                            */
/*                                                      :::      ::::::::   */
/*   metrics.h                                          :+:      :+:    :+:   */
/*                                                  +:+ +:+         +:+     */
/*   By: sanxez <desanchezmunoz02@gmail.com>        +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2026/10/29 02:00:00 by sanxez            #+#    #+#             */
/*   Updated: 2026/10/29 02:00:00 by sanxez           ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#ifndef METRICS_H
# define METRICS_H

# include <stddef.h>
# include "cost.h"

# define REQ_BUDGET 1
# define REQ_ACCURACY 2
# define REQ_PRECISION 4
# define REQ_RECALL 8

typedef struct s_metrics
{
	double	accuracy;
	double	precision;
	double	recall;
	double	specificity;
}	t_metrics;

typedef struct s_request
{
	int	budget;
	int	accuracy;
	int	precision;
	int	recall;
}	t_request;

typedef struct s_check
{
	t_cost		cost;
	t_metrics	metrics;
	t_request	request;
	int			unmet;
}	t_check;

double		metrics_vote(double right, int voters);
double		metrics_rate(double leaf, int depth, int levels, double corr);
t_metrics	metrics_estimate(t_params params, t_profile profile);
int			metrics_permil(double rate);
t_request	field_request(const int *values);
int			request_unmet(t_request request, t_metrics metrics, t_cost cost);
t_check		request_check(const int *values);
void		request_estimate(t_check check, int id, char *buf, size_t size);

#endif
