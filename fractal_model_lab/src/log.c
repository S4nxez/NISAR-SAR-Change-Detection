/* ************************************************************************** */
/*                                                                            */
/*                                                      :::      ::::::::   */
/*   log.c                                              :+:      :+:    :+:   */
/*                                                  +:+ +:+         +:+     */
/*   By: sanxez <desanchezmunoz02@gmail.com>        +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2026/10/25 12:00:00 by sanxez            #+#    #+#             */
/*   Updated: 2026/10/29 12:00:00 by sanxez           ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#include <stdarg.h>
#include <stdio.h>
#include <string.h>
#include "app.h"

void	app_log(t_app *app, const char *message)
{
	if (app->log_count == LOG_LINES)
	{
		memmove(app->logs[0], app->logs[1], (LOG_LINES - 1) * LOG_LEN);
		app->log_count--;
	}
	snprintf(app->logs[app->log_count], LOG_LEN, "%s", message);
	app->log_count++;
	app->log_scroll = 0;
}

void	app_logf(t_app *app, const char *format, ...)
{
	char	message[LOG_LEN];
	va_list	args;

	va_start(args, format);
	vsnprintf(message, LOG_LEN, format, args);
	va_end(args);
	app_log(app, message);
}

void	app_clear_logs(t_app *app)
{
	app->log_count = 0;
	app->log_scroll = 0;
}

static void	help_keys(t_app *app)
{
	app_log(app, "Teclas: Tab/S-Tab panel | 1-4 foco | z zoom | q salir");
	app_log(app, "        g generar | h ayuda | : ir al terminal");
	app_log(app, "Fractal: flechas arriba/abajo desplazan niveles");
	app_log(app, "Parametros: arriba/abajo elige, -/+ o izq/der cambia,");
	app_log(app, "        Enter escribe 'set <campo> ' en el terminal");
	app_log(app, "Terminal: Esc sale, RePag/AvPag desplaza los logs");
}

void	app_help(t_app *app)
{
	app_log(app, "--- ayuda ---");
	help_keys(app);
	app_log(app, "Comandos: help | gen | stats | reset | clear | quit");
	app_log(app, "  set <campo> <n>  (o '<campo> <n>')");
	app_log(app, "  campos: levels depth exponent random random_pct seed");
	app_log(app, "  (niveles profundidad exponencial aleatorio apagado_pct");
	app_log(app, "  semilla) y los de 'profile'");
	app_log(app, "  profile [campo n]  perfil de modelo para recursos");
	app_log(app, "  focus <1-4> | zoom [1-4|off] | scroll <nivel>");
	app_log(app, "Arbol: L niveles, D hijos por nodo; E aplica el arbol");
	app_log(app, "  sobre cada hoja E veces: (L-1)*E+1 niveles totales.");
	app_log(app, "  Hojas (D) = modelos decisores; resto (V) = votantes.");
	app_log(app, "Aleatorio: random 1 apaga al azar el random_pct% de los");
	app_log(app, "  modelos, ramas incluidas: cada corte (x) apaga lo que");
	app_log(app, "  cuelga de el. Misma semilla (seed), mismo esquema.");
}
