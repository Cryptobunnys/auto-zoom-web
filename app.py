import streamlit as st
import numpy as np
import subprocess
import tempfile
import os
import librosa
import soundfile as sf
from moviepy.editor import VideoFileClip
import warnings
import base64
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

# Solución definitiva para FFmpeg
def install_ffmpeg():
    """Instala FFmpeg en el entorno de Streamlit Cloud"""
    try:
        st.info("📥 Instalando FFmpeg... Esto puede tomar 1 minuto")
        start_time = time.time()
        
        # Instalar FFmpeg usando apt-get
        result = subprocess.run(
            ['apt-get', 'update'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        result = subprocess.run(
            ['apt-get', '-y', 'install', 'ffmpeg'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Verificar instalación
        result = subprocess.run(
            ['ffmpeg', '-version'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        if "ffmpeg version" in result.stdout:
            st.success(f"✅ FFmpeg instalado correctamente en {time.time()-start_time:.1f} segundos")
            return True
        else:
            st.error(f"❌ Error instalando FFmpeg: {result.stderr}")
            return False
            
    except Exception as e:
        st.error(f"❌ Error crítico: {str(e)}")
        return False

# Verificar e instalar FFmpeg si es necesario
if not os.path.exists('/usr/bin/ffmpeg'):
    if install_ffmpeg():
        st.experimental_rerun()  # Reiniciar la app después de instalar
    else:
        st.error("No se pudo instalar FFmpeg. La aplicación no funcionará correctamente.")
        st.stop()

def analyze_audio(audio_path):
    """Analiza el audio usando librosa"""
    try:
        # Cargar audio con librosa
        y, sr = librosa.load(audio_path, sr=16000, mono=True)
        
        # Calcular volumen
        volume = np.abs(y)
        volume = volume / np.max(volume)
        
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

def process_video(input_path, output_path, zoom_profile):
    """Procesa el video con el perfil de zoom usando moviepy"""
    try:
        # Cargar video
        clip = VideoFileClip(input_path)
        
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

def extract_audio(input_path, output_path):
    """Extrae audio usando moviepy para evitar problemas con ffmpeg"""
    try:
        from moviepy.audio.io.AudioFileClip import AudioFileClip
        audio_clip = AudioFileClip(input_path)
        audio_clip.write_audiofile(
            output_path, 
            fps=16000, 
            ffmpeg_params=['-ac', '1']  # Mono
        )
        audio_clip.close()
        return True
    except Exception as e:
        st.error(f"Error extrayendo audio: {str(e)}")
        return False

if uploaded_file is not None:
    # Mostrar video subido
    st.video(uploaded_file)
    
    if st.button("✨ Aplicar Zoom Automático", type="primary", use_container_width=True):
        with st.spinner('Procesando tu video... Esto puede tardar varios minutos'):
            # Crear archivos temporales
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp_video:
                tmp_video.write(uploaded_file.getvalue())
                input_path = tmp_video.name
            
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_audio:
                audio_path = tmp_audio.name
            
            # Extraer audio usando moviepy
            if not extract_audio(input_path, audio_path):
                os.unlink(input_path)
                if os.path.exists(audio_path):
                    os.unlink(audio_path)
                st.stop()
            
            # Procesar
            try:
                # Analizar audio
                zoom_profile = analyze_audio(audio_path)
                
                # Procesar video
                output_path = "procesado_" + uploaded_file.name
                success = process_video(input_path, output_path, zoom_profile)
                
                if success:
                    st.success("✅ ¡Video procesado con éxito!")
                    
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
                    
            finally:
                # Limpiar archivos temporales
                os.unlink(input_path)
                os.unlink(audio_path)
                if os.path.exists(output_path):
                    os.unlink(output_path)

# Pie de página
st.markdown("---")
st.caption("AutoZoom Pro v5.0 | Herramienta para creadores de contenido")
st.caption("© 2024 - Zoom automático basado en análisis de voz")
