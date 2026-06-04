#!/bin/bash
# Configuració: base de datos, carpeta de destino y días de retención
DB_USER="root"
DB_PASS=""
DB_NAME="glpi"
BACKUP_DIR="/opt/backups_glpi"
FECHA=$(date +%Y-%m-%d_%H-%M)
ARCHIVO="$BACKUP_DIR/glpi_backup_$FECHA.sql.gz"
DIAS_RETENCION=7

# Crea la carpeta si no existe
mkdir -p $BACKUP_DIR

# Vuelca la base de datos y la comprime con gzip
mysqldump -u $DB_USER $DB_NAME | gzip > $ARCHIVO

# Comprueba si el backup se creó correctamente
if [ $? -eq 0 ]; then
    echo "[$FECHA] Backup creado: $ARCHIVO"
else
    echo "[$FECHA] ERROR: el backup fallo"
    exit 1
fi

# Borra los backups con más de 7 días de antigüedad
find $BACKUP_DIR -name "*.sql.gz" -mtime +$DIAS_RETENCION -delete
echo "[$FECHA] Limpieza completada"

# Sube los backups a la nube que he utilizado mediante rclone
rclone copy /opt/backups_glpi/ dropbox:backups_glpi
echo "[$FECHA] Backup subido a Dropbox correctamente"
