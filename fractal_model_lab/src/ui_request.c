/* ************************************************************************** */
/*                                                                            */
/*                                                      :::      ::::::::   */
/*   ui_request.c                                       :+:      :+:    :+:   */
/*                                                  +:+ +:+         +:+     */
/*   By: sanxez <desanchezmunoz02@gmail.com>        +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2026/10/29 02:00:00 by sanxez            #+#    #+#             */
/*   Updated: 2026/10/29 02:00:00 by sanxez           ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#include <stdio.h>
#include "ui.h"
#include "format.h"

static chtype	check_attr(t_check check, int request)
{
	if (check.unmet & request)
		return (COLOR_PAIR(CP_WARN) | A_BOLD);
	return (COLOR_PAIR(CP_LEAF));
}

void	draw_request(WINDOW *win, int id, int y, t_check check)
{
	char	estimate[FMT_LEN];
	char	text[FMT_LEN + 4];
	chtype	attr;

	request_estimate(check, id, estimate, FMT_LEN);
	snprintf(text, sizeof(text), "-> %s", estimate);
	attr = check_attr(check, 1 << (id - F_BUDGET));
	wattron(win, attr);
	ui_text(win, y, getcurx(win) + 1, text);
	wattroff(win, attr);
}

void	draw_budget(WINDOW *win, int y, t_check check)
{
	char	money[FMT_LEN];
	chtype	attr;

	fmt_count(check.cost.month_eur, money, FMT_LEN);
	attr = check_attr(check, REQ_BUDGET);
	wattron(win, attr);
	if (check.request.budget > 0)
		ui_textf(win, y, "Coste %s EUR/mes (presupuesto %d)", money,
			check.request.budget);
	else
		ui_textf(win, y, "Coste %s EUR/mes (sin limite)", money);
	wattroff(win, attr);
}
