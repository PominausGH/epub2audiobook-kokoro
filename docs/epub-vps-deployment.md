# ePub2Audiobook VPS Deployment Guide

## Prerequisites

- VPS with SSH access
- Docker and Docker Compose installed
- Port 5000 open (or configure reverse proxy)

## Quick Deploy

### 1. SSH into your VPS

```bash
ssh user@your-vps-ip
```

### 2. Clone the repository

```bash
git clone https://github.com/PominausGH/epub2audiobook-kokoro.git
cd epub2audiobook-kokoro
```

### 3. Configure environment

```bash
# Create .env file with secure secret key
echo "SECRET_KEY=$(openssl rand -hex 32)" > .env
```

### 4. Start the container

```bash
docker-compose up -d
```

### 5. Access the app

Open `http://your-vps-ip:5000` in your browser.

**First user to register becomes admin.**

---

## Installing Docker (if needed)

### Ubuntu/Debian

```bash
# Update packages
sudo apt update

# Install Docker
curl -fsSL https://get.docker.com | sudo sh

# Add your user to docker group (logout/login after)
sudo usermod -aG docker $USER

# Install Docker Compose
sudo apt install docker-compose-plugin
```

### Verify installation

```bash
docker --version
docker compose version
```

---

## Configuration

### Environment Variables

Create a `.env` file in the project directory:

```bash
# Required - generate a secure key
SECRET_KEY=your-secret-key-here

# Optional
DATABASE_PATH=/data/db/epub2audiobook.db
FLASK_ENV=production
```

### Data Persistence

Data is stored in `./data/` directory:
- `./data/uploads/` - Uploaded ePub files
- `./data/output/` - Generated audiobooks
- `./data/db/` - SQLite database (users, jobs)

To backup:
```bash
tar -czvf epub2audiobook-backup.tar.gz ./data
```

---

## Reverse Proxy with Nginx (Optional)

For HTTPS and custom domain:

### 1. Install Nginx

```bash
sudo apt install nginx certbot python3-certbot-nginx
```

### 2. Create Nginx config

```bash
sudo nano /etc/nginx/sites-available/epub2audiobook
```

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # For large file uploads
        client_max_body_size 100M;
        proxy_read_timeout 600s;
    }
}
```

### 3. Enable site and get SSL

```bash
sudo ln -s /etc/nginx/sites-available/epub2audiobook /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx

# Get SSL certificate
sudo certbot --nginx -d your-domain.com
```

---

## Management Commands

### View logs

```bash
docker-compose logs -f
```

### Restart

```bash
docker-compose restart
```

### Stop

```bash
docker-compose down
```

### Update to latest version

```bash
git pull
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

### Check status

```bash
docker-compose ps
```

---

## Troubleshooting

### Container won't start

```bash
# Check logs
docker-compose logs

# Check if port is in use
sudo lsof -i :5000
```

### Out of disk space

```bash
# Check disk usage
df -h

# Clean old Docker data
docker system prune -a
```

### Database locked

```bash
# Restart the container
docker-compose restart
```

### Reset everything (⚠️ deletes all data)

```bash
docker-compose down -v
rm -rf ./data
docker-compose up -d
```

---

## Security Notes

1. **Change SECRET_KEY** - Never use the default
2. **Firewall** - Only expose port 5000 if needed, prefer reverse proxy
3. **Updates** - Keep Docker and the app updated
4. **Backups** - Regularly backup `./data/` directory
