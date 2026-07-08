# Network Security Controls

Network/security owner: Adam Menker

This application is a private internal tool. The current local development deployment does not by itself satisfy all production network security controls. Production SP-API access must not be enabled in a publicly reachable environment until the production controls below are implemented for that environment.

## Local Development Controls

- The app runs locally through Docker.
- The backend is intended for local/internal access only.
- `.env` secrets remain local and are ignored by git.
- The operating system firewall should be enabled.
- Endpoint anti-virus/anti-malware or equivalent OS security protections should be enabled and kept current.
- The development database should bind only to localhost or the Docker network.
- The database must not be exposed to the public internet.
- No router/firewall rule should forward public internet traffic to the local backend, frontend, or database.

## Production/Non-Local Deployment Requirements

Before any non-local production deployment that processes Amazon Information:

- HTTPS/TLS is required for all browser and API traffic.
- Firewall or security group rules must restrict inbound traffic to the minimum required ports.
- The backend API is the only service that may be exposed, and only behind HTTPS and access controls.
- The database must run in a private network segment and must not be publicly reachable.
- Admin access must require MFA.
- Secrets must be stored in a password manager, secret manager, or private deployment environment variables.
- IDS/IPS or managed threat detection/monitoring must be enabled using an appropriate host, network, or cloud security tool.
- Anti-virus/anti-malware or endpoint protection must be enabled and updated at least monthly on systems that access Amazon Information.
- Network segmentation must separate public application access from private database, secrets, and administrative services.
- Access control lists or firewall rules must deny unauthorized IP address access.
- Logs and security alerts must be reviewed regularly.

## Required Control Categories

Amazon flagged the following control categories; this project must maintain evidence for each before production access is enabled:

- Firewalls and access control lists.
- IDS/IPS or managed threat detection.
- Anti-virus/anti-malware.
- Network segmentation.

## Current Application Guardrails

- Docker Compose keeps the database in a Docker network and maps it only for local development.
- The backend has a production guard that fails fast when `APP_ENV=production` unless unauthenticated public exposure is explicitly acknowledged.
- Production HTTPS and access control requirements are documented here and in [SECURITY.md](SECURITY.md).

