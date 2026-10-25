/* ************************************************************************** */
/*                                                                            */
/*                                                      :::      ::::::::   */
/*   ui.h                                               :+:      :+:    :+:   */
/*                                                  +:+ +:+         +:+     */
/*   By: sanxez <desanchezmunoz02@gmail.com>        +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2026/10/25 12:00:00 by sanxez            #+#    #+#             */
/*   Updated: 2026/10/25 12:00:00 by sanxez           ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#ifndef UI_H
# define UI_H

# include "app.h"

# define CP_VOTER_A 1
# define CP_VOTER_B 2
# define CP_VOTER_C 3
# define CP_LEAF 4
# define CP_ROOT 5
# define CP_FOCUS 6
# define CP_WARN 7
# define UI_MARGIN 2

typedef void	(*t_drawer)(WINDOW *win, t_app *app);

void	ui_init_colors(void);
void	ui_draw(t_app *app);
void	ui_frame(WINDOW *win, const char *title, int focused);
void	ui_bar(WINDOW *win, int y, t_cost cost);
void	ui_bar_legend(WINDOW *win, int y, t_cost cost);
void	ui_text(WINDOW *win, int y, int x, const char *text);
int		ui_wrap_len(const char *text, int room);
int		ui_line_rows(const char *line, int room);
void	ui_textf(WINDOW *win, int y, const char *format, ...);
void	draw_fractal(WINDOW *win, t_app *app);
void	draw_params(WINDOW *win, t_app *app);
void	draw_cost(WINDOW *win, t_app *app);
void	draw_logs(WINDOW *win, t_app *app);
void	draw_status(WINDOW *win, t_app *app);

#endif
