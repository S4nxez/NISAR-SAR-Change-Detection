/* ************************************************************************** */
/*                                                                            */
/*                                                      :::      ::::::::   */
/*   cli.h                                              :+:      :+:    :+:   */
/*                                                  +:+ +:+         +:+     */
/*   By: sanxez <desanchezmunoz02@gmail.com>        +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2026/10/28 21:00:00 by sanxez            #+#    #+#             */
/*   Updated: 2026/10/28 21:00:00 by sanxez           ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#ifndef CLI_H
# define CLI_H

# include <stdio.h>
# include "app.h"

# define CLI_NAME "fractal_lab"
# define CLI_OK 0
# define CLI_WRITE_ERROR 1
# define CLI_USAGE_ERROR 2
# define CLI_FIELD_LEN 32

typedef struct s_cli
{
	int	json;
	int	help;
}	t_cli;

int			cli_run(t_app *app, int argc, char **argv);
int			cli_parse_arg(t_app *app, t_cli *cli, char **argv, int *index);
void		cli_usage(void);
void		cli_json(t_app *app);
void		cli_json_tree(t_app *app);
const char	*cli_json_bool(int value);

#endif
