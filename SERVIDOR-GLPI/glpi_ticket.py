import requests
import sys

# Aquí guardamos la dirección de GLPI y las dos claves que necesitamos
# para que la API nos deje entrar
GLPI_URL   = "http://192.168.1.169/apirest.php"
APP_TOKEN  = "TU_APP_TOKEN_AQUI"
USER_TOKEN = "TU_USER_TOKEN_AQUI"

def iniciar_sesion():
    # Le decimos a GLPI que queremos empezar a trabajar
    # y nos devuelve un ticket de sesión temporal
    r = requests.get(
        f"{GLPI_URL}/initSession",
        headers={
            "Authorization": f"user_token {USER_TOKEN}",
            "App-Token": APP_TOKEN
        }
    )
    r.raise_for_status()
    return r.json()["session_token"]

def cerrar_sesion(st):
    # Cuando terminamos, cerramos la sesión para no dejarla abierta
    requests.get(
        f"{GLPI_URL}/killSession",
        headers={"Session-Token": st, "App-Token": APP_TOKEN}
    )

def crear_ticket(titulo, descripcion, urgencia=3):
    # Valores posibles de urgencia:
    # 1=Muy baja  2=Baja  3=Media  4=Alta  5=Muy alta
    st = iniciar_sesion()
    try:
        # Mandamos el ticket a GLPI con todos sus datos
        r = requests.post(
            f"{GLPI_URL}/Ticket",
            headers={
                "Session-Token": st,
                "App-Token": APP_TOKEN,
                "Content-Type": "application/json"
            },
            json={"input": {
                "name":    titulo, # Título del ticket
                "content": descripcion, # Descripción el ticket
                "urgency": int(urgencia), # Nivel de irgencia
                "type":    1 # 1 = Número de incidencia
            }}
        )
        # Mostramos el número de ticket que nos ha asignado GLPI
        tid = r.json().get("id", "ERROR")
        print(f"[OK] Ticket #{tid} creado: {titulo}")
    finally:
        # Cerramos la sesión pase lo que pase, aunque haya fallado algo
        cerrar_sesion(st)

# Desde aquí arranca el script cuando lo ejecutamos desde la terminal
# Podemos pasarle el título, la descripción y la urgencia como parámetros
# Si no ponemos nada usa los valores por defecto
if __name__ == "__main__":
    titulo = sys.argv[1] if len(sys.argv) > 1 else "Alerta automatica"
    desc   = sys.argv[2] if len(sys.argv) > 2 else "Incidencia detectada automaticamente"
    urg    = int(sys.argv[3]) if len(sys.argv) > 3 else 3
    crear_ticket(titulo, desc, urg)
