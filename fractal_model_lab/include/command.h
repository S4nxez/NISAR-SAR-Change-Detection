/* ************************************************************************** */
/*                                                                            */
/*                                                      :::      ::::::::   */
/*   command.h                                          :+:      :+:    :+:   */
/*                                                  +:+ +:+         +:+     */
/*   By: sanxez <desanchezmunoz02@gmail.com>        +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2026/10/25 12:00:00 by sanxez            #+#    #+#             */
/*   Updated: 2026/10/25 12:00:00 by sanxez           ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#ifndef COMMAND_H
# define COMMAND_H

# include "app.h"

# define MAX_ARGS 4

typedef int	(*t_command_fn)(t_app *app, int argc, char **argv);

typedef struct s_command
{
	const char		*name;
	const char		*alias;
	t_command_fn	run;
}	t_command;

int	cmd_help(t_app *app, int argc, char **argv);
int	cmd_generate(t_app *app, int argc, char **argv);
int	cmd_stats(t_app *app, int argc, char **argv);
int	cmd_reset(t_app *app, int argc, char **argv);
int	cmd_clear(t_app *app, int argc, char **argv);
int	cmd_focus(t_app *app, int argc, char **argv);
int	cmd_zoom(t_app *app, int argc, char **argv);
int	cmd_scroll(t_app *app, int argc, char **argv);
int	cmd_quit(t_app *app, int argc, char **argv);
int	cmd_set(t_app *app, int argc, char **argv);
int	cmd_profile(t_app *app, int argc, char **argv);

#endif
