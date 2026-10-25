/* ************************************************************************** */
/*                                                                            */
/*                                                      :::      ::::::::   */
/*   fractal_span.c                                     :+:      :+:    :+:   */
/*                                                  +:+ +:+         +:+     */
/*   By: sanxez <desanchezmunoz02@gmail.com>        +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2026/10/25 12:00:00 by sanxez            #+#    #+#             */
/*   Updated: 2026/10/25 12:00:00 by sanxez           ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#include "view.h"

chtype	view_edge_attr(t_view *view, int y)
{
	int	level;

	level = view->first + (y - view->top) / view->gap;
	return (view_attr(view->params, level) & A_COLOR);
}

void	view_draw_span(t_view *view, int y, t_span span)
{
	chtype	attr;

	attr = view_edge_attr(view, y);
	if (span.first == span.last)
	{
		mvwaddch(view->win, y, span.first, ACS_VLINE | attr);
		return ;
	}
	mvwhline(view->win, y, span.first, ACS_HLINE | attr,
		span.last - span.first + 1);
	mvwaddch(view->win, y, span.first, ACS_ULCORNER | attr);
	mvwaddch(view->win, y, span.last, ACS_URCORNER | attr);
}

int	view_child_tees(t_view *view, int level, t_u64 first, t_span span)
{
	t_u64	child;
	t_u64	last;
	int		x;
	int		y;
	int		hits;

	hits = 0;
	y = view_row(view, level) - 1;
	child = first + 1;
	last = first + (t_u64)view->params.depth - 1;
	while (child < last)
	{
		x = view_node_x(view, level, child);
		if (x == span.parent)
			hits = 1;
		else
			mvwaddch(view->win, y, x, ACS_TTEE | view_edge_attr(view, y));
		child++;
	}
	return (hits);
}

void	view_draw_junction(t_view *view, int y, t_span span)
{
	chtype	glyph;

	if (span.parent < span.first || span.parent > span.last)
		return ;
	if (span.first == span.last)
		glyph = ACS_VLINE;
	else if (span.parent == span.first)
		glyph = ACS_LTEE;
	else if (span.parent == span.last)
		glyph = ACS_RTEE;
	else if (span.hits_child)
		glyph = ACS_PLUS;
	else
		glyph = ACS_BTEE;
	mvwaddch(view->win, y, span.parent, glyph | view_edge_attr(view, y));
}

int	view_child_extent(t_view *view, int level, t_u64 parent, t_span *span)
{
	t_u64	child;

	view_group_span(view, level, parent, span);
	if (!view_fits(view, level + 1))
	{
		if (span->last - span->first < 2)
		{
			span->first = span->parent;
			span->last = span->parent;
		}
		return (0);
	}
	child = parent * (t_u64)view->params.depth;
	span->first = view_node_x(view, level + 1, child);
	span->last = view_node_x(view, level + 1,
			child + (t_u64)view->params.depth - 1);
	if (span->parent < span->first)
		span->first = span->parent;
	if (span->parent > span->last)
		span->last = span->parent;
	return (view_sparse(view, level + 1));
}
