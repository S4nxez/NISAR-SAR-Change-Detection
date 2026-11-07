/* ************************************************************************** */
/*                                                                            */
/*                                                      :::      ::::::::   */
/*   command.c                                          :+:      :+:    :+:   */
/*                                                  +:+ +:+         +:+     */
/*   By: sanxez <desanchezmunoz02@gmail.com>        +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2026/10/25 12:00:00 by sanxez            #+#    #+#             */
/*   Updated: 2026/10/25 12:00:00 by sanxez           ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#include <string.h>
#include "command.h"

static const t_command	*command_find(const char *name)
{
	static const t_command	commands[] = {
	{"help", 0, cmd_help},
	{"generate", "gen", cmd_generate},
	{"stats", 0, cmd_stats},
	{"reset", 0, cmd_reset},
	{"clear", 0, cmd_clear},
	{"focus", 0, cmd_focus},
	{"zoom", "max", cmd_zoom},
	{"scroll", 0, cmd_scroll},
	{"quit", 0, cmd_quit},
	{"set", 0, cmd_set},
	{"profile", 0, cmd_profile},
	{0, 0, 0}
	};
	int						i;

	i = 0;
	while (commands[i].name)
	{
		if (!strcmp(name, commands[i].name)
			|| (commands[i].alias
				&& !strcmp(name, commands[i].alias)))
			return (&commands[i]);
		i++;
	}
	return (0);
}

static int	tokenize(char *line, char **argv)
{
	char	*token;
	int		argc;

	argc = 0;
	token = strtok(line, " \t");
	while (token && argc < MAX_ARGS)
	{
		argv[argc] = token;
		argc++;
		token = strtok(0, " \t");
	}
	if (token)
		return (-1);
	return (argc);
}

void	command_execute(t_app *app, char *line)
{
	const t_command	*command;
	char			*argv[MAX_ARGS + 1];
	int				argc;

	argc = tokenize(line, argv + 1);
	if (argc < 0)
	{
		app_log(app, "error: too many arguments");
		return ;
	}
	if (argc == 0)
		return ;
	command = command_find(argv[1]);
	if (command)
		command->run(app, argc, argv + 1);
	else if (field_find(argv[1]) >= 0)
	{
		argv[0] = "set";
		cmd_set(app, argc + 1, argv);
	}
	else
		app_logf(app, "error: unknown '%s', type help", argv[1]);
}
