/* ************************************************************************** */
/*                                                                            */
/*                                                      :::      ::::::::   */
/*   format.c                                           :+:      :+:    :+:   */
/*                                                  +:+ +:+         +:+     */
/*   By: sanxez <desanchezmunoz02@gmail.com>        +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2026/10/25 12:00:00 by sanxez            #+#    #+#             */
/*   Updated: 2026/10/25 12:00:00 by sanxez           ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#include <stdio.h>
#include "format.h"

static int	scale_down(double *value, double base, int max_unit)
{
	int	unit;

	unit = 0;
	while (*value >= base && unit < max_unit)
	{
		*value /= base;
		unit++;
	}
	return (unit);
}

void	fmt_count(t_u64 value, char *buf, size_t size)
{
	const char	*units;
	double		scaled;
	int			unit;

	units = " kMGTPE";
	if (value == U64_MAX)
		snprintf(buf, size, ">1.8E");
	else if (value < 10000)
		snprintf(buf, size, "%llu", value);
	else
	{
		scaled = (double)value;
		unit = scale_down(&scaled, 1000.0, 6);
		snprintf(buf, size, "%.1f%c", scaled, units[unit]);
	}
}

void	fmt_mib(t_u64 mib, char *buf, size_t size)
{
	const char	*units[5];
	double		scaled;
	int			unit;

	units[0] = "MiB";
	units[1] = "GiB";
	units[2] = "TiB";
	units[3] = "PiB";
	units[4] = "EiB";
	scaled = (double)mib;
	unit = scale_down(&scaled, 1024.0, 4);
	if (mib == U64_MAX)
		snprintf(buf, size, ">16 EiB");
	else if (unit == 0)
		snprintf(buf, size, "%llu MiB", mib);
	else
		snprintf(buf, size, "%.1f %s", scaled, units[unit]);
}

void	fmt_time_us(t_u64 us, char *buf, size_t size)
{
	double	value;

	value = (double)us;
	if (us == U64_MAX)
		snprintf(buf, size, "inf");
	else if (us < 1000)
		snprintf(buf, size, "%llu us", us);
	else if (us < 1000000)
		snprintf(buf, size, "%.1f ms", value / 1e3);
	else if (us < 60000000)
		snprintf(buf, size, "%.2f s", value / 1e6);
	else if (us < 3600000000ULL)
		snprintf(buf, size, "%.1f min", value / 6e7);
	else
		snprintf(buf, size, "%.1f h", value / 3.6e9);
}

int	parse_int(const char *str, int *out)
{
	int	value;
	int	len;

	value = 0;
	len = 0;
	if (!str || str[0] == '\0')
		return (0);
	while (str[len] >= '0' && str[len] <= '9' && len < 9)
	{
		value = value * 10 + (str[len] - '0');
		len++;
	}
	if (str[len] != '\0')
		return (0);
	*out = value;
	return (1);
}
