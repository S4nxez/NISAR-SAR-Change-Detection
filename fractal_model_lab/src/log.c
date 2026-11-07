/* ************************************************************************** */
/*                                                                            */
/*                                                      :::      ::::::::   */
/*   log.c                                              :+:      :+:    :+:   */
/*                                                  +:+ +:+         +:+     */
/*   By: sanxez <desanchezmunoz02@gmail.com>        +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2026/10/25 12:00:00 by sanxez            #+#    #+#             */
/*   Updated: 2026/10/25 12:00:00 by sanxez           ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#include <stdarg.h>
#include <stdio.h>
#include <string.h>
#include "app.h"

void	app_log(t_app *app, const char *message)
{
	if (app->log_count == LOG_LINES)
	{
		memmove(app->logs[0], app->logs[1], (LOG_LINES - 1) * LOG_LEN);
		app->log_count--;
	}
	snprintf(app->logs[app->log_count], LOG_LEN, "%s", message);
	app->log_count++;
	app->log_scroll = 0;
}

void	app_logf(t_app *app, const char *format, ...)
{
	char	message[LOG_LEN];
	va_list	args;

	va_start(args, format);
	vsnprintf(message, LOG_LEN, format, args);
	va_end(args);
	app_log(app, message);
}

void	app_clear_logs(t_app *app)
{
	app->log_count = 0;
	app->log_scroll = 0;
}

static void	help_keys(t_app *app)
{
	app_log(app, "Keys: Tab/S-Tab panel | 1-4 focus | z zoom | q quit");
	app_log(app, "        g generate | h help | : go to terminal");
	app_log(app, "Fractal: up/down arrows scroll levels");
	app_log(app, "Parameters: up/down selects, -/+ or left/right changes,");
	app_log(app, "        Enter types 'set <field> ' in the terminal");
	app_log(app, "Terminal: Esc leaves, PgUp/PgDn scroll the logs");
}

void	app_help(t_app *app)
{
	app_log(app, "--- help ---");
	help_keys(app);
	app_log(app, "Commands: help | gen | stats | reset | clear | quit");
	app_log(app, "  set <field> <n>  (or '<field> <n>')");
	app_log(app, "  fields: levels depth exponent and those of 'profile'");
	app_log(app, "  profile [field n]  model profile for resources");
	app_log(app, "  focus <1-4> | zoom [1-4|off] | scroll <level>");
	app_log(app, "Tree: L levels, D children per node; E applies the tree");
	app_log(app, "  on every leaf E times: (L-1)*E+1 total levels.");
	app_log(app, "  Leaves (D) = decider models; the rest (V) = voters.");
}
