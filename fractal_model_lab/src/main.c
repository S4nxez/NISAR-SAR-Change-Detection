/* ************************************************************************** */
/*                                                                            */
/*                                                      :::      ::::::::   */
/*   main.c                                             :+:      :+:    :+:   */
/*                                                  +:+ +:+         +:+     */
/*   By: sanxez <desanchezmunoz02@gmail.com>        +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2026/10/25 12:00:00 by sanxez            #+#    #+#             */
/*   Updated: 2026/10/28 21:00:00 by sanxez           ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#include "app.h"
#include "cli.h"

int	main(int argc, char **argv)
{
	static t_app	app;

	if (argc > 1)
		return (cli_run(&app, argc, argv));
	app_init(&app);
	app_run(&app);
	return (0);
}
