/* ************************************************************************** */
/*                                                                            */
/*                                                      :::      ::::::::   */
/*   cli_args.c                                         :+:      :+:    :+:   */
/*                                                  +:+ +:+         +:+     */
/*   By: sanxez <desanchezmunoz02@gmail.com>        +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2026/10/28 21:00:00 by sanxez            #+#    #+#             */
/*   Updated: 2026/10/28 21:00:00 by sanxez           ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#include <stdarg.h>
#include <string.h>
#include "cli.h"
#include "format.h"

static int	cli_fail(const char *format, ...)
{
	va_list	args;

	fprintf(stderr, "%s: ", CLI_NAME);
	va_start(args, format);
	vfprintf(stderr, format, args);
	va_end(args);
	fprintf(stderr, "\nPrueba '%s --help' para mas informacion.\n",
		CLI_NAME);
	return (CLI_USAGE_ERROR);
}

static int	set_value(t_app *app, int id, const char *arg)
{
	const t_field	*field;
	int				value;

	field = field_get(id);
	if (!parse_int(arg, &value))
		return (cli_fail("'%s' no es un entero positivo (--%s)",
				arg, field->name));
	if (value < field->min || value > field->max)
		return (cli_fail("%s fuera de rango (%d-%d): %d",
				field->name, field->min, field->max, value));
	app->values[id] = value;
	return (CLI_OK);
}

static int	option_field(const char *option, size_t len)
{
	char	name[CLI_FIELD_LEN];

	if (len >= CLI_FIELD_LEN)
		return (-1);
	memcpy(name, option, len);
	name[len] = '\0';
	return (field_find(name));
}

static int	field_option(t_app *app, char **argv, int *index)
{
	const char	*option;
	const char	*value;
	size_t		len;
	int			id;

	option = argv[*index] + 2;
	value = strchr(option, '=');
	len = strlen(option);
	if (value)
		len = (size_t)(value - option);
	id = option_field(option, len);
	if (id < 0)
		return (cli_fail("opcion desconocida '%s'", argv[*index]));
	if (value)
		return (set_value(app, id, value + 1));
	if (!argv[*index + 1])
		return (cli_fail("falta el valor de '%s'", argv[*index]));
	(*index)++;
	return (set_value(app, id, argv[*index]));
}

int	cli_parse_arg(t_app *app, t_cli *cli, char **argv, int *index)
{
	const char	*arg;

	arg = argv[*index];
	if (!strcmp(arg, "-h") || !strcmp(arg, "--help"))
		cli->help = 1;
	else if (!strcmp(arg, "--json"))
		cli->json = 1;
	else if (!strcmp(arg, "--text"))
		cli->json = 0;
	else if (!strncmp(arg, "--", 2) && arg[2] != '\0')
		return (field_option(app, argv, index));
	else
		return (cli_fail("argumento no valido '%s'", arg));
	return (CLI_OK);
}
