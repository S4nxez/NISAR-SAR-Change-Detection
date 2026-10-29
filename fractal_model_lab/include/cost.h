/* ************************************************************************** */
/*                                                                            */
/*                                                      :::      ::::::::   */
/*   cost.h                                             :+:      :+:    :+:   */
/*                                                  +:+ +:+         +:+     */
/*   By: sanxez <desanchezmunoz02@gmail.com>        +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2026/10/25 12:00:00 by sanxez            #+#    #+#             */
/*   Updated: 2026/10/29 02:00:00 by sanxez           ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#ifndef COST_H
# define COST_H

# include "tree.h"

# define TIER_CLUSTER -1
# define TIER_COUNT 8

typedef struct s_profile
{
	int	runtime_mib;
	int	leaf_mib;
	int	voter_mib;
	int	disk_pct;
	int	leaf_us;
	int	voter_us;
	int	target_ms;
	int	headroom_pct;
	int	vcpu_cents;
	int	gib_cents;
	int	leaf_recall;
	int	leaf_spec;
	int	positive_pct;
	int	corr_pct;
}	t_profile;

typedef struct s_tier
{
	const char	*name;
	int			vcpus;
	int			ram_gib;
}	t_tier;

typedef struct s_cost
{
	t_u64	leaf_mib;
	t_u64	voter_mib;
	t_u64	runtime_mib;
	t_u64	ram_mib;
	t_u64	required_mib;
	t_u64	disk_mib;
	t_u64	cpu_us;
	t_u64	path_us;
	t_u64	vcpus;
	t_u64	replicas;
	t_u64	month_eur;
	int		tier;
}	t_cost;

t_cost			cost_estimate(t_tree tree, t_profile profile);
const t_tier	*container_tier(int index);
int				container_pick(t_cost *cost);
t_u64			container_latency_us(t_cost cost);

#endif
