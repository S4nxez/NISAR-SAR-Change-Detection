/* ************************************************************************** */
/*                                                                            */
/*                                                      :::      ::::::::   */
/*   command_set.c                                      :+:      :+:    :+:   */
/*                                                  +:+ +:+         +:+     */
/*   By: sanxez <desanchezmunoz02@gmail.com>        +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2026/10/25 12:00:00 by sanxez            #+#    #+#             */
/*   Updated: 2026/10/29 02:00:00 by sanxez           ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#include "command.h"
#include "format.h"

static int	set_named(t_app *app, const char *name, const char *arg)
{
	int	id;
	int	value;

	id = field_find(name);
	if (id < 0)
	{
		app_logf(app, "error: campo '%s' desconocido", name);
		return (0);
	}
	if (!parse_int(arg, &value))
	{
		app_logf(app, "error: '%s' no es un entero positivo", arg);
		return (0);
	}
	return (field_change(app, id, value));
}

int	cmd_set(t_app *app, int argc, char **argv)
{
	if (argc != 3)
	{
		app_log(app, "uso: set <campo> <valor>");
		return (0);
	}
	return (set_named(app, argv[1], argv[2]));
}

int	cmd_profile(t_app *app, int argc, char **argv)
{
	if (argc == 1)
	{
		report_profile(app);
		return (1);
	}
	if (argc != 3 || field_find(argv[1]) < PARAM_FIELDS)
	{
		app_log(app, "uso: profile <campo_perfil> <valor>");
		return (0);
	}
	return (set_named(app, argv[1], argv[2]));
}
