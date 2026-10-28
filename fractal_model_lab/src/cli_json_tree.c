/* ************************************************************************** */
/*                                                                            */
/*                                                      :::      ::::::::   */
/*   cli_json_tree.c                                    :+:      :+:    :+:   */
/*                                                  +:+ +:+         +:+     */
/*   By: sanxez <desanchezmunoz02@gmail.com>        +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2026/10/28 21:00:00 by sanxez            #+#    #+#             */
/*   Updated: 2026/10/28 21:00:00 by sanxez           ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#include "cli.h"

const char	*cli_json_bool(int value)
{
	if (value)
		return ("true");
	return ("false");
}

static void	json_level(t_params params, int level, const char *separator)
{
	const char	*role;

	role = "voter";
	if (tree_is_leaf(params, level))
		role = "leaf";
	printf("      {\"level\": %d, \"nodes\": %llu, \"role\": \"%s\", "
		"\"copy\": %d, \"copy_root\": %s}%s\n", level + 1,
		tree_level_nodes(params, level), role,
		tree_iteration(params, level) + 1,
		cli_json_bool(tree_is_copy_root(params, level)), separator);
}

void	cli_json_tree(t_app *app)
{
	t_params	params;
	t_tree		tree;
	int			level;

	params = app_params(app);
	tree = tree_build(params);
	printf("  \"tree\": {\"total_levels\": %d, \"nodes\": %llu, "
		"\"leaves\": %llu, \"voters\": %llu, \"saturated\": %s,\n",
		tree.total_levels, tree.nodes, tree.leaves, tree.voters,
		cli_json_bool(tree.saturated));
	printf("    \"levels\": [\n");
	level = 0;
	while (level + 1 < tree.total_levels)
		json_level(params, level++, ",");
	json_level(params, level, "");
	printf("    ]},\n");
}
