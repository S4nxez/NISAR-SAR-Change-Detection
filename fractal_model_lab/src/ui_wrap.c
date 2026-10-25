/* ************************************************************************** */
/*                                                                            */
/*                                                      :::      ::::::::   */
/*   ui_wrap.c                                          :+:      :+:    :+:   */
/*                                                  +:+ +:+         +:+     */
/*   By: sanxez <desanchezmunoz02@gmail.com>        +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2026/10/25 12:00:00 by sanxez            #+#    #+#             */
/*   Updated: 2026/10/25 12:00:00 by sanxez           ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#include <string.h>
#include "ui.h"

int	ui_wrap_len(const char *text, int room)
{
	int	len;

	len = (int)strlen(text);
	if (len <= room)
		return (len);
	len = room;
	while (len > 0 && text[len] != ' ')
		len--;
	if (len == 0)
		return (room);
	return (len + 1);
}

int	ui_line_rows(const char *line, int room)
{
	int	rows;

	rows = 0;
	while (rows == 0 || *line)
	{
		line += ui_wrap_len(line, room);
		rows++;
	}
	return (rows);
}
