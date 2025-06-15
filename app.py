import streamlit as st
import numpy as np
import tempfile
import os
import librosa
from moviepy.editor import VideoFileClip, AudioFileClip
import warnings
import io
from pydub import AudioSegment
import time

# Configurar página
st.set_page_config(page_title="AutoZoom Pro", page_icon="🎬", layout="wide")
st.title("🎬 AutoZoom Pro - Zoom Automático para Videos")
st.subheader("Sube tu video y la herramienta aplicará zooms profesionales automáticamente")

# Ocultar warnings
warnings.filterwarnings("ignore")

# Subida de archivos
uploaded_file = st.file_uploader("Sube tu video MP4", type=["mp4"], accept_multiple_files=False)

# Parámetros ajustables
st.sidebar.header("⚙️ Configuración de Zoom")
zoom_intensity = st.sidebar.slider("Intensidad del Zoom", 1.0, 1.5, 1.1, 0.01)
sensitivity = st.sidebar.slider("Sensibilidad de Voz", 0.1, 0.9, 0.3, 0.05)
smoothness = st.sidebar.slider("Suavidad", 0.1, 1.0, 0.5, 0.05)

def analyze_audio(audio_bytes):
    """Analiza el audio directamente desde bytes usando librosa"""
    try:
        # Convertir bytes a array de audio con librosa
        y, sr = librosa.load(io.BytesIO(audio_bytes), sr=16000, mono=True)
        
        # Calcular volumen
        volume = np.abs(y)
        if np.max(volume) > 0:
            volume = volume / np.max(volume)
        else:
            volume = np.zeros_like(volume)
        
        # Detectar voz
        is_speech = volume > sensitivity
        
        # Calcular puntos de zoom con suavizado
        zoom_points = []
        current_zoom = 1.0
        
        # Tamaño de ventana basado en la suavidad
        window_size = max(100, int(5000 * smoothness))
        
        for i in range(0, len(is_speech), window_size):
            window = is_speech[i:i+window_size]
            if len(window) == 0:
                continue
                
            if np.mean(window) > 0.3:  # Segmento con voz
                current_zoom = min(zoom_intensity, current_zoom + 0.02 * (1/smoothness))
            else:  # Silencio
                current_zoom = max(1.0, current_zoom - 0.02 * (1/smoothness))
                
            zoom_points.append(current_zoom)
        
        return zoom_points
        
    except Exception as e:
        st.error(f"Error en análisis de audio: {str(e)}")
        return [1.0] * 100  # Perfil de zoom plano como respaldo

def process_video(video_path, output_path, zoom_profile):
    """Procesa el video con el perfil de zoom"""
    try:
        # Cargar video
        clip = VideoFileClip(video_path)
        
        # Calcular frames por segundo del perfil de zoom
        zoom_fps = len(zoom_profile) / clip.duration
        
        # Función para aplicar zoom
        def make_frame(get_frame, t):
            try:
                # Obtener nivel de zoom para este tiempo
                idx = min(int(t * zoom_fps), len(zoom_profile)-1)
                zoom_level = zoom_profile[idx]
                
                # Aplicar zoom
                frame = get_frame(t)
                return frame * zoom_level
            except:
                return get_frame(t)  # Respaldar al frame original
            
        # Aplicar efecto
        zoom_clip = clip.fl(lambda gf, t: make_frame(gf, t), apply_to=['video'])
        
        # Escribir video de salida
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
        return True
        
    except Exception as e:
        st.error(f"Error en procesamiento de video: {str(e)}")
        return False

def extract_audio_from_video(video_bytes):
    """Extrae audio directamente desde los bytes del video usando Pydub"""
    try:
        # Crear archivo temporal en memoria
        video_file = io.BytesIO(video_bytes)
        video_file.name = "temp_video.mp4"
        
        # Cargar video con Pydub
        audio = AudioSegment.from_file(video_file, format="mp4")
        
        # Convertir a mono y 16kHz
        audio = audio.set_channels(1).set_frame_rate(16000)
        
        # Exportar a bytes
        audio_bytes = io.BytesIO()
        audio.export(audio_bytes, format="wav")
        
        return audio_bytes.getvalue()
        
    except Exception as e:
        st.error(f"Error extrayendo audio: {str(e)}")
        return None

if uploaded_file is not None:
    # Mostrar video subido
    st.video(uploaded_file)
    
    if st.button("✨ Aplicar Zoom Automático", type="primary", use_container_width=True):
        start_time = time.time()
        
        with st.spinner('Procesando tu video... Esto puede tardar varios minutos'):
            # Leer el contenido del archivo subido
            video_bytes = uploaded_file.getvalue()
            
            # Paso 1: Extraer audio directamente desde bytes
            audio_bytes = extract_audio_from_video(video_bytes)
            
            if audio_bytes is None:
                st.error("Error al extraer audio del video")
                st.stop()
            
            # Paso 2: Analizar audio
            zoom_profile = analyze_audio(audio_bytes)
            
            # Crear archivo temporal para video
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp_video:
                tmp_video.write(video_bytes)
                input_path = tmp_video.name
            
            # Paso 3: Procesar video
            output_path = "procesado_" + uploaded_file.name
            success = process_video(input_path, output_path, zoom_profile)
            
            if success:
                processing_time = time.time() - start_time
                st.success(f"✅ ¡Video procesado con éxito en {processing_time:.1f} segundos!")
                
                # Mostrar video resultante
                st.video(output_path)
                
                # Botón de descarga
                with open(output_path, "rb") as f:
                    st.download_button(
                        "⬇️ Descargar Video Procesado",
                        f,
                        file_name=output_path,
                        mime="video/mp4"
                    )
            else:
                st.error("Error procesando el video. Intenta con otro archivo.")
            
            # Limpiar archivos temporales
            os.unlink(input_path)
            if os.path.exists(output_path):
                os.unlink(output_path)

# Pie de página
st.markdown("---")
st.caption("AutoZoom Pro v7.0 | Herramienta para creadores de contenido")
st.caption("© 2024 - Zoom automático basado en análisis de voz")
