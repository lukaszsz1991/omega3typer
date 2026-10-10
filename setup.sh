#!/usr/bin/env bash
# Skrypt przygotowuje projekt do uruchomienia na Ubuntu/Debian:
# pakiety systemowe, środowisko wirtualne, baza PostgreSQL, plik .env i migracje.
# Można go bezpiecznie uruchamiać ponownie.

set -eo pipefail

cd "$(dirname "$0")"

DB_NAME="omega3typer"
DB_USER="omega3user"

# Polecenia dla użytkownika postgres, uruchamiane z katalogu /tmp,
# żeby uniknąć ostrzeżeń o braku dostępu do bieżącego katalogu.
pg() { (cd /tmp && sudo -u postgres "$@"); }

echo "==> Pakiety systemowe (wymaga sudo)"
sudo apt update
sudo apt install -y python3 python3-venv python3-pip git postgresql postgresql-contrib libpq-dev

echo "==> Środowisko wirtualne i zależności"
if [ ! -d venv ]; then
    python3 -m venv venv
fi
source venv/bin/activate
pip install -r requirements.txt

echo "==> Plik .env"
if [ -f .env ]; then
    echo "    .env już istnieje, zostawiam bez zmian"
    DB_PASSWORD="$(grep '^DB_PASSWORD=' .env | cut -d= -f2-)"
else
    SECRET_KEY="$(python -c 'import secrets; print(secrets.token_urlsafe(50))')"
    DB_PASSWORD="$(python -c 'import secrets; print(secrets.token_urlsafe(16))')"
    cat > .env <<EOF
SECRET_KEY=${SECRET_KEY}
DEBUG=True
DB_NAME=${DB_NAME}
DB_USER=${DB_USER}
DB_PASSWORD=${DB_PASSWORD}
DB_HOST=localhost
DB_PORT=5432
EOF
    echo "    utworzono .env z losowym kluczem i hasłem"
fi

if [ -z "$DB_PASSWORD" ]; then
    echo "Błąd: brak DB_PASSWORD w pliku .env" >&2
    exit 1
fi

echo "==> Baza danych PostgreSQL"
if pg psql -tAc "SELECT 1 FROM pg_roles WHERE rolname='${DB_USER}'" | grep -q 1; then
    pg psql -c "ALTER USER ${DB_USER} WITH PASSWORD '${DB_PASSWORD}';"
else
    pg psql -c "CREATE USER ${DB_USER} WITH PASSWORD '${DB_PASSWORD}';"
fi

if ! pg psql -tAc "SELECT 1 FROM pg_database WHERE datname='${DB_NAME}'" | grep -q 1; then
    pg psql -c "CREATE DATABASE ${DB_NAME} OWNER ${DB_USER};"
fi

# Uprawnienia wymagane w PostgreSQL 15 i nowszych oraz do testów Django
pg psql -c "ALTER DATABASE ${DB_NAME} OWNER TO ${DB_USER};"
pg psql -d "${DB_NAME}" -c "GRANT ALL ON SCHEMA public TO ${DB_USER};"
pg psql -c "ALTER USER ${DB_USER} CREATEDB;"

echo "==> Migracje"
python manage.py migrate

echo
echo "Gotowe. Kolejne kroki:"
echo "  source venv/bin/activate"
echo "  python manage.py createsuperuser"
echo "  python manage.py runserver"