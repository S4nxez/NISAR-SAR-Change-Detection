/* ************************************************************************** */
/*                                                                            */
/*                                                      :::      ::::::::   */
/*   cli.c                                              :+:      :+:    :+:   */
/*                                                  +:+ +:+         +:+     */
/*   By: sanxez <desanchezmunoz02@gmail.com>        +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2026/10/28 21:00:00 by sanxez            #+#    #+#             */
/*   Updated: 2026/10/28 21:00:00 by sanxez           ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#include <string.h>
#include "cli.h"

static void	cli_text(t_app *app)
{
	int	line;

	report_generate(app);
	report_levels(app);
	line = 0;
	while (line < app->log_count)
		puts(app->logs[line++]);
}

static int	cli_flush(void)
{
	if (fflush(stdout) == EOF || ferror(stdout))
	{
		fprintf(stderr, "%s: no se pudo escribir la salida\n", CLI_NAME);
		return (CLI_WRITE_ERROR);
	}
	return (CLI_OK);
}

int	cli_run(t_app *app, int argc, char **argv)
{
	t_cli	cli;
	int		status;
	int		index;

	memset(app, 0, sizeof(*app));
	memset(&cli, 0, sizeof(cli));
	field_reset(app->values);
	status = CLI_OK;
	index = 1;
	while (status == CLI_OK && !cli.help && index < argc)
	{
		status = cli_parse_arg(app, &cli, argv, &index);
		index++;
	}
	if (status != CLI_OK)
		return (status);
	if (cli.help)
		cli_usage();
	else if (cli.json)
		cli_json(app);
	else
		cli_text(app);
	return (cli_flush());
}
