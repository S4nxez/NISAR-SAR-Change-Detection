/* ************************************************************************** */
/*                                                                            */
/*                                                      :::      ::::::::   */
/*   format.h                                           :+:      :+:    :+:   */
/*                                                  +:+ +:+         +:+     */
/*   By: sanxez <desanchezmunoz02@gmail.com>        +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2026/10/25 12:00:00 by sanxez            #+#    #+#             */
/*   Updated: 2026/10/25 12:00:00 by sanxez           ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#ifndef FORMAT_H
# define FORMAT_H

# include <stddef.h>
# include "tree.h"

# define FMT_LEN 32

void	fmt_count(t_u64 value, char *buf, size_t size);
void	fmt_mib(t_u64 mib, char *buf, size_t size);
void	fmt_time_us(t_u64 us, char *buf, size_t size);
int		parse_int(const char *str, int *out);

#endif
