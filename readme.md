# Trade Margin Analytics
![Java](https://img.shields.io/badge/Java-ED8B00?style=for-the-badge&logo=openjdk&logoColor=white)
![Spring Boot](https://img.shields.io/badge/Spring_Boot-6DB33F?style=for-the-badge&logo=spring-boot&logoColor=white)
![JavaScript](https://img.shields.io/badge/JavaScript-F7DF1E?style=for-the-badge&logo=javascript&logoColor=black)
![Leaflet](https://img.shields.io/badge/Leaflet-199900?style=for-the-badge&logo=leaflet&logoColor=white)
![Podman](https://img.shields.io/badge/Podman-892CA0?style=for-the-badge&logo=podman&logoColor=white)
![Caddy](https://img.shields.io/badge/Caddy-00ADD8?style=for-the-badge&logo=caddy&logoColor=white)
![Tailscale](https://img.shields.io/badge/Tailscale-242424?style=for-the-badge&logo=tailscale&logoColor=white)
![Raspberry Pi](https://img.shields.io/badge/Raspberry_Pi-A22846?style=for-the-badge&logo=raspberry-pi&logoColor=white)
<br>
![Website](https://img.shields.io/website?url=https%3A%2F%2Fraspberrypi.tail0a4b52.ts.net%2Ftrade-analytics%2F&up_message=online&down_message=offline&style=for-the-badge&label=Demo)

Trade Margin Analytics es una aplicación web orientada a la comparación de rutas comerciales internacionales, permitiendo analizar coste, tiempo y riesgo para tomar decisiones más eficientes.

🌐 **Live demo:**
https://raspberrypi.tail0a4b52.ts.net/trade-analytics/

---

## Tech Stack

| Layer | Technology |
|---|---|
| **Backend** | Java, Spring Boot *(planned)* |
| **Frontend** | Vanilla JavaScript, HTML, CSS |
| **Visualización** | Chart.js, Leaflet |
| **Infraestructura** | Podman, Caddy |
| **CI/CD** | GitHub Actions *(planned)* |
| **Networking** | Tailscale |
| **Server** | Raspberry Pi |

---

## Features (MVP)

- Visualización de rutas internacionales sobre mapa interactivo
- Comparación de rutas por:
  - Coste
  - Tiempo
  - Riesgo
- Sistema de recomendación de mejor ruta basado en score
- Dashboard con métricas agregadas

> ⚠️ Proyecto en fase inicial — funcionalidades sujetas a cambios

---

## Deployment

El proyecto está desplegado en una Raspberry Pi utilizando contenedores y acceso público seguro sin necesidad de abrir puertos en el router.

- **Caddy** como reverse proxy con HTTPS automático
- **Podman y poodman-compose** para la gestión de contenedores
- **Tailscale Funnel** para exponer la aplicación públicamente
- **GitHub Actions** para automatizar el flujo de trabajo