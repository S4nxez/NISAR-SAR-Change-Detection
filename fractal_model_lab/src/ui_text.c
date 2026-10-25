/* ************************************************************************** */
/*                                                                            */
/*                                                      :::      ::::::::   */
/*   ui_text.c                                          :+:      :+:    :+:   */
/*                                                  +:+ +:+         +:+     */
/*   By: sanxez <desanchezmunoz02@gmail.com>        +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2026/10/25 12:00:00 by sanxez            #+#    #+#             */
/*   Updated: 2026/10/25 12:00:00 by sanxez           ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#include <stdarg.h>
#include <stdio.h>
#include "ui.h"

void	ui_text(WINDOW *win, int y, int x, const char *text)
{
	int	room;

	room = getmaxx(win) - 1 - x;
	if (room <= 0 || y <= 0 || y >= getmaxy(win) - 1)
		return ;
	mvwaddnstr(win, y, x, text, room);
}

void	ui_textf(WINDOW *win, int y, const char *format, ...)
{
	char	text[256];
	va_list	args;

	va_start(args, format);
	vsnprintf(text, sizeof(text), format, args);
	va_end(args);
	ui_text(win, y, UI_MARGIN, text);
}
