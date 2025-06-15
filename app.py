import streamlit as st
import numpy as np
import tempfile
import os
import librosa
from moviepy.editor import VideoFileClip
import warnings
import time
import cv2
from pydub import AudioSegment
import io

# Solución para error de pyaudioop
try:
    import pyaudioop
except ImportError:
    pass

# Configuración de página
st.set_page_config(
    page_title="🎬 AutoZoom Pro",
    page_icon="🎬",
    layout="wide"
)

# Ocultar warnings
warnings.filterwarnings("ignore")

# Interfaz de usuario
st.title("🎬 AutoZoom Pro - Editor Inteligente")
st.subheader("Zoom automático profesional basado en tu voz")
st.markdown("""
<style>
.stProgress > div > div > div > div {
    background-color: #4CAF50;
}
</style>
""", unsafe_allow_html=True)

# Parámetros ajustables
zoom_intensity = st.sidebar.slider("Intensidad de Zoom", 1.0, 1.5, 1.1, 0.01)
sensitivity = st.sidebar.slider("Sensibilidad de Voz", 0.1, 0.9, 0.3, 0.05)
smoothness = st.sidebar.slider("Suavidad", 0.1, 1.0, 0.5, 0.05)

# Subida de archivos
uploaded_file = st.file_uploader(
    "Sube tu video (MP4, MOV, AVI)",
    type=["mp4", "mov", "avi"],
    accept_multiple_files=False
)

def analyze_audio(audio_bytes):
    """Analiza el audio usando librosa"""
    try:
        # Cargar audio directamente desde bytes
        y, sr = librosa.load(io.BytesIO(audio_bytes), sr=16000, mono=True)
        
        # Calcular volumen normalizado
        volume = np.abs(y)
        if volume.max() > 0:
            volume = volume / volume.max()
        
        # Detección de voz adaptativa
        is_speech = volume > sensitivity
        
        # Suavizado inteligente
        zoom_profile = []
        current_zoom = 1.0
        transition_speed = 0.05 * (1/smoothness)
        
        for i in range(0, len(is_speech), 1000):
            window = is_speech[i:i+1000]
            if len(window) == 0:
                continue
                
            if np.mean(window) > 0.3:  # Segmento con voz
                target_zoom = zoom_intensity
            else:  # Silencio
                target_zoom = 1.0
                
            current_zoom += (target_zoom - current_zoom) * transition_speed
            zoom_profile.append(current_zoom)
        
        return zoom_profile
        
    except Exception as e:
        st.error(f"Error en análisis de audio: {str(e)}")
        return [1.0] * 100  # Perfil plano como respaldo

def extract_audio_from_video(video_bytes):
    """Extrae audio usando Pydub"""
    try:
        # Crear archivo temporal en memoria
        video_file = io.BytesIO(video_bytes)
        video_file.name = "temp_video.mp4"
        
        # Cargar video con Pydub
        audio = AudioSegment.from_file(video_file, format="mp4")
        
        # Convertir a mono y 16kHz
        audio = audio.set_channels(1).set_frame_rate(
