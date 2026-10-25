/* ************************************************************************** */
/*                                                                            */
/*                                                      :::      ::::::::   */
/*   view.h                                             :+:      :+:    :+:   */
/*                                                  +:+ +:+         +:+     */
/*   By: sanxez <desanchezmunoz02@gmail.com>        +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2026/10/25 12:00:00 by sanxez            #+#    #+#             */
/*   Updated: 2026/10/25 12:00:00 by sanxez           ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#ifndef VIEW_H
# define VIEW_H

# include <ncurses.h>
# include "tree.h"

# define VIEW_LABEL_W 4
# define VIEW_COUNT_W 7
# define VIEW_MAX_GAP 4

typedef struct s_view
{
	WINDOW		*win;
	t_params	params;
	int			total;
	int			first;
	int			shown;
	int			top;
	int			gap;
	int			left;
	int			width;
}	t_view;

typedef struct s_span
{
	int	parent;
	int	first;
	int	last;
	int	hits_child;
}	t_span;

void	view_init(t_view *view, WINDOW *win, t_params params, int first);
int		view_row(t_view *view, int level);
int		view_sparse(t_view *view, int level);
int		view_node_x(t_view *view, int level, t_u64 index);
int		view_span_center(t_view *view, int level, t_u64 index);
int		view_compact_x(t_view *view, int level, t_u64 index);
int		view_group_level(t_view *view, int level);
int		view_fits(t_view *view, int level);
int		view_child_extent(t_view *view, int level, t_u64 parent,
			t_span *span);
void	view_draw_level(t_view *view, int level);
void	view_draw_edges(t_view *view, int level);
void	view_group_span(t_view *view, int level, t_u64 index, t_span *span);
void	view_draw_span(t_view *view, int y, t_span span);
void	view_draw_junction(t_view *view, int y, t_span span);
int		view_child_tees(t_view *view, int level, t_u64 first, t_span span);
chtype	view_edge_attr(t_view *view, int y);
chtype	view_attr(t_params params, int level);
chtype	view_glyph(t_params params, int level);
chtype	view_density(t_view *view, int level);

#endif
