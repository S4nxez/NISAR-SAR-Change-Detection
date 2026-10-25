/* ************************************************************************** */
/*                                                                            */
/*                                                      :::      ::::::::   */
/*   ui_logs.c                                          :+:      :+:    :+:   */
/*                                                  +:+ +:+         +:+     */
/*   By: sanxez <desanchezmunoz02@gmail.com>        +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2026/10/25 12:00:00 by sanxez            #+#    #+#             */
/*   Updated: 2026/10/25 12:00:00 by sanxez           ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#include <string.h>
#include "ui.h"

#define LOG_TOP 3

static chtype	log_attr(const char *line)
{
	if (!strncmp(line, "> ", 2))
		return (COLOR_PAIR(CP_ROOT) | A_BOLD);
	if (!strncmp(line, "error", 5))
		return (COLOR_PAIR(CP_WARN) | A_BOLD);
	if (!strncmp(line, "aviso", 5))
		return (COLOR_PAIR(CP_WARN));
	if (!strncmp(line, "---", 3))
		return (COLOR_PAIR(CP_VOTER_A) | A_BOLD);
	return (A_NORMAL);
}

static void	draw_prompt(WINDOW *win, t_app *app)
{
	int	room;
	int	offset;

	room = getmaxx(win) - 6;
	offset = 0;
	if (app->cmd_len > room)
		offset = app->cmd_len - room;
	wattron(win, A_BOLD);
	ui_textf(win, 1, "> %s", app->cmd + offset);
	wattroff(win, A_BOLD);
	if (app->focus == PANEL_TERM)
		mvwaddch(win, 1, 4 + app->cmd_len - offset, ' ' | A_REVERSE);
	mvwhline(win, 2, 1, ACS_HLINE, getmaxx(win) - 2);
}

static int	draw_line(WINDOW *win, int y, const char *line, int room)
{
	chtype	attr;
	int		rows;
	int		len;

	attr = log_attr(line);
	rows = 0;
	wattron(win, attr);
	while (rows == 0 || *line)
	{
		len = ui_wrap_len(line, room);
		if (y >= LOG_TOP && y < getmaxy(win) - 1)
			mvwaddnstr(win, y, 2, line, len);
		line += len;
		y++;
		rows++;
	}
	wattroff(win, attr);
	return (rows);
}

void	draw_logs(WINDOW *win, t_app *app)
{
	int	room;
	int	y;
	int	i;

	ui_frame(win, "[4] TERMINAL / LOGS", app->focus == PANEL_TERM);
	draw_prompt(win, app);
	room = getmaxx(win) - 4;
	if (room < 1)
		return ;
	y = getmaxy(win) - 1;
	i = app->log_count - app->log_scroll - 1;
	while (i >= 0 && y > LOG_TOP)
	{
		y -= ui_line_rows(app->logs[i], room);
		draw_line(win, y, app->logs[i], room);
		i--;
	}
	if (app->log_scroll > 0)
		mvwprintw(win, getmaxy(win) - 1, 2, " +%d recientes (AvPag) ",
			app->log_scroll);
}
