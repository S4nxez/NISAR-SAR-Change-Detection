/* ************************************************************************** */
/*                                                                            */
/*                                                      :::      ::::::::   */
/*   command_basic.c                                    :+:      :+:    :+:   */
/*                                                  +:+ +:+         +:+     */
/*   By: sanxez <desanchezmunoz02@gmail.com>        +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2026/10/25 12:00:00 by sanxez            #+#    #+#             */
/*   Updated: 2026/10/25 12:00:00 by sanxez           ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#include "command.h"

int	cmd_help(t_app *app, int argc, char **argv)
{
	(void)argc;
	(void)argv;
	app_help(app);
	return (1);
}

int	cmd_generate(t_app *app, int argc, char **argv)
{
	(void)argc;
	(void)argv;
	report_generate(app);
	return (1);
}

int	cmd_stats(t_app *app, int argc, char **argv)
{
	(void)argc;
	(void)argv;
	report_levels(app);
	return (1);
}

int	cmd_reset(t_app *app, int argc, char **argv)
{
	(void)argc;
	(void)argv;
	field_reset(app->values);
	app->fractal_top = 0;
	app_log(app, "Parametros y perfil restaurados.");
	report_generate(app);
	return (1);
}

int	cmd_clear(t_app *app, int argc, char **argv)
{
	(void)argc;
	(void)argv;
	app_clear_logs(app);
	return (1);
}
