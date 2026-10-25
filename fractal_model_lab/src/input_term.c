/* ************************************************************************** */
/*                                                                            */
/*                                                      :::      ::::::::   */
/*   input_term.c                                       :+:      :+:    :+:   */
/*                                                  +:+ +:+         +:+     */
/*   By: sanxez <desanchezmunoz02@gmail.com>        +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2026/10/25 12:00:00 by sanxez            #+#    #+#             */
/*   Updated: 2026/10/25 12:00:00 by sanxez           ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#include <string.h>
#include "app.h"

static void	scroll_logs(t_app *app, int delta)
{
	app->log_scroll += delta;
	if (app->log_scroll > app->log_count - 1)
		app->log_scroll = app->log_count - 1;
	if (app->log_scroll < 0)
		app->log_scroll = 0;
}

static void	submit(t_app *app)
{
	char	line[CMD_LEN];

	if (app->cmd_len == 0)
		return ;
	memcpy(line, app->cmd, CMD_LEN);
	app->cmd[0] = '\0';
	app->cmd_len = 0;
	app_logf(app, "> %s", line);
	command_execute(app, line);
}

static void	edit_command(t_app *app, int key)
{
	if (key == KEY_BACKSPACE || key == 127 || key == '\b')
	{
		if (app->cmd_len > 0)
			app->cmd_len--;
		app->cmd[app->cmd_len] = '\0';
	}
	else if (key >= ' ' && key <= '~' && app->cmd_len < CMD_LEN - 1)
	{
		app->cmd[app->cmd_len] = (char)key;
		app->cmd_len++;
		app->cmd[app->cmd_len] = '\0';
	}
}

void	term_key(t_app *app, int key)
{
	if (key == 27)
		app_focus(app, app->prev_focus);
	else if (key == '\n' || key == '\r' || key == KEY_ENTER)
		submit(app);
	else if (key == KEY_PPAGE)
		scroll_logs(app, 5);
	else if (key == KEY_NPAGE)
		scroll_logs(app, -5);
	else if (key == KEY_UP)
		scroll_logs(app, 1);
	else if (key == KEY_DOWN)
		scroll_logs(app, -1);
	else
		edit_command(app, key);
}
