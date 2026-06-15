# Server-Setup: Raspberry Pi + PostgreSQL + Tailscale

Zentraler Datenbankserver für Min Guata Lada.
Alle drei Standorte (Bludenz, Feldkirch, Dornbirn) greifen über ein Tailscale-VPN auf denselben PostgreSQL-Server zu.

---

## Voraussetzungen

| Komponente | Empfehlung |
|---|---|
| Raspberry Pi | Pi 4 oder Pi 5, ≥ 4 GB RAM |
| Betriebssystem | Raspberry Pi OS Lite 64-bit (Debian Bookworm) |
| Speicher | ≥ 32 GB SD-Karte oder besser USB-SSD |
| Netzwerk | Feste LAN-IP im Heimnetz (DHCP-Reservierung empfohlen) |
| Strom | Unterbrechungsfreie Stromversorgung (USV) empfohlen |

---

## 1. Raspberry Pi OS einrichten

```bash
# Nach dem ersten Boot: System aktualisieren
sudo apt update && sudo apt full-upgrade -y
sudo apt install -y curl wget gnupg2 lsb-release

# Hostname setzen (optional)
sudo hostnamectl set-hostname mgl-server
```

---

## 2. PostgreSQL installieren

```bash
# Offizielles PostgreSQL-Repository (aktuelle Version)
sudo apt install -y postgresql postgresql-contrib

# Dienst starten und beim Boot aktivieren
sudo systemctl enable --now postgresql

# Prüfen ob PostgreSQL läuft
sudo systemctl status postgresql
```

---

## 3. Datenbank und Benutzer anlegen

```bash
# Als postgres-User einloggen
sudo -u postgres psql
```

Im psql-Prompt:

```sql
-- Datenbank anlegen
CREATE DATABASE minguatalada
    ENCODING 'UTF8'
    LC_COLLATE 'de_AT.UTF-8'
    LC_CTYPE 'de_AT.UTF-8'
    TEMPLATE template0;

-- Dedizierter Anwendungsbenutzer (KEIN Superuser!)
CREATE USER mgl_user WITH PASSWORD 'SICHERES_LANGES_PASSWORT';

-- Nur Rechte auf die Anwendungsdatenbank
GRANT CONNECT ON DATABASE minguatalada TO mgl_user;
\c minguatalada
GRANT USAGE, CREATE ON SCHEMA public TO mgl_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO mgl_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO mgl_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT ALL ON TABLES TO mgl_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT ALL ON SEQUENCES TO mgl_user;

\q
```

---

## 4. PostgreSQL absichern

### 4.1 Nur localhost + Tailscale lauschen

```bash
# Tailscale-IP des Pi herausfinden (nach Schritt 5)
# z.B. 100.64.1.1

sudo nano /etc/postgresql/*/main/postgresql.conf
```

Zeile ändern:
```
listen_addresses = 'localhost,100.64.1.1'
```

### 4.2 pg_hba.conf — nur Tailscale-Subnetz zulassen

```bash
sudo nano /etc/postgresql/*/main/pg_hba.conf
```

Am Ende anfügen (bestehende Zeilen NICHT löschen):
```
# Min Guata Lada: nur Tailscale-VPN-Subnetz, starke Authentifizierung
host    minguatalada   mgl_user   100.64.0.0/10   scram-sha-256
```

```bash
# PostgreSQL neu starten
sudo systemctl restart postgresql
```

### 4.3 Kein Port-Forwarding am Router!

PostgreSQL lauscht **nur** auf localhost und der Tailscale-IP.
Port 5432 wird **niemals** am Router weitergeleitet.
Die Verbindung läuft ausschliesslich über das verschlüsselte Tailscale-VPN.

---

## 5. Tailscale installieren

```bash
# Tailscale-Installation (offizielles Skript)
curl -fsSL https://tailscale.com/install.sh | sh

# Pi dem Tailscale-Netzwerk hinzufügen
sudo tailscale up

# Tailscale-IP des Pi anzeigen
tailscale ip -4
# Beispiel: 100.64.1.1
```

Auf jedem **Client-PC** (Standorte Bludenz / Feldkirch / Dornbirn):
```bash
# Tailscale Desktop-App installieren und einloggen
# https://tailscale.com/download
```

Alle Geräte müssen im selben Tailscale-Konto oder -Netzwerk angemeldet sein.

---

## 6. Schema initialisieren

Auf einem Client-PC (mit Tailscale-Verbindung zum Pi):

```bash
# Verbindung testen
psql postgresql://mgl_user:PASSWORT@100.64.1.1:5432/minguatalada -c "SELECT version();"

# Schema anlegen (idempotent — sicher wiederholbar)
psql postgresql://mgl_user:PASSWORT@100.64.1.1:5432/minguatalada \
     -f database/schema_postgres.sql
```

---

## 7. Datenmigration SQLite → PostgreSQL

Das Skript liest die bestehende SQLite-Datei READ-ONLY und überträgt alle Daten:

```bash
# Erst Trockenlauf: nichts schreiben, nur prüfen
python scripts/migrate_sqlite_to_postgres.py \
    --sqlite data/system.db \
    --pg postgresql://mgl_user:PASSWORT@100.64.1.1:5432/minguatalada \
    --dry-run

# Echte Migration (einmalig ausführen)
python scripts/migrate_sqlite_to_postgres.py \
    --sqlite data/system.db \
    --pg postgresql://mgl_user:PASSWORT@100.64.1.1:5432/minguatalada
```

---

## 8. Anwendung konfigurieren

Auf jedem Client-PC: `.env`-Datei im Projektverzeichnis anlegen
(Vorlage: `.env.example`):

```env
DATABASE_URL=postgresql://mgl_user:PASSWORT@100.64.1.1:5432/minguatalada
APP_SECRET_KEY=langer-zufaelliger-string
```

Alternativ als Systemumgebungsvariable (für den installierten Frozen-Build):

```
setx DATABASE_URL "postgresql://mgl_user:PASSWORT@100.64.1.1:5432/minguatalada"
setx APP_SECRET_KEY "langer-zufaelliger-string"
```

---

## 9. Automatische Backups auf dem Pi

```bash
# Backup-Skript anlegen
sudo nano /usr/local/bin/mgl-backup.sh
```

```bash
#!/bin/bash
set -euo pipefail
BACKUP_DIR="/var/backups/minguatalada"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
mkdir -p "$BACKUP_DIR"

pg_dump --format=custom \
        --file "$BACKUP_DIR/backup_${TIMESTAMP}.pgdump" \
        postgresql://mgl_user:PASSWORT@localhost:5432/minguatalada

# Ältere Backups löschen (nur 10 behalten)
ls -t "$BACKUP_DIR"/backup_*.pgdump | tail -n +11 | xargs -r rm

echo "Backup abgeschlossen: backup_${TIMESTAMP}.pgdump"
```

```bash
sudo chmod +x /usr/local/bin/mgl-backup.sh

# Tägliches Backup um 02:00 Uhr via cron
(crontab -l 2>/dev/null; echo "0 2 * * * /usr/local/bin/mgl-backup.sh >> /var/log/mgl-backup.log 2>&1") | crontab -
```

### Backup wiederherstellen

```bash
pg_restore --clean --if-exists \
           --dbname postgresql://mgl_user:PASSWORT@localhost:5432/minguatalada \
           /var/backups/minguatalada/backup_YYYYMMDD_HHMMSS.pgdump
```

---

## 10. Monitoring & Wartung

### PostgreSQL-Status prüfen
```bash
sudo systemctl status postgresql
sudo -u postgres psql -c "SELECT COUNT(*) FROM pg_stat_activity;"
```

### Tailscale-Verbindung prüfen
```bash
tailscale status
tailscale ping 100.64.x.x   # Client-PC-IP zum Testen
```

### Speicherplatz überwachen
```bash
df -h
sudo -u postgres psql minguatalada -c "SELECT pg_size_pretty(pg_database_size('minguatalada'));"
```

### PostgreSQL-Logs
```bash
sudo tail -f /var/log/postgresql/postgresql-*-main.log
```

---

## 11. Troubleshooting

| Problem | Mögliche Ursache | Lösung |
|---|---|---|
| `connection refused` | PostgreSQL hört nicht auf Tailscale-IP | `listen_addresses` in postgresql.conf prüfen, `systemctl restart postgresql` |
| `pg_hba.conf: no entry` | Tailscale-IP nicht in pg_hba.conf | Eintrag `host minguatalada mgl_user 100.64.0.0/10 scram-sha-256` prüfen |
| `SCRAM authentication failed` | Falsches Passwort oder alter Client | Passwort in `.env` prüfen; psycopg3 >= 3.1 verwenden |
| `timeout` nach VPN-Trennung | VPN-Unterbrechung | Tailscale automatisch neu verbunden; App neu starten |
| `Pool erschöpft` | Zu viele gleichzeitige Verbindungen | `max_size` in `_get_pool()` erhöhen; `max_connections` in postgresql.conf anpassen |

---

## Sicherheits-Checkliste

- [ ] `mgl_user` hat **kein** `SUPERUSER`-Recht
- [ ] PostgreSQL hört **nur** auf `localhost` und Tailscale-IP
- [ ] Port 5432 ist **nicht** am Router weitergeleitet
- [ ] pg_hba.conf erlaubt nur Tailscale-Subnetz `100.64.0.0/10`
- [ ] Authentifizierung: `scram-sha-256` (kein `md5`, kein `trust`)
- [ ] `.env`-Datei ist in `.gitignore` und nicht in Git
- [ ] Tägliche Backups laufen (cron prüfen: `crontab -l`)
- [ ] Raspberry Pi OS hat aktuelle Sicherheitsupdates (`apt upgrade`)
- [ ] Tailscale-MFA aktiviert (Tailscale-Admin-Panel)
