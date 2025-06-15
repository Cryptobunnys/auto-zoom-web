import streamlit as st
import numpy as np
import subprocess
import tempfile
import os
from pydub import AudioSegment
from moviepy.editor import VideoFileClip

st.set_page_config(page_title="AutoZoom Pro", page_icon="🎬", layout="wide")

# Configuración inicial
st.title("🎬 AutoZoom Pro")
st.subheader("Zoom automático basado en tu voz - Para creadores de contenido")
st.markdown("Sube tu video en primera persona y la herramienta aplicará zooms profesionales automáticamente")

# Subida de archivos
uploaded_file = st.file_uploader("Sube tu video MP4", type=["mp4"])

# Parámetros ajustables
st.sidebar.header("Configuración de Zoom")
zoom_intensity = st.sidebar.slider("Intensidad del Zoom", 1.0, 1.3, 1.1, 0.01)
sensitivity = st.sidebar.slider("Sensibilidad de Voz", 0.1, 0.9, 0.3, 0.05)

def analyze_audio(audio_path):
    audio = AudioSegment.from_file(audio_path)
    audio.export("temp_audio.wav", format="wav")
    
    # Leer audio
    sample_rate, data = np.memmap("temp_audio.wav", dtype='h', mode='r', offset=44)
    
    # Calcular volumen
    volume = np.abs(data).astype(float)
    volume = volume / np.max(volume)
    
    # Detectar voz
    is_speech = volume > sensitivity
    
    # Calcular zoom
    zoom_points = []
    current_zoom = 1.0
    for i in range(0, len(is_speech), 1000):
        window = is_speech[i:i+1000]
        if len(window) == 0: continue
            
        if np.mean(window) > 0.3:  # Segmento con voz
            current_zoom = max(zoom_intensity, min(current_zoom + 0.02, zoom_intensity + 0.1))
        else:  # Silencio
            current_zoom = min(1.0, max(current_zoom - 0.02, zoom_intensity))
        zoom_points.append(current_zoom)
    
    os.remove("temp_audio.wav")
    return zoom_points

def process_video(input_path, output_path):
    # Extraer audio
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp_audio:
        temp_audio_path = tmp_audio.name
    
    subprocess.run(['ffmpeg', '-y', '-i', input_path, '-q:a', '0', '-map', 'a', temp_audio_path], check=True)
    
    # Analizar audio
    zoom_profile = analyze_audio(temp_audio_path)
    os.remove(temp_audio_path)
    
    # Procesar video
    clip = VideoFileClip(input_path)
    
    # Función de zoom
    def zoom_effect(get_frame, t):
        frame_index = min(int(t * 10), len(zoom_profile)-1)
        zoom_level = zoom_profile[frame_index]
        frame = get_frame(t)
        return frame * zoom_level
    
    zoom_clip = clip.fl(zoom_effect, apply_to=['mask'])
    
    # Exportar
    zoom_clip.write_videofile(
        output_path,
        codec='libx264',
        audio_codec='aac',
        fps=clip.fps,
        threads=4,
        preset='fast',
        logger=None
    )
    clip.close()

if uploaded_file is not None:
    st.video(uploaded_file)
    
    if st.button("✨ Aplicar Zoom Automático", type="primary"):
        with st.spinner('Procesando... esto puede tardar unos minutos'):
            # Guardar archivo temporal
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp_file:
                tmp_file.write(uploaded_file.getvalue())
                input_path = tmp_file.name
            
            output_path = "procesado_" + uploaded_file.name
            
            # Procesar
            process_video(input_path, output_path)
            
            # Mostrar resultado
            st.success("¡Video procesado con éxito!")
            st.video(output_path)
            
            # Descargar
            with open(output_path, "rb") as f:
                st.download_button(
                    label="⬇️ Descargar Video",
                    data=f,
                    file_name=output_path,
                    mime="video/mp4"
                )
            
            # Limpiar
            os.unlink(input_path)
            os.unlink(output_path)

st.markdown("---")
st.caption("AutoZoom Pro v1.0 | Para creadores de contenido")
