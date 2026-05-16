# Install IncidentRelay on RedHat-like distributions from RPM repository

IncidentRelay provides an RPM repository for RedHat-like distributions such as RHEL, Rocky Linux, AlmaLinux and CentOS Stream.

Repository file:

```text
https://repo.incidentrelay.io/incidentrelay.repo
```

## 1. Install the repository file

For RHEL 9 / Rocky Linux 9 / AlmaLinux 9 / CentOS Stream 9 and newer:

```bash
sudo dnf install -y curl
sudo curl -fsSL \
  https://repo.incidentrelay.io/incidentrelay.repo \
  -o /etc/yum.repos.d/incidentrelay.repo

sudo dnf makecache
```

For older yum-based systems:

```bash
sudo yum install -y curl
sudo curl -fsSL \
  https://repo.incidentrelay.io/incidentrelay.repo \
  -o /etc/yum.repos.d/incidentrelay.repo

sudo yum makecache
```

## 2. Install IncidentRelay

```bash
sudo dnf install -y incidentrelay
```

Or with `yum`:

```bash
sudo yum install -y incidentrelay
```

The RPM package installs IncidentRelay into:

```text
/var/www/incidentrelay
```

Main configuration file:

```text
/etc/incidentrelay/incidentrelay.conf
```

Runtime data directory:

```text
/var/lib/incidentrelay
```

Log directory:

```text
/var/log/incidentrelay
```

System user:

```text
incidentrelay
```

## 3. Configure IncidentRelay

Edit the configuration file:

```bash
sudo vi /etc/incidentrelay/incidentrelay.conf
```

At minimum, review:

```ini
[server]
secret_key = change-me

[database]
type = sqlite
name = /var/lib/incidentrelay/incidentrelay.db
```

For PostgreSQL, use:

```ini
[database]
type = postgresql
host = 127.0.0.1
port = 5432
name = incidentrelay
user = incidentrelay
password = change-me
```

## 4. Run database migrations

The RPM package tries to run migrations during installation. If the database was not ready during install, run migrations manually after editing the config:

```bash
sudo -u incidentrelay \
  INCEDENTRELAY_CONFIG_FILE=/etc/incidentrelay/incidentrelay.conf \
  /var/www/incidentrelay/venv/bin/python \
  /var/www/incidentrelay/manage.py migrate
```

## 5. Create the first admin user

```bash
sudo -u incidentrelay \
  INCEDENTRELAY_CONFIG_FILE=/etc/incidentrelay/incidentrelay.conf \
  /var/www/incidentrelay/venv/bin/python \
  /var/www/incidentrelay/manage.py create-admin \
  --username admin \
  --password 'change-me-123' \
  --email admin@example.com
```

Change the password and email before using this command in production.

## 6. Start services

Enable and start the web service and scheduler:

```bash
sudo systemctl enable --now incidentrelay-web
sudo systemctl enable --now incidentrelay-scheduler
```

Check service status:

```bash
sudo systemctl status incidentrelay-web
sudo systemctl status incidentrelay-scheduler
```

Follow logs:

```bash
sudo journalctl -u incidentrelay-web -f
sudo journalctl -u incidentrelay-scheduler -f
```

## 7. Optional: start Telegram worker

Start this service only if Telegram bot polling/callback processing is used:

```bash
sudo systemctl enable --now incidentrelay-telegram-worker
```

Check logs:

```bash
sudo journalctl -u incidentrelay-telegram-worker -f
```

## 8. Upgrade IncidentRelay

```bash
sudo dnf update -y incidentrelay
```

Or with `yum`:

```bash
sudo yum update -y incidentrelay
```

After upgrade, run migrations if needed:

```bash
sudo -u incidentrelay \
  INCEDENTRELAY_CONFIG_FILE=/etc/incidentrelay/incidentrelay.conf \
  /var/www/incidentrelay/venv/bin/python \
  /var/www/incidentrelay/manage.py migrate
```

Then restart services:

```bash
sudo systemctl restart incidentrelay-web
sudo systemctl restart incidentrelay-scheduler
sudo systemctl restart incidentrelay-telegram-worker
```

If Telegram worker is not used, skip the last command.

## 9. Remove IncidentRelay

```bash
sudo dnf remove -y incidentrelay
```

Or with `yum`:

```bash
sudo yum remove -y incidentrelay
```

Configuration and runtime data may remain on disk depending on RPM removal policy. Check and remove manually if required:

```bash
sudo rm -rf /etc/incidentrelay
sudo rm -rf /var/lib/incidentrelay
sudo rm -rf /var/log/incidentrelay
```
