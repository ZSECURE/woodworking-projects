# woodworking-projects

Conservatory Timber Roof Calculator — Flask web application.

## Running locally

```bash
pip install -r requirements.txt
python app.py
# App available at http://localhost:5000
```

## Production deployment (Docker + HTTPS)

### Prerequisites

- A server with Docker and Docker Compose installed
- A domain name pointing at your server's IP address
- Ports 80 and 443 open in your firewall

### 1. Replace `YOUR_DOMAIN` in the Nginx config

Edit `nginx/nginx.conf` and replace every occurrence of `YOUR_DOMAIN` with your actual domain (e.g. `myapp.example.com`).

### 2. Issue your Let's Encrypt certificate (first time only)

Start Nginx on port 80 only (needed for the ACME challenge):

```bash
docker compose up -d nginx
docker compose run --rm certbot certonly \
  --webroot --webroot-path /var/www/certbot \
  --email you@example.com \
  --agree-tos --no-eff-email \
  -d YOUR_DOMAIN
```

### 3. Start everything

```bash
docker compose up -d
```

The app is now available at `https://YOUR_DOMAIN`. Certbot automatically renews the certificate every 12 hours if needed.

### Updating the app

```bash
docker compose build app
docker compose up -d --no-deps app
```