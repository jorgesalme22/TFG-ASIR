# TFG - Implantación de un Sistema de Gestión de Incidencias con GLPI

**Trabajo de Fin de Grado — Ciclo Formativo de Grado Superior en Administración de Sistemas Informáticos en Red (ASIR)**

---

## Descripción del proyecto

Este proyecto consiste en el diseño, implantación y configuración de un sistema completo de gestión de incidencias informáticas para una empresa ficticia, usando software libre. La infraestructura se ha desplegado en máquinas virtuales con Ubuntu Server e incluye:

- **GLPI** como sistema de tickets e inventario
- **OpenLDAP** para la autenticación centralizada de usuarios
- **Portal web Flask** para que los usuarios puedan abrir tickets desde el navegador
- **Bot de Telegram** para notificar al técnico en tiempo real
- **Apache + ModSecurity** como servidor web con WAF
- **BIND9** para resolución DNS interna
- **rclone + Dropbox** para copias de seguridad automáticas en la nube

---

## Estructura del repositorio

```
TFG/
├── SERVIDOR-GLPI/              # Configuración del servidor principal (GLPI + Apache + Portal)
│   ├── portal_tfg/             # Aplicación web Flask para apertura de tickets
│   │   ├── app.py              # Lógica principal: login LDAP, creación de tickets, Telegram
│   │   ├── nohup.out           # Salida de ejecución del servidor Flask
│   │   └── templates/
│   │       ├── login.html      # Plantilla de la página de login
│   │       └── ticket.html     # Plantilla del formulario de tickets
│   ├── glpi_ticket.py          # Script CLI para crear tickets vía API de GLPI
│   ├── config_db.php           # Configuración de conexión a la base de datos de GLPI
│   ├── backup_glpi.sh          # Script de backup automático con rclone a Dropbox
│   ├── rclone.conf             # Configuración de rclone para Dropbox
│   ├── glpi.conf               # VirtualHost de Apache para GLPI (HTTPS)
│   ├── portal.conf             # VirtualHost de Apache para el portal Flask
│   ├── apache2.conf            # Configuración global de Apache
│   ├── 000-default.conf        # VirtualHost por defecto de Apache
│   ├── default-ssl.conf        # Configuración SSL por defecto
│   ├── ports.conf              # Puertos en escucha de Apache
│   ├── modsecurity.conf        # Configuración de ModSecurity (WAF)
│   ├── security2.conf          # Módulo mod_security2 de Apache
│   ├── security.conf           # Cabeceras de seguridad HTTP
│   ├── crs-setup.conf          # Configuración del Core Rule Set (OWASP CRS)
│   ├── crontab_root.txt        # Tareas programadas del usuario root (backup)
│   ├── crontab_user.txt        # Tareas programadas del usuario del portal
│   ├── 50-cloud-init.yaml      # Configuración de red (Netplan)
│   ├── hostname                # Nombre del servidor
│   ├── hosts                   # Resolución de nombres local
│   ├── sshd_config             # Configuración del servidor SSH
│   └── info_versiones.txt      # Versiones del software instalado
│
└── SERVIDOR-LDAP/              # Configuración del servidor de directorio (LDAP + DNS)
    ├── directorio.ldif         # Estructura del directorio LDAP (usuarios y grupos)
    ├── slapd-config.ldif       # Configuración interna de OpenLDAP (cn=config)
    ├── ldap.conf               # Configuración del cliente LDAP
    ├── db.empresa.local        # Zona DNS directa (BIND9)
    ├── named.conf.local        # Definición de zonas en BIND9
    ├── named.conf.options      # Opciones globales de BIND9
    ├── 50-cloud-init.yaml      # Configuración de red (Netplan)
    ├── hostname                # Nombre del servidor
    ├── hosts                   # Resolución de nombres local
    └── sshd_config             # Configuración del servidor SSH
```

---

## Arquitectura de la infraestructura

```
                        ┌─────────────────────────────────┐
                        │         Red interna              │
                        │       192.168.100.0/24           │
                        └─────────────────────────────────┘
                               │                │
              ┌────────────────┘                └────────────────┐
              ▼                                                   ▼
 ┌─────────────────────────┐                    ┌──────────────────────────┐
 │    SERVIDOR GLPI         │                    │    SERVIDOR LDAP/DNS     │
 │   192.168.100.20         │                    │    192.168.100.10        │
 │                          │                    │                          │
 │  · GLPI (Apache/HTTPS)  │◄──── LDAP auth ────│  · OpenLDAP              │
 │  · Portal Flask :8080   │                    │  · BIND9 (DNS interno)   │
 │  · ModSecurity (WAF)    │                    │                          │
 │  · MariaDB               │                    └──────────────────────────┘
 │  · rclone → Dropbox     │
 └─────────────────────────┘
              │
              │ Notificaciones
              ▼
      ┌───────────────┐
      │  Bot Telegram  │
      └───────────────┘
```

---

## Tecnologías utilizadas

| Tecnología | Versión | Función |
|---|---|---|
| Ubuntu Server | 24.04 LTS | Sistema operativo base |
| GLPI | 10.x | Gestión de tickets e inventario |
| OpenLDAP | 2.5.x | Directorio de usuarios centralizado |
| Apache2 | 2.4.x | Servidor web |
| ModSecurity + OWASP CRS | 3.x / 4.x | Firewall de aplicaciones web (WAF) |
| MariaDB | 10.x | Base de datos de GLPI |
| BIND9 | 9.x | DNS interno |
| Python / Flask | 3.x / 3.x | Portal web para apertura de tickets |
| rclone | — | Copias de seguridad en la nube |

---

## Funcionalidades principales

### Portal web de tickets
Los usuarios de la empresa acceden a un portal web sencillo donde:
1. Se autentican con sus credenciales de LDAP
2. Rellenan un formulario con el título, descripción y categoría de la incidencia
3. El sistema calcula la **urgencia automáticamente** analizando palabras clave en el texto
4. El ticket se crea en GLPI vía API REST
5. El técnico recibe una **notificación por Telegram** al instante

### Autenticación centralizada con LDAP
Todos los usuarios del sistema se gestionan en un directorio OpenLDAP. El portal Flask valida las credenciales contra LDAP en cada inicio de sesión.

### Backups automáticos en la nube
Un script ejecutado por cron realiza cada noche un volcado de la base de datos de GLPI, lo comprime y lo sube a Dropbox mediante rclone. Los backups con más de 7 días se eliminan automáticamente.

### Seguridad con ModSecurity (WAF)
El servidor Apache tiene habilitado ModSecurity con el conjunto de reglas OWASP CRS para proteger GLPI de ataques web comunes (SQLi, XSS, etc.).

---

## Configuración necesaria antes de desplegar

Los archivos de configuración usan placeholders que debes sustituir por tus valores reales:

### `SERVIDOR-GLPI/portal_tfg/app.py`
```python
app.secret_key = "CLAVE_SECRETA_PARA_FIRMAR_COOKIES"   # Genera una clave aleatoria segura
GLPI_URL       = "https://IP_SERVIDOR_GLPI/apirest.php"
APP_TOKEN      = "TU_APP_TOKEN_AQUI"                   # Obtenido en GLPI > Configuración > API
USER_TOKEN     = "TU_USER_TOKEN_AQUI"                  # Obtenido en el perfil del usuario de GLPI
LDAP_HOST      = "IP_SERVIDOR_LDAP"
TELEGRAM_TOKEN   = "TU_TELEGRAM_TOKEN_AQUI"            # Token del bot de Telegram (@BotFather)
TELEGRAM_CHAT_ID = "TU_CHAT_ID_AQUI"                   # ID del chat del técnico
```

### `SERVIDOR-GLPI/config_db.php`
```php
public $dbpassword = 'tu_password_mariadb';  // Contraseña del usuario 'glpi' en MariaDB
```

### `SERVIDOR-GLPI/rclone.conf`
```
token = {"access_token":"TU_TOKEN_DE_DROPBOX_AQUI",...}  // Generado con: rclone config
```

### `SERVIDOR-LDAP/directorio.ldif` y `slapd-config.ldif`
Los campos `userPassword` y `olcRootPW` contienen el placeholder `HASH_SSHA_AQUI`.
Genera hashes reales con:
```bash
slappasswd -s tu_contraseña
```

---

## Autor

**Jorge Salmerón Carrasco**
Grado Superior en Administración de Sistemas Informáticos en Red (ASIR)
Curso 2025-2026
