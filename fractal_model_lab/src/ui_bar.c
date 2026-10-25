/* ************************************************************************** */
/*                                                                            */
/*                                                      :::      ::::::::   */
/*   ui_bar.c                                           :+:      :+:    :+:   */
/*                                                  +:+ +:+         +:+     */
/*   By: sanxez <desanchezmunoz02@gmail.com>        +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2026/10/25 12:00:00 by sanxez            #+#    #+#             */
/*   Updated: 2026/10/25 12:00:00 by sanxez           ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#include <stdio.h>
#include "ui.h"
#include "format.h"

static int	segment(t_u64 part, t_u64 total, int width)
{
	if (total == 0)
		return (0);
	return ((int)((double)part / (double)total * (double)width + 0.5));
}

static int	fill(WINDOW *win, int y, int x, int len)
{
	while (len > 0)
	{
		mvwaddch(win, y, x, ACS_CKBOARD);
		x++;
		len--;
	}
	return (x);
}

void	ui_bar(WINDOW *win, int y, t_cost cost)
{
	int	width;
	int	leaf;
	int	voter;
	int	x;

	width = getmaxx(win) - 6;
	if (width < 4 || y >= getmaxy(win) - 1)
		return ;
	leaf = segment(cost.leaf_mib, cost.ram_mib, width);
	voter = segment(cost.voter_mib, cost.ram_mib, width);
	if (leaf + voter > width)
		voter = width - leaf;
	mvwaddch(win, y, 2, '[');
	wattron(win, COLOR_PAIR(CP_LEAF));
	x = fill(win, y, 3, leaf);
	wattroff(win, COLOR_PAIR(CP_LEAF));
	wattron(win, COLOR_PAIR(CP_VOTER_A));
	x = fill(win, y, x, voter);
	wattroff(win, COLOR_PAIR(CP_VOTER_A));
	wattron(win, COLOR_PAIR(CP_ROOT) | A_DIM);
	x = fill(win, y, x, width - leaf - voter);
	wattroff(win, COLOR_PAIR(CP_ROOT) | A_DIM);
	mvwaddch(win, y, x, ']');
}

static void	legend_item(WINDOW *win, int y, chtype attr, const char *text)
{
	int	x;

	x = UI_MARGIN;
	if (getcurx(win) > x)
		x = getcurx(win) + 2;
	wattron(win, attr);
	ui_text(win, y, x, text);
	wattroff(win, attr);
}

void	ui_bar_legend(WINDOW *win, int y, t_cost cost)
{
	char	size[FMT_LEN];
	char	text[FMT_LEN + 4];

	wmove(win, y, 0);
	fmt_mib(cost.leaf_mib, size, FMT_LEN);
	snprintf(text, sizeof(text), "D %s", size);
	legend_item(win, y, COLOR_PAIR(CP_LEAF), text);
	fmt_mib(cost.voter_mib, size, FMT_LEN);
	snprintf(text, sizeof(text), "V %s", size);
	legend_item(win, y, COLOR_PAIR(CP_VOTER_A), text);
	fmt_mib(cost.runtime_mib, size, FMT_LEN);
	snprintf(text, sizeof(text), "TF %s", size);
	legend_item(win, y, COLOR_PAIR(CP_ROOT), text);
}
