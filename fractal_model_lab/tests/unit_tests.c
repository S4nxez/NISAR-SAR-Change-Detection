/*
** Unit tests of the budget and metric estimates of fractal_lab: the field table,
** the majority vote model, the monthly cost and the check of the requested
** budget, accuracy, precision and recall. They link only the calculation
** objects (no ncurses, no terminal).
**
** Usage: make unit (builds and runs it). Exits 1 if any check fails.
** Expected values come from the formulas in README.md (Presupuesto y metricas),
** computed independently with exact binomial coefficients.
*/

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "field.h"
#include "format.h"
#include "metrics.h"

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

static void	check_near(const char *name, double got, double want)
{
	char	detail[128];
	double	diff;

	diff = got - want;
	if (diff < 0)
		diff = -diff;
	snprintf(detail, sizeof(detail), "got %.17g, expected %.17g", got, want);
	check(diff < 1e-12, name, detail);
}

static void	check_u64(const char *name, t_u64 got, t_u64 want)
{
	char	detail[128];

	snprintf(detail, sizeof(detail), "got %llu, expected %llu", got, want);
	check(got == want, name, detail);
}

static void	check_str(const char *name, const char *got, const char *want)
{
	char	detail[128];

	snprintf(detail, sizeof(detail), "got '%s', expected '%s'", got, want);
	check(!strcmp(got, want), name, detail);
}

static void	set_tree(int *values, int levels, int depth, int exponent)
{
	field_reset(values);
	values[F_LEVELS] = levels;
	values[F_DEPTH] = depth;
	values[F_EXPONENT] = exponent;
}

static void	test_fields(void)
{
	const t_field	*field;
	char			detail[128];
	int				id;
	int				ok;

	ok = 1;
	detail[0] = '\0';
	for (id = 0; id < FIELD_COUNT; id++)
	{
		field = field_get(id);
		if (field_find(field->name) != id || field_find(field->alias) != id
			|| field->initial < field->min || field->initial > field->max)
		{
			ok = 0;
			snprintf(detail, sizeof(detail), "field %d (%s)", id, field->name);
		}
	}
	check(ok, "fields: every name and alias finds its own field, defaults "
		"within range", detail);
	check(!field_get(-1) && !field_get(FIELD_COUNT),
		"fields: ids out of range have no field", "");
	check(F_BUDGET == FRACTAL_FIELDS && F_RECALL == PARAM_FIELDS - 1,
		"fields: the requests follow the tree fields (panel 2)", "");
	check(REQ_BUDGET == 1 << (F_BUDGET - F_BUDGET)
		&& REQ_ACCURACY == 1 << (F_ACCURACY - F_BUDGET)
		&& REQ_PRECISION == 1 << (F_PRECISION - F_BUDGET)
		&& REQ_RECALL == 1 << (F_RECALL - F_BUDGET),
		"fields: REQ_* bits follow the order of the request fields", "");
}

static void	test_vote(void)
{
	check_near("vote: 1 voter keeps the rate", metrics_vote(0.8, 1), 0.8);
	check_near("vote: 2 voters keep it (a tie is decided at 50%)",
		metrics_vote(0.8, 2), 0.8);
	check_near("vote: majority of 3 at 80%", metrics_vote(0.8, 3), 0.896);
	check_near("vote: 4 voters at 70%, ties at 50%",
		metrics_vote(0.7, 4), 0.784);
	check_near("vote: majority of 5 at 60%", metrics_vote(0.6, 5), 0.68256);
	check_near("vote: 12 voters at 90%", metrics_vote(0.9, 12),
		0.99970429392);
	check_near("vote: chance stays chance", metrics_vote(0.5, 7), 0.5);
	check_near("vote: always wrong", metrics_vote(0.0, 3), 0.0);
	check_near("vote: always right", metrics_vote(1.0, 4), 1.0);
	check_near("vote: no voters keeps the rate", metrics_vote(0.3, 0), 0.3);
}

static void	test_rate(void)
{
	double	rate;
	double	next;
	int		levels;
	int		ok;

	check_near("rate: no voting levels", metrics_rate(0.8, 3, 0, 0.5), 0.8);
	check_near("rate: fully correlated siblings add nothing",
		metrics_rate(0.8, 3, 4, 1.0), 0.8);
	check_near("rate: independent errors, 2 levels of 3",
		metrics_rate(0.8, 3, 2, 0.0), 0.969801728);
	check_near("rate: 50% correlation, 4 levels of 3",
		metrics_rate(0.8, 3, 4, 0.5), 0.958297355910273);
	ok = 1;
	for (levels = 0; levels < 30; levels++)
	{
		rate = metrics_rate(0.7, 5, levels, 0.3);
		next = metrics_rate(0.7, 5, levels + 1, 0.3);
		if (next < rate || metrics_rate(0.3, 5, levels + 1, 0.3)
			> metrics_rate(0.3, 5, levels, 0.3))
			ok = 0;
	}
	check(ok, "rate: more levels help deciders better than chance and "
		"hurt worse ones", "");
}

static void	test_estimate(void)
{
	int			values[FIELD_COUNT];
	t_metrics	m;

	field_reset(values);
	m = metrics_estimate(field_params(values), field_profile(values));
	check_near("estimate: default recall", m.recall, 0.958297355910273);
	check_near("estimate: default specificity", m.specificity,
		0.9888257867094412);
	check_near("estimate: default accuracy", m.accuracy, 0.9857729436295244);
	check_near("estimate: default precision", m.precision,
		0.9050229316802013);
	check(metrics_permil(m.accuracy) == 986 && metrics_permil(m.precision)
		== 905 && metrics_permil(m.recall) == 958, "estimate: default "
		"rounded to 98.6% / 90.5% / 95.8%", "");
	set_tree(values, 1, 3, 2);
	m = metrics_estimate(field_params(values), field_profile(values));
	check_near("estimate: one level is one decider (recall)", m.recall, 0.8);
	check_near("estimate: one decider (accuracy)", m.accuracy, 0.89);
	check_near("estimate: one decider (precision)", m.precision, 0.08 / 0.17);
	field_reset(values);
	values[F_LEAF_RECALL] = 0;
	values[F_LEAF_SPEC] = 100;
	m = metrics_estimate(field_params(values), field_profile(values));
	check_near("estimate: never predicts positive, precision 0 (no 0/0)",
		m.precision, 0.0);
	check_near("estimate: never predicts positive, accuracy", m.accuracy, 0.9);
	field_reset(values);
	values[F_LEAF_RECALL] = 40;
	values[F_LEAF_SPEC] = 45;
	m = metrics_estimate(field_params(values), field_profile(values));
	check_near("estimate: deciders worse than chance get worse (recall)",
		m.recall, 0.27189799534049747);
	check_near("estimate: worse than chance (precision)", m.precision,
		0.04646635027240442);
	set_tree(values, 12, 12, 5);
	m = metrics_estimate(field_params(values), field_profile(values));
	check(metrics_permil(m.accuracy) == 1000 && metrics_permil(m.precision)
		== 1000 && m.precision == m.precision, "estimate: 55 voting levels of "
		"12 stay finite and reach 100.0%", "");
	set_tree(values, 5, 2, 3);
	m = metrics_estimate(field_params(values), field_profile(values));
	check_near("estimate: depth 2 votes change nothing", m.recall, 0.8);
	set_tree(values, 12, 12, 5);
	values[F_LEAF_RECALL] = 30;
	values[F_POSITIVE_PCT] = 50;
	m = metrics_estimate(field_params(values), field_profile(values));
	check_near("estimate: precision from tiny rates keeps its precision "
		"(recall 1.1e-17, false positives 2.8e-18)", m.precision,
		0.79829195508120887429);
}

static void	test_permil(void)
{
	int			values[FIELD_COUNT];
	t_metrics	m;

	check(metrics_permil(-1.0) == 0 && metrics_permil(0.0) == 0,
		"permil: rates up to 0 are 0", "");
	check(metrics_permil(1.0) == 1000 && metrics_permil(2.0) == 1000,
		"permil: rates from 1 are 1000", "");
	check(metrics_permil(0.98577) == 986 && metrics_permil(0.0004) == 0
		&& metrics_permil(0.0006) == 1, "permil: rounds to the nearest", "");
	set_tree(values, 1, 3, 2);
	values[F_LEAF_RECALL] = 100;
	values[F_LEAF_SPEC] = 45;
	values[F_POSITIVE_PCT] = 1;
	m = metrics_estimate(field_params(values), field_profile(values));
	check(metrics_permil(m.accuracy) == 456, "permil: an exact half rounds "
		"up (accuracy 45.55% is shown as 45.6%)", "");
}

static void	test_cost(void)
{
	int		values[FIELD_COUNT];
	t_cost	cost;

	field_reset(values);
	cost = cost_estimate(tree_build(field_params(values)),
			field_profile(values));
	check(cost.tier == 2, "cost: the default schema fits a medium container",
		"");
	check_u64("cost: medium is 4 vCPU x 27 + 8 GiB x 3 EUR/month",
		cost.month_eur, 132);
	values[F_VCPU_CENTS] = 2701;
	cost = cost_estimate(tree_build(field_params(values)),
			field_profile(values));
	check_u64("cost: cents round up to the next euro", cost.month_eur, 133);
	set_tree(values, 7, 6, 1);
	cost = cost_estimate(tree_build(field_params(values)),
			field_profile(values));
	check(cost.tier == TIER_CLUSTER && cost.replicas == 10,
		"cost: L=7 D=6 E=1 needs a cluster of 10 x 8xlarge", "");
	check_u64("cost: a cluster pays every replica", cost.month_eur, 37440);
	set_tree(values, 12, 12, 5);
	cost = cost_estimate(tree_build(field_params(values)),
			field_profile(values));
	check_u64("cost: saturated schema, saturated cost", cost.month_eur,
		U64_MAX);
	field_reset(values);
	values[F_VCPU_CENTS] = 0;
	values[F_GIB_CENTS] = 0;
	cost = cost_estimate(tree_build(field_params(values)),
			field_profile(values));
	check_u64("cost: free resources cost nothing", cost.month_eur, 0);
}

static void	test_ceil_div(void)
{
	check_u64("ceil_div: exact", ceil_div(13200, 100), 132);
	check_u64("ceil_div: rounds up", ceil_div(13201, 100), 133);
	check_u64("ceil_div: zero", ceil_div(0, 100), 0);
	check_u64("ceil_div: no overflow just below 2^64",
		ceil_div(U64_MAX - 1, 100), 184467440737095517ULL);
	check_u64("ceil_div: saturated stays saturated", ceil_div(U64_MAX, 100),
		U64_MAX);
	check_u64("ceil_div: by zero saturates", ceil_div(5, 0), U64_MAX);
}

static int	unmet_with(int *values, int id, int value)
{
	field_reset(values);
	values[id] = value;
	return (request_check(values).unmet);
}

static void	test_request(void)
{
	int			values[FIELD_COUNT];
	t_request	request;
	t_metrics	m;

	check(unmet_with(values, F_LEVELS, 3) == 0,
		"request: the default schema meets the default request", "");
	check(unmet_with(values, F_BUDGET, 131) == REQ_BUDGET,
		"request: 132 EUR/month is over a budget of 131", "");
	check(unmet_with(values, F_BUDGET, 132) == 0,
		"request: a cost equal to the budget meets it", "");
	set_tree(values, 7, 6, 1);
	values[F_BUDGET] = 0;
	check((request_check(values).unmet & REQ_BUDGET) == 0,
		"request: budget 0 has no limit", "");
	check(unmet_with(values, F_ACCURACY, 99) == REQ_ACCURACY
		&& unmet_with(values, F_ACCURACY, 98) == 0,
		"request: accuracy 98.6% meets 98 but not 99", "");
	check(unmet_with(values, F_PRECISION, 91) == REQ_PRECISION
		&& unmet_with(values, F_PRECISION, 90) == 0,
		"request: precision 90.5% meets 90 but not 91", "");
	check(unmet_with(values, F_RECALL, 96) == REQ_RECALL
		&& unmet_with(values, F_RECALL, 95) == 0,
		"request: recall 95.8% meets 95 but not 96", "");
	request = field_request(values);
	request.budget = 0;
	request.accuracy = 80;
	request.precision = 80;
	request.recall = 100;
	m.accuracy = 0.7996;
	m.precision = 0.7994;
	m.recall = 0.9996;
	m.specificity = 0.9;
	check(request_unmet(request, m, cost_estimate(tree_build(
					field_params(values)), field_profile(values)))
		== REQ_PRECISION, "request: compared as shown, rounded to 0.1% "
		"(79.96% meets 80, 79.94% does not)", "");
	field_reset(values);
	values[F_ACCURACY] = 0;
	values[F_PRECISION] = 0;
	values[F_RECALL] = 0;
	values[F_LEAF_RECALL] = 0;
	check(request_check(values).unmet == 0,
		"request: 0 asks for nothing", "");
}

static void	test_text(void)
{
	int		values[FIELD_COUNT];
	char	text[FMT_LEN];
	t_check	result;

	field_reset(values);
	result = request_check(values);
	request_estimate(result, F_BUDGET, text, FMT_LEN);
	check_str("text: budget estimate, in EUR/month like the budget", text,
		"132");
	request_estimate(result, F_ACCURACY, text, FMT_LEN);
	check_str("text: accuracy estimate", text, "98.6%");
	request_estimate(result, F_PRECISION, text, FMT_LEN);
	check_str("text: precision estimate", text, "90.5%");
	request_estimate(result, F_RECALL, text, FMT_LEN);
	check_str("text: recall estimate", text, "95.8%");
	set_tree(values, 7, 6, 1);
	request_estimate(request_check(values), F_BUDGET, text, FMT_LEN);
	check_str("text: large costs are abbreviated", text, "37.4k");
	set_tree(values, 12, 12, 5);
	request_estimate(request_check(values), F_BUDGET, text, FMT_LEN);
	check_str("text: saturated cost", text, ">1.8E");
	request_estimate(request_check(values), F_RECALL, text, FMT_LEN);
	check_str("text: 100% is shown whole", text, "100.0%");
}

int	main(void)
{
	printf("Testing the budget and metric estimates of fractal_lab\n");
	test_fields();
	test_vote();
	test_rate();
	test_estimate();
	test_permil();
	test_cost();
	test_ceil_div();
	test_request();
	test_text();
	printf("\n");
	if (g_failures)
	{
		printf("Model lab unit tests FAILED: %d of %d checks failed\n",
			g_failures, g_checks);
		return (1);
	}
	printf("Model lab unit tests passed: %d checks\n", g_checks);
	return (0);
}
