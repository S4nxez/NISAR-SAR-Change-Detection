/* ************************************************************************** */
/*                                                                            */
/*                                                      :::      ::::::::   */
/*   cli_help.c                                         :+:      :+:    :+:   */
/*                                                  +:+ +:+         +:+     */
/*   By: sanxez <desanchezmunoz02@gmail.com>        +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2026/10/28 21:00:00 by sanxez            #+#    #+#             */
/*   Updated: 2026/10/28 21:00:00 by sanxez           ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#include "cli.h"

static void	usage_options(void)
{
	printf("Uso: %s [--text | --json] [--<campo> <n> | --<campo>=<n>]...\n\n",
		CLI_NAME);
	printf("Sin argumentos abre la TUI. Con argumentos genera el esquema "
		"sin interfaz\n(no necesita terminal) y lo escribe en la salida "
		"estandar.\n\n");
	printf("Opciones:\n");
	printf("  --text           informe en texto, el de 'gen' y 'stats' "
		"(por defecto)\n");
	printf("  --json           esquema completo en JSON, para "
		"integraciones (la web)\n");
	printf("  --<campo> <n>    fija un campo por nombre o alias (tambien "
		"--<campo>=<n>);\n");
	printf("                   los demas toman su valor por defecto. "
		"Si una opcion se\n                   repite, vale la ultima\n");
	printf("  -h, --help       muestra esta ayuda\n\n");
}

static void	usage_field(int id)
{
	const t_field	*field;
	char			name[CLI_FIELD_LEN + 2];
	char			alias[CLI_FIELD_LEN + 2];
	char			range[CLI_FIELD_LEN];

	field = field_get(id);
	if (id == 0)
		printf("Campos del esquema (nombre, alias, rango, por defecto):\n");
	else if (id == FRACTAL_FIELDS)
		printf("Perfil de modelo (nombre, alias, rango, por defecto):\n");
	snprintf(name, sizeof(name), "--%s", field->name);
	snprintf(alias, sizeof(alias), "--%s", field->alias);
	snprintf(range, sizeof(range), "%d-%d", field->min, field->max);
	printf("  %-16s %-16s %-12s %5d  %s\n", name, alias, range,
		field->initial, field->label);
}

void	cli_usage(void)
{
	int	id;

	usage_options();
	id = 0;
	while (id < FIELD_COUNT)
		usage_field(id++);
	printf("\nCodigos de salida: 0 correcto, 1 error al escribir la salida, "
		"2 argumentos\nno validos (el error se escribe en la salida de "
		"error).\n");
}
