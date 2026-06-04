from flask import Flask, render_template, request, redirect, url_for, session  # Importa lo necesario de Flask
from ldap3 import Server, Connection, ALL, Tls  # Importa clases de ldap3
import requests, ssl  # Librerías para HTTP y SSL

app = Flask(__name__)  # Crea la app Flask
# Clave secreta para gestionar las sesiones de usuario
app.secret_key = "CLAVE_SECRETA_PARA_FIRMAR_COOKIES"  # Clave para firmar las cookies de sesión

# Dirección de la API de GLPI y tokens de autenticación
GLPI_URL   = "https://192.168.1.171/apirest.php"  # URL de la API de GLPI
APP_TOKEN  = "TU_APP_TOKEN_AQUI"  # Token de la aplicación
USER_TOKEN = "TU_USER_TOKEN_AQUI"  # Token del usuario de GLPI

# Datos del servidor LDAP donde están los usuarios de la empresa
LDAP_HOST  = "192.168.100.10"  # IP del servidor LDAP
LDAP_PORT  = 389  # Puerto LDAP sin cifrar
LDAP_BASE  = "dc=empresa,dc=local"  # DN base del directorio

# Token del bot de Telegram y Chat ID del técnico que recibe los avisos
TELEGRAM_TOKEN   = "TU_TELEGRAM_TOKEN_AQUI"  # Token del bot de Telegram
TELEGRAM_CHAT_ID = "TU_CHAT_ID_AQUI"  # ID del chat del técnico

# Relación entre el nombre de la categoría y su ID numérico en GLPI
CATEGORIAS = {  # Diccionario nombre → ID de categoría en GLPI
    "Hardware":           3,  # Hardware = ID 3
    "Software":           4,  # Software = ID 4
    "Red y conectividad": 2,  # Red = ID 2
    "Accesos y permisos": 1,  # Accesos = ID 1
    "Otro":               0   # Otro = ID 0
}

# Palabras que indican urgencia muy alta
PALABRAS_MUY_ALTA = [  # Palabras que disparan urgencia 5
    "caído", "caido", "no funciona", "sin acceso", "urgente",
    "crítico", "critico", "no arranca", "bloqueado", "perdido",
    "virus", "hackeado", "no puedo trabajar", "parado"
]

# Palabras que indican urgencia alta
PALABRAS_ALTA = [  # Palabras que disparan urgencia 4
    "fallo", "error", "no abre", "no carga", "lento",
    "problema grave", "no responde", "pantalla azul", "se cuelga"
]

# Palabras que indican urgencia media
PALABRAS_MEDIA = [  # Palabras que disparan urgencia 3
    "problema", "no puedo", "necesito ayuda", "no me deja",
    "no funciona bien", "a veces falla", "intermitente"
]

# Texto que se muestra al usuario y se manda por Telegram
URGENCIA_TEXTO = {  # Traduce número de urgencia a texto
    5: "Muy alta",
    4: "Alta",
    3: "Media",
    2: "Baja",
    1: "Muy baja"
}

def calcular_urgencia(titulo, descripcion):  # Función que calcula la urgencia del ticket
    # Junta el título y la descripción en minúsculas para buscar
    # las palabras clave sin distinguir mayúsculas y minúsculas
    texto = (titulo + " " + descripcion).lower()  # Une título y descripción en minúsculas
    for palabra in PALABRAS_MUY_ALTA:  # Busca palabras de urgencia muy alta
        if palabra in texto:  # Si encuentra una...
            return 5  # ...devuelve 5
    for palabra in PALABRAS_ALTA:  # Busca palabras de urgencia alta
        if palabra in texto:
            return 4  # Devuelve 4
    for palabra in PALABRAS_MEDIA:  # Busca palabras de urgencia media
        if palabra in texto:
            return 3  # Devuelve 3
    return 2  # Por defecto, urgencia baja

def enviar_telegram(ticket_id, titulo, urgencia, categoria, usuario):  # Función que avisa al técnico
    # Construye el mensaje y lo manda al técnico por Telegram
    texto = (  # Construye el mensaje con los datos del ticket
        f"🔔 Nuevo ticket #{ticket_id}\n"
        f"👤 Usuario: {usuario}\n"
        f"📋 Título: {titulo}\n"
        f"🏷️ Categoría: {categoria}\n"
        f"⚡ Urgencia: {URGENCIA_TEXTO.get(urgencia, urgencia)}"  # Pasa la urgencia a texto
    )
    try:  # Intenta enviar el mensaje
        requests.post(  # POST a la API de Telegram
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            json={"chat_id": TELEGRAM_CHAT_ID, "text": texto}  # Envía chat y texto en JSON
        )
    except Exception as e:  # Si falla...
        print(f"Error Telegram: {e}")  # ...imprime el error sin parar la app

def autenticar_ldap(usuario, password):  # Función que valida usuario/contraseña en LDAP
    # Valida las credenciales contra el directorio LDAP
    try:
        srv  = Server(LDAP_HOST, port=LDAP_PORT, get_info=ALL)  # Define el servidor LDAP
        dn   = f"cn={usuario},ou=usuarios,{LDAP_BASE}"  # Monta el DN completo del usuario
        conn = Connection(srv, user=dn, password=password, auto_bind=True)  # Intenta hacer bind
        return conn.bound  # Devuelve True si el bind es correcto
    except Exception as e:  # Si falla el bind...
        print(f"Error LDAP: {e}")  # ...muestra el error
        return False  # ...y devuelve False

def crear_ticket_glpi(titulo, descripcion, urgencia, categoria):  # Función que crea el ticket vía API
    # Paso 1: inicia sesión en la API de GLPI
    r = requests.get(f"{GLPI_URL}/initSession", verify=False,  # Llama a initSession (sin verificar SSL)
        headers={"Authorization": f"user_token {USER_TOKEN}",  # Cabecera con el user token
                 "App-Token": APP_TOKEN})  # Cabecera con el app token
    st = r.json()["session_token"]  # Guarda el session_token devuelto

    # Paso 2: crea el ticket con la urgencia calculada automáticamente
    r2 = requests.post(f"{GLPI_URL}/Ticket", verify=False,  # POST al endpoint /Ticket
         headers={"Session-Token": st, "App-Token": APP_TOKEN,  # Cabeceras con los tokens
                  "Content-Type": "application/json"},  # Indica que el cuerpo va en JSON
         json={"input": {"name": titulo, "content": descripcion,  # Datos del ticket dentro de input
                         "urgency": int(urgencia), "type": 1,  # urgency 1-5; type 1 = Incidencia
                         "itilcategories_id": CATEGORIAS.get(categoria, 0)}})  # ID de categoría

    # Paso 3: cierra la sesión en la API
    requests.get(f"{GLPI_URL}/killSession", verify=False,  # Cierra la sesión de la API
        headers={"Session-Token": st, "App-Token": APP_TOKEN})

    # Devuelve el ID del ticket creado
    resultado = r2.json()  # Convierte la respuesta a objeto Python
    if isinstance(resultado, list):  # Si la respuesta es una lista...
        return resultado[0].get("id")  # ...devuelve el id del primer elemento
    return resultado.get("id")  # Si es un dict, devuelve el id directamente

@app.route("/", methods=["GET", "POST"])  # Ruta raíz, acepta GET y POST
def login():
    # Muestra el login y valida las credenciales contra LDAP
    error = None  # Variable para el mensaje de error
    if request.method == "POST":  # Si se ha enviado el formulario...
        u = request.form["usuario"]  # Lee el usuario
        p = request.form["password"]  # Lee la contraseña
        if autenticar_ldap(u, p):  # Si las credenciales son válidas...
            session["usuario"] = u  # ...guarda el usuario en la sesión
            return redirect(url_for("ticket"))  # ...y redirige a /ticket
        error = "Usuario o contrasena incorrectos"  # Si no, prepara el error
    return render_template("login.html", error=error)  # Renderiza el formulario de login

@app.route("/ticket", methods=["GET", "POST"])  # Ruta del formulario de ticket
def ticket():
    # Si no ha iniciado sesión lo manda al login
    if "usuario" not in session:  # Si no hay sesión activa...
        return redirect(url_for("login"))  # ...redirige al login
    ticket_id = None  # Inicializa el ID del ticket
    urgencia_asignada = None  # Inicializa la urgencia
    if request.method == "POST":  # Si se envía el formulario...
        titulo      = request.form["titulo"]  # Lee el título
        descripcion = request.form["descripcion"]  # Lee la descripción
        categoria   = request.form.get("categoria", "Otro")  # Lee la categoría (por defecto "Otro")
        # Calcula la urgencia automáticamente
        urgencia_asignada = calcular_urgencia(titulo, descripcion)  # Calcula la urgencia del ticket
        # Crea el ticket en GLPI
        ticket_id = crear_ticket_glpi(titulo, descripcion,  # Crea el ticket en GLPI
                                      urgencia_asignada, categoria)
        # Avisa al técnico por Telegram
        if ticket_id:  # Si el ticket se ha creado...
            enviar_telegram(ticket_id, titulo, urgencia_asignada,  # ...manda aviso por Telegram
                          categoria, session["usuario"])
    return render_template("ticket.html",  # Renderiza el formulario con los datos
                           usuario=session["usuario"],
                           ticket_id=ticket_id,
                           urgencia=urgencia_asignada)

@app.route("/logout")  # Ruta para cerrar sesión
def logout():
    # Borra la sesión y manda al login
    session.clear()  # Borra los datos de sesión
    return redirect(url_for("login"))  # Redirige al login

if __name__ == "__main__":  # Si el script se ejecuta directamente...
    # Arranca Flask escuchando en todas las interfaces en el puerto 8080
    app.run(host="0.0.0.0", port=8080, debug=False)  # Arranca Flask en 0.0.0.0:8080 
