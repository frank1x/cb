import os
import signal
import requests
import subprocess
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__)

# Diccionario para almacenar PIDs de procesos activos
active_downloads = {}

# Verificar si la carpeta 'Videos' existe, si no crearla
def ensure_videos_folder():
    if not os.path.exists("Videos"):
        os.makedirs("Videos")

# Verificar si una modelo está en línea y obtener la URL de la transmisión
def is_model_online(model_username):
    try:
        url = f"https://chaturbate.com/api/chatvideocontext/{model_username}/"
        response = requests.get(url)

        if response.status_code == 200:
            data = response.json()
            if data.get("room_status") == "public":
                playlist_url = data.get("hls_source")
                if playlist_url:
                    playlist_url = playlist_url.replace("live-hls", "live-fhls").replace("playlist.m3u8", "playlist_sfm4s.m3u8")
                    return True, playlist_url
            return False, None
        return False, None
    except Exception as e:
        print(f"⚠️ Error al verificar el estado de la modelo '{model_username}': {e}")
        return False, None

# Iniciar la descarga de la transmisión de la modelo
def start_stream_download(model_username, playlist_url):
    try:
        # Evitar duplicados
        if model_username in active_downloads:
            print(f"⚠️ Ya hay una descarga activa para '{model_username}'.")
            return

        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        output_filename = f"Videos/{model_username}_{timestamp}.mp4"
        command = [
            "./streamlink.AppImage", playlist_url, "best",
            "-o", output_filename
        ]

        # Iniciar el proceso en un grupo propio para detenerlo fácilmente
        process = subprocess.Popen(command, preexec_fn=os.setsid)
        active_downloads[model_username] = process.pid
        print(f"📥 Descarga iniciada para '{model_username}' en el archivo: {output_filename}")

    except Exception as e:
        print(f"⚠️ Error al descargar la transmisión de '{model_username}': {e}")

# Pausar la descarga de la transmisión de la modelo
def pause_stream_download(model_username):
    pid = active_downloads.get(model_username)
    if pid:
        try:
            os.killpg(os.getpgid(pid), signal.SIGTERM)
            print(f"⏸️ Descarga pausada para '{model_username}'.")
            del active_downloads[model_username]
        except Exception as e:
            print(f"⚠️ Error al pausar la descarga de '{model_username}': {e}")
    else:
        print(f"⚠️ No hay descargas activas para '{model_username}'.")

# Leer los nombres de las modelos desde el archivo 'modelos.txt'
def read_models(filename="modelos.txt"):
    if not os.path.exists(filename):
        return []
    with open(filename, "r") as file:
        return [line.strip() for line in file if line.strip()]

# Agregar una modelo a la lista de modelos
def add_model(model_username, filename="modelos.txt"):
    models = read_models(filename)
    if model_username not in models:
        with open(filename, "a") as file:
            file.write(model_username + "\n")
        print(f"✅ Modelo '{model_username}' agregada a la lista.")
    else:
        print(f"⚠️ La modelo '{model_username}' ya está en la lista.")

@app.route('/')
def index():
    models = read_models()
    online_models = []
    for model in models:
        online, playlist_url = is_model_online(model)
        downloading = model in active_downloads
        online_models.append((model, online, playlist_url, downloading))
    return render_template("index.html", models=online_models)

@app.route('/add', methods=['POST'])
def add():
    model_url = request.form.get("model_url")
    if model_url:
        model_username = model_url.rstrip('/').split('/')[-1]
        add_model(model_username)
        online, playlist_url = is_model_online(model_username)
        if online:
            start_stream_download(model_username, playlist_url)
    return redirect(url_for('index'))

@app.route('/download', methods=['POST'])
def download():
    model_username = request.form.get("model")
    playlist_url = request.form.get("url")
    start_stream_download(model_username, playlist_url)
    return redirect(url_for('index'))

@app.route('/pause', methods=['POST'])
def pause():
    model_username = request.form.get("model")
    pause_stream_download(model_username)
    return redirect(url_for('index'))

if __name__ == "__main__":
    ensure_videos_folder()
    app.run(host="0.0.0.0", port=5000, debug=True)
