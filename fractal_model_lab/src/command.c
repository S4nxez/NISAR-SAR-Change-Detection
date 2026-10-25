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
	{"help", "ayuda", cmd_help},
	{"generate", "gen", cmd_generate},
	{"stats", "niveles", cmd_stats},
	{"reset", "reiniciar", cmd_reset},
	{"clear", "limpiar", cmd_clear},
	{"focus", "foco", cmd_focus},
	{"zoom", "max", cmd_zoom},
	{"scroll", "ver", cmd_scroll},
	{"quit", "salir", cmd_quit},
	{"set", "fijar", cmd_set},
	{"profile", "perfil", cmd_profile},
	{0, 0, 0}
	};
	int						i;

	i = 0;
	while (commands[i].name)
	{
		if (!strcmp(name, commands[i].name)
			|| !strcmp(name, commands[i].alias))
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
		app_log(app, "error: demasiados argumentos");
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
		app_logf(app, "error: '%s' desconocido, escribe help", argv[1]);
}
