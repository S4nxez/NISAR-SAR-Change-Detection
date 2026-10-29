# NISAR SAR Change Detection - Boilerplate code
![Java](https://img.shields.io/badge/Java-ED8B00?style=for-the-badge&logo=openjdk&logoColor=white)
![Spring Boot](https://img.shields.io/badge/Spring_Boot-6DB33F?style=for-the-badge&logo=spring-boot&logoColor=white)
![JavaScript](https://img.shields.io/badge/JavaScript-F7DF1E?style=for-the-badge&logo=javascript&logoColor=black)
![Leaflet](https://img.shields.io/badge/Leaflet-199900?style=for-the-badge&logo=leaflet&logoColor=white)
![Podman](https://img.shields.io/badge/Podman-892CA0?style=for-the-badge&logo=podman&logoColor=white)
![Caddy](https://img.shields.io/badge/Caddy-00ADD8?style=for-the-badge&logo=caddy&logoColor=white)
![Tailscale](https://img.shields.io/badge/Tailscale-242424?style=for-the-badge&logo=tailscale&logoColor=white)
![Raspberry Pi](https://img.shields.io/badge/Raspberry_Pi-A22846?style=for-the-badge&logo=raspberry-pi&logoColor=white)
<br>
[![Website](https://img.shields.io/website?url=https%3A%2F%2Fraspberrypi.tail0a4b52.ts.net%2Fterra-pulse%2F&up_message=online&down_message=offline&style=for-the-badge&label=Demo)](https://img.shields.io/website?url=https%3A%2F%2Fraspberrypi.tail0a4b52.ts.net%2Fterra-pulse%2F)

Web application with linux infraestructure and sub-programs oriented towards NISAR SAR Nasa Space Apps challenge hackathon, focused on combining the strength of *machine learning* with a user friendly interface.

🌐 **Live demo:**
https://raspberrypi.tail0a4b52.ts.net/terra-pulse/

---

## Tech Stack

| Layer | Technology |
|---|---|
| **Backend** | Java, Spring Boot |
| **Frontend** | Vanilla JavaScript, HTML, CSS |
| **Machine learning** | Python (TF), C |
| **Infrastructure** | Podman, Caddy |
| **CI/CD** | GitHub Actions |
| **Networking** | Tailscale |
| **Server** | Raspberry Pi |


---

## Features (MVP)

- AI Schemes generator
- Data visualization 
- Change detection metrics based on NISAR SAR:
  - Change level and direction
  - Detection confidence
  - VV / VH backscatter time series
- Dashboard with relevant information

> ⚠️ Project in initial phase, functionalities are changing

---

## Deployment

The project is deployed on a Raspberry Pi using containers, with secure public access provided without the need to open ports on the router.

- **Caddy** as a reverse proxy with automatic HTTPS
- **Podman and Podman Compose** for container management
- **Tailscale Funnel** to expose the application publicly
- **GitHub Actions** to automate the workflow

Every push to `main` is validated before the images are built and deployed (frontend, model lab and backend builds, backend tests and a startup check of the whole stack), every deployment is smoke tested on the Raspberry Pi and through the public URL, and a failed deployment is rolled back to the last known-good images, see [tools/ci](tools/ci/README.md).

Every push to `develop` goes through the same pipeline to a separate develop stack on the Raspberry Pi, with its own database, so changes are QA'd there before the weekly merge releases them to production, see [Develop stack](tools/ci/README.md#develop-stack).
