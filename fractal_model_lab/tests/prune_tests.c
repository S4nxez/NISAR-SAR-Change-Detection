/*
** Unit tests of the random shutdown of models of fractal_lab (src/prune*.c):
** the random, random_pct and seed fields, the rules of the shutdown (the root
** and the last active child of a node are never shut down, a shut down model
** disables its whole branch, no more than random_pct% of the models are shut
** down and no other model could still be), its counts and its
** reproducibility. They link only the calculation objects (no ncurses).
**
** Usage: make unit (builds and runs it). Exits 1 if any check fails.
** Every built shutdown is checked by verify(), which recomputes everything
** from the state array without the prune functions.
*/

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "field.h"
#include "prune.h"

#define DETAIL_LEN 160

static int	g_checks;
static int	g_failures;

static void	check(int ok, const char *name, const char *detail)
{
	const char	*actions;

	g_checks++;
	if (ok)
	{
		printf("[ OK ] %s\n", name);
		return ;
	}
	g_failures++;
	printf("[FAIL] %s\n", name);
	if (detail && *detail)
		printf("       %s\n", detail);
	actions = getenv("GITHUB_ACTIONS");
	if (actions && !strcmp(actions, "true"))
		printf("::error title=Model lab unit test::%s\n", name);
}

static void	check_u64(const char *name, t_u64 got, t_u64 want)
{
	char	detail[DETAIL_LEN];

	snprintf(detail, sizeof(detail), "got %llu, expected %llu", got, want);
	check(got == want, name, detail);
}

static t_params	schema(int levels, int depth, int exponent)
{
	int	values[FIELD_COUNT];

	field_reset(values);
	values[F_LEVELS] = levels;
	values[F_DEPTH] = depth;
	values[F_EXPONENT] = exponent;
	return (field_params(values));
}

static t_params	random_schema(t_params params, int pct, int seed)
{
	params.random = 1;
	params.random_pct = pct;
	params.seed = seed;
	return (params);
}

static t_u64	fnv1a(const unsigned char *data, t_u64 size)
{
	t_u64	hash;
	t_u64	i;

	hash = 14695981039346656037ULL;
	for (i = 0; i < size; i++)
		hash = (hash ^ data[i]) * 1099511628211ULL;
	return (hash);
}

static int	fail(char *why, const char *format, t_u64 a, t_u64 b)
{
	snprintf(why, DETAIL_LEN, format, a, b);
	return (0);
}

/* Node states and links: every rule of the shutdown, node by node. */
static int	verify_nodes(const t_prune *p, char *why)
{
	t_u64	depth;
	t_u64	i;
	t_u64	child;
	int		state;
	int		parent;
	int		active_child;

	depth = (t_u64)p->params.depth;
	if (p->state[0] != NODE_ON)
		return (fail(why, "the root is not active (%llu/%llu)", 0, p->nodes));
	for (i = 1; i < p->nodes; i++)
	{
		state = p->state[i];
		parent = p->state[(i - 1) / depth];
		if (state != NODE_ON && state != NODE_CUT && state != NODE_OFF)
			return (fail(why, "node %llu has state %llu", i, state));
		if (parent != NODE_ON && state != NODE_OFF)
			return (fail(why, "node %llu is %llu under a shut down model",
					i, state));
		if (parent == NODE_ON && state == NODE_OFF)
			return (fail(why, "node %llu disabled without a shut down "
					"model above (%llu)", i, 0));
	}
	for (i = 0; i < p->nodes && i * depth + 1 < p->nodes; i++)
	{
		active_child = 0;
		for (child = i * depth + 1; child <= i * depth + depth; child++)
			active_child |= (p->state[child] == NODE_ON);
		if (p->state[i] == NODE_ON && !active_child)
			return (fail(why, "active voter %llu has no active child "
					"(depth %llu)", i, depth));
	}
	return (1);
}

/* Counts kept by the prune against the ones of the state array. */
static int	verify_counts(const t_prune *p, char *why)
{
	t_tree	full;
	t_tree	tree;
	t_u64	first;
	t_u64	i;
	t_u64	active;
	t_u64	removed;
	t_u64	cuts;
	int		level;

	full = tree_build(p->params);
	if (p->nodes != full.nodes || p->levels != full.total_levels)
		return (fail(why, "size %llu, expected %llu", p->nodes, full.nodes));
	removed = 0;
	cuts = 0;
	first = 0;
	for (level = 0; level < p->levels; level++)
	{
		if (p->offset[level] != first)
			return (fail(why, "level %llu starts at %llu", level,
					p->offset[level]));
		active = 0;
		for (i = first; i < first + tree_level_nodes(p->params, level); i++)
		{
			active += (p->state[i] == NODE_ON);
			removed += (p->state[i] != NODE_ON);
			cuts += (p->state[i] == NODE_CUT);
			if (prune_state(p, level, i - first) != p->state[i])
				return (fail(why, "prune_state of node %llu (level %llu)",
						i, level));
		}
		if (p->active[level] != active
			|| prune_level_nodes(p, level) != active)
			return (fail(why, "level %llu has %llu active models", level,
					active));
		first = i;
	}
	if (removed != p->removed || cuts != p->cuts)
		return (fail(why, "%llu models shut down, %llu cuts", removed, cuts));
	tree = prune_tree(p);
	if (tree.total_levels != full.total_levels
		|| tree.nodes != p->nodes - removed
		|| tree.leaves != p->active[p->levels - 1]
		|| tree.voters != tree.nodes - tree.leaves)
		return (fail(why, "prune_tree: %llu nodes, %llu leaves",
				tree.nodes, tree.leaves));
	return (1);
}

/* No more than random_pct%, and nothing else could be shut down within it. */
static int	verify_target(const t_prune *p, char *why)
{
	t_u64	*branch;
	t_u64	depth;
	t_u64	i;
	t_u64	child;
	t_u64	left;
	int		ok;

	if (p->target != (p->nodes * (t_u64)p->params.random_pct + 50) / 100)
		return (fail(why, "target %llu for %llu nodes", p->target, p->nodes));
	if (p->removed > p->target)
		return (fail(why, "%llu shut down, over the target %llu",
				p->removed, p->target));
	depth = (t_u64)p->params.depth;
	branch = calloc(p->nodes, sizeof(*branch));
	if (!branch)
		return (fail(why, "out of memory (%llu/%llu)", 0, 0));
	i = p->nodes;
	while (i-- > 0)
	{
		branch[i] = (p->state[i] == NODE_ON);
		for (child = i * depth + 1; i * depth + 1 < p->nodes
			&& child <= i * depth + depth; child++)
			branch[i] += branch[child];
	}
	ok = 1;
	left = p->target - p->removed;
	for (i = 1; ok && left > 0 && i < p->nodes; i++)
	{
		if (p->state[i] != NODE_ON || branch[i] > left)
			continue ;
		for (child = (i - 1) / depth * depth + 1;
			child <= (i - 1) / depth * depth + depth; child++)
			if (child != i && p->state[child] == NODE_ON)
				ok = fail(why, "node %llu could still be shut down "
						"(%llu left)", i, left);
	}
	free(branch);
	return (ok);
}

static int	verify(const t_prune *p, char *why)
{
	why[0] = '\0';
	if (p->status != PRUNE_DONE)
		return (fail(why, "status %llu (%llu nodes)", p->status, p->nodes));
	return (verify_nodes(p, why) && verify_counts(p, why)
		&& verify_target(p, why));
}

static void	test_fields(void)
{
	const t_field	*field;
	int				values[FIELD_COUNT];
	t_params		params;
	int				id;
	int				ok;

	ok = 1;
	for (id = 0; id < FIELD_COUNT; id++)
	{
		field = field_get(id);
		ok &= (field_find(field->name) == id && field_find(field->alias) == id
				&& field->initial >= field->min
				&& field->initial <= field->max);
	}
	check(ok, "fields: every name and alias finds its own field, defaults "
		"within range", "");
	check(field_find("random") == F_RANDOM
		&& field_find("aleatorio") == F_RANDOM
		&& field_find("random_pct") == F_RANDOM_PCT
		&& field_find("apagado_pct") == F_RANDOM_PCT
		&& field_find("seed") == F_SEED && field_find("semilla") == F_SEED,
		"fields: random/aleatorio, random_pct/apagado_pct, seed/semilla", "");
	check(field_get(F_RANDOM)->initial == 0 && field_get(F_RANDOM)->min == 0
		&& field_get(F_RANDOM)->max == 1,
		"fields: random is a 0/1 flag, off by default", "");
	check(field_get(F_RANDOM_PCT)->min == 0
		&& field_get(F_RANDOM_PCT)->max == 100
		&& field_get(F_RANDOM_PCT)->initial == 20,
		"fields: random_pct is a percentage (0-100, 20 by default)", "");
	check(field_get(F_SEED)->min == 0 && field_get(F_SEED)->max == 9999,
		"fields: seed 0-9999", "");
	check(F_RANDOM == F_EXPONENT + 1 && F_SEED + 1 == FRACTAL_FIELDS,
		"fields: the random fields are schema fields (panel 2, not profile)",
		"");
	field_reset(values);
	values[F_RANDOM] = 1;
	values[F_RANDOM_PCT] = 37;
	values[F_SEED] = 4242;
	params = field_params(values);
	check(params.random == 1 && params.random_pct == 37 && params.seed == 4242
		&& params.levels == 3 && params.depth == 3 && params.exponent == 2,
		"fields: field_params copies random, random_pct and seed", "");
}

static void	test_off(void)
{
	t_prune		prune;
	t_params	params;
	t_tree		tree;
	t_tree		full;
	int			level;
	int			ok;

	memset(&prune, 0, sizeof(prune));
	params = schema(3, 3, 2);
	check(prune_update(&prune, params) == PRUNE_OFF && prune.state == 0,
		"off: random 0 shuts nothing down and allocates nothing", "");
	tree = prune_tree(&prune);
	full = tree_build(params);
	check(tree.nodes == full.nodes && tree.leaves == full.leaves
		&& tree.voters == full.voters
		&& tree.total_levels == full.total_levels && tree.nodes == 121,
		"off: prune_tree is the full tree (121 models)", "");
	ok = 1;
	for (level = 0; level < full.total_levels; level++)
		ok &= (prune_level_nodes(&prune, level)
				== tree_level_nodes(params, level)
				&& prune_state(&prune, level, 0) == NODE_ON);
	check(ok, "off: every level keeps all its models", "");
	prune_update(&prune, random_schema(params, 20, 1));
	prune_update(&prune, params);
	check(prune.status == PRUNE_OFF && prune.state == 0 && prune.removed == 0,
		"off: turning random off again frees the shutdown", "");
	prune_clear(&prune);
}

static void	test_default(void)
{
	t_prune	prune;
	t_tree	tree;
	char	why[DETAIL_LEN];

	memset(&prune, 0, sizeof(prune));
	check(prune_update(&prune, random_schema(schema(3, 3, 2), 20, 1))
		== PRUNE_DONE, "default schema: random 1 applies", "");
	check(verify(&prune, why), "default schema: follows the rules", why);
	check_u64("default schema: 20% of 121 models is 24", prune.target, 24);
	check_u64("default schema: exactly 24 models shut down", prune.removed,
		24);
	tree = prune_tree(&prune);
	check_u64("default schema: 97 models left", tree.nodes, 97);
	check(tree.total_levels == 5 && prune.active[0] == 1,
		"default schema: keeps its 5 levels and the root", "");
	check_u64("default schema, seed 1: 60 decision models left", tree.leaves,
		60);
	check_u64("default schema, seed 1: 15 shutdown points", prune.cuts, 15);
	prune_clear(&prune);
}

static t_u64	state_hash(t_params params, int pct, int seed)
{
	t_prune	prune;
	t_u64	hash;

	memset(&prune, 0, sizeof(prune));
	if (prune_update(&prune, random_schema(params, pct, seed)) != PRUNE_DONE)
		return (0);
	hash = fnv1a(prune.state, prune.nodes);
	prune_clear(&prune);
	return (hash);
}

static void	test_reproducible(void)
{
	t_prune	a;
	t_prune	b;

	memset(&a, 0, sizeof(a));
	memset(&b, 0, sizeof(b));
	prune_update(&a, random_schema(schema(4, 4, 2), 35, 123));
	prune_update(&b, random_schema(schema(4, 4, 2), 35, 123));
	check(a.status == PRUNE_DONE && b.status == PRUNE_DONE
		&& a.nodes == b.nodes && !memcmp(a.state, b.state, a.nodes)
		&& a.removed == b.removed && a.cuts == b.cuts,
		"reproducible: the same parameters give the same schema", "");
	prune_clear(&a);
	prune_clear(&b);
	check(state_hash(schema(3, 3, 2), 20, 1)
		!= state_hash(schema(3, 3, 2), 20, 2),
		"reproducible: another seed gives another schema", "");
	check_u64("reproducible: schema of L3 D3 E2 20% seed 1 on any machine",
		state_hash(schema(3, 3, 2), 20, 1), 3714512305258621196ULL);
	check_u64("reproducible: schema of L4 D4 E2 35% seed 123 on any machine",
		state_hash(schema(4, 4, 2), 35, 123), 6728598119391171540ULL);
	check_u64("reproducible: schema of L3 D12 E2 50% seed 9999 on any "
		"machine", state_hash(schema(3, 12, 2), 50, 9999),
		528952390124203178ULL);
}

static void	sweep_one(t_params params, int pct, int seed, int *stats)
{
	t_prune	prune;
	char	why[DETAIL_LEN];
	t_tree	tree;
	int		level;
	int		chain;

	memset(&prune, 0, sizeof(prune));
	prune_update(&prune, random_schema(params, pct, seed));
	stats[0]++;
	if (!verify(&prune, why))
	{
		if (stats[1]++ == 0)
			printf("       L%d D%d E%d %d%% seed %d: %s\n", params.levels,
				params.depth, params.exponent, pct, seed, why);
		prune_clear(&prune);
		return ;
	}
	tree = tree_build(params);
	if (params.depth >= 2 && pct <= 24 && prune.removed != prune.target)
		stats[2]++;
	chain = 1;
	for (level = 0; level < tree.total_levels; level++)
		chain &= (prune.active[level] == 1);
	if (params.depth >= 2 && pct == 100
		&& (prune.removed != tree.nodes - (t_u64)tree.total_levels || !chain))
		stats[3]++;
	if (params.depth == 1 && prune.removed != 0)
		stats[4]++;
	prune_clear(&prune);
}

static void	test_sweep(void)
{
	static const int	pcts[] = {0, 1, 5, 10, 20, 24, 25, 33, 50, 66, 75,
		90, 99, 100};
	static const int	seeds[] = {0, 1, 2, 42, 9999};
	int					stats[5];
	char				detail[DETAIL_LEN];
	char				name[DETAIL_LEN];
	int					shape[3];
	size_t				p;
	size_t				s;

	memset(stats, 0, sizeof(stats));
	for (shape[0] = 1; shape[0] <= 5; shape[0]++)
		for (shape[1] = 1; shape[1] <= 6; shape[1]++)
			for (shape[2] = 1; shape[2] <= 3; shape[2]++)
			{
				if (tree_build(schema(shape[0], shape[1], shape[2])).nodes
					> 20000)
					continue ;
				for (p = 0; p < sizeof(pcts) / sizeof(*pcts); p++)
					for (s = 0; s < sizeof(seeds) / sizeof(*seeds); s++)
						sweep_one(schema(shape[0], shape[1], shape[2]),
							pcts[p], seeds[s], stats);
			}
	snprintf(detail, sizeof(detail), "%d of %d schemas break a rule",
		stats[1], stats[0]);
	snprintf(name, sizeof(name), "sweep: %d schemas (levels 1-5, depth 1-6, "
		"exponent 1-3, 14 percentages, 5 seeds) follow the rules", stats[0]);
	check(stats[1] == 0 && stats[0] > 1000, name, detail);
	check(stats[2] == 0, "sweep: up to 24% the exact percentage is always "
		"reached (depth >= 2)", "");
	check(stats[3] == 0, "sweep: 100% leaves a single chain of models from "
		"the root to one decision model", "");
	check(stats[4] == 0, "sweep: with depth 1 (a chain) nothing can be shut "
		"down", "");
}

static void	test_limits(void)
{
	t_prune		prune;
	t_params	params;
	t_tree		tree;
	t_tree		full;
	char		why[DETAIL_LEN];

	memset(&prune, 0, sizeof(prune));
	prune_update(&prune, random_schema(schema(10, 2, 2), 20, 5));
	check(verify(&prune, why) && prune.nodes == 524287
		&& prune.removed == prune.target,
		"limits: 524287 models (19 levels of 2) follow the rules", why);
	prune_update(&prune, random_schema(schema(4, 4, 3), 60, 9));
	check(verify(&prune, why) && prune.nodes == 349525,
		"limits: 349525 models (10 levels of 4) follow the rules", why);
	params = random_schema(schema(6, 4, 2), 20, 1);
	check(prune_update(&prune, params) == PRUNE_TOO_BIG && prune.state == 0,
		"limits: 1398101 models exceed PRUNE_MAX_NODES, nothing applied", "");
	tree = prune_tree(&prune);
	full = tree_build(params);
	check(tree.nodes == full.nodes && tree.leaves == full.leaves
		&& prune_level_nodes(&prune, 5) == tree_level_nodes(params, 5)
		&& prune_state(&prune, 3, 7) == NODE_ON,
		"limits: a schema too big is shown full", "");
	params = random_schema(schema(12, 12, 5), 20, 1);
	check(prune_update(&prune, params) == PRUNE_TOO_BIG
		&& prune_tree(&prune).saturated,
		"limits: a saturated schema (>2^64 models) is too big", "");
	prune_clear(&prune);
	check(prune.state == 0 && prune.status == PRUNE_OFF && !prune.ready,
		"limits: prune_clear frees and resets the shutdown", "");
}

static void	test_edges(void)
{
	t_prune	prune;
	char	why[DETAIL_LEN];

	memset(&prune, 0, sizeof(prune));
	prune_update(&prune, random_schema(schema(1, 3, 2), 100, 1));
	check(verify(&prune, why) && prune.nodes == 1 && prune.removed == 0
		&& prune_tree(&prune).leaves == 1,
		"edges: a single model is never shut down", why);
	prune_update(&prune, random_schema(schema(3, 1, 2), 100, 1));
	check(verify(&prune, why) && prune.nodes == 5 && prune.removed == 0
		&& prune.target == 5, "edges: depth 1 keeps the whole chain", why);
	prune_update(&prune, random_schema(schema(3, 3, 2), 0, 1));
	check(verify(&prune, why) && prune.removed == 0 && prune.cuts == 0,
		"edges: 0% shuts nothing down", why);
	prune_update(&prune, random_schema(schema(2, 12, 1), 100, 3));
	check(verify(&prune, why) && prune.removed == 11
		&& prune.active[1] == 1,
		"edges: 100% of a root with 12 decision models keeps one", why);
	prune_clear(&prune);
}

static void	test_cache(void)
{
	t_prune			prune;
	t_params		params;
	unsigned char	*state;
	unsigned char	copy[121];

	memset(&prune, 0, sizeof(prune));
	params = random_schema(schema(3, 3, 2), 20, 1);
	prune_update(&prune, params);
	state = prune.state;
	memcpy(copy, prune.state, sizeof(copy));
	prune_update(&prune, params);
	check(prune.state == state && !memcmp(copy, prune.state, sizeof(copy)),
		"cache: the same parameters reuse the shutdown", "");
	params.seed = 2;
	prune_update(&prune, params);
	check(prune.status == PRUNE_DONE && memcmp(copy, prune.state,
			sizeof(copy)) != 0,
		"cache: another seed rebuilds it", "");
	params.levels = 4;
	prune_update(&prune, params);
	check(prune.status == PRUNE_DONE && prune.nodes == 1093,
		"cache: another schema rebuilds it", "");
	prune_clear(&prune);
}

int	main(void)
{
	test_fields();
	test_off();
	test_default();
	test_reproducible();
	test_sweep();
	test_limits();
	test_edges();
	test_cache();
	printf("\n%d checks, %d failed\n", g_checks, g_failures);
	return (g_failures != 0);
}
