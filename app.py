import streamlit as st
import numpy as np
import tempfile
import os
import librosa
import soundfile as sf
from moviepy.editor import VideoFileClip
import warnings
import io
import time
import imageio
from scipy.io import wavfile
import cv2

# Configuración de página
st.set_page_config(
    page_title="🎬 AutoZoom Pro",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Ocultar warnings
warnings.filterwarnings("ignore")

# Interfaz de usuario
st.title("🎬 AutoZoom Pro - Editor Inteligente")
st.subheader("Zoom automático profesional basado en tu voz")

with st.expander("⚙️ Configuración avanzada", expanded=True):
    col1, col2, col3 = st.columns(3)
    with col1:
        zoom_intensity = st.slider("Intensidad de Zoom", 1.0, 1.5, 1.1, 0.01)
    with col2:
        sensitivity = st.slider("Sensibilidad de Voz", 0.1, 0.9, 0.3, 0.05)
    with col3:
        smoothness = st.slider("Suavidad", 0.1, 1.0, 0.5, 0.05)

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
        rms = librosa.feature.rms(y=y)
        volume = (rms - np.min(rms)) / (np.max(rms) - np.min(rms) + 1e-10)
        volume = volume.flatten()
        
        # Detección de voz adaptativa
        is_speech = volume > sensitivity
        
        # Suavizado inteligente
        zoom_profile = []
        current_zoom = 1.0
        transition_speed = 0.05 * (1/smoothness)
        
        for speech in is_speech:
            target_zoom = zoom_intensity if speech else 1.0
            current_zoom += (target_zoom - current_zoom) * transition_speed
            zoom_profile.append(current_zoom)
        
        return zoom_profile
        
    except Exception as e:
        st.error(f"Error en análisis de audio: {str(e)}")
        return np.ones(100)  # Perfil plano como respaldo

def extract_audio(video_bytes):
    """Extrae audio usando moviepy (sin dependencias externas)"""
    try:
        # Guardar video temporalmente
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp_video:
            tmp_video.write(video_bytes)
            video_path = tmp_video.name
        
        # Extraer audio con moviepy
        video_clip = VideoFileClip(video_path)
        audio_clip = video_clip.audio
        
        # Guardar audio temporalmente
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_audio:
            audio_path = tmp_audio.name
            audio_clip.write_audiofile(audio_path, fps=16000)
        
        # Leer audio como bytes
        with open(audio_path, "rb") as f:
            audio_bytes = f.read()
        
        # Limpiar
        video_clip.close()
        os.unlink(video_path)
        os.unlink(audio_path)
        
        return audio_bytes
        
    except Exception as e:
        st.error(f"Error extrayendo audio: {str(e)}")
        return None

def enhance_video(input_path, output_path, zoom_profile):
    """Procesa el video con calidad mejorada"""
    try:
        # Cargar video con imageio
        reader = imageio.get_reader(input_path)
        fps = reader.get_meta_data()['fps']
        frame_count = 0
        
        # Configurar writer para máxima calidad
        writer = imageio.get_writer(
            output_path,
            fps=fps,
            quality=10,
            codec='libx264',
            pixelformat='yuv420p'
        )
        
        # Calcular fps del perfil de zoom
        zoom_fps = len(zoom_profile) / reader.count_frames()
        
        for frame in reader:
            # Aplicar zoom
            zoom_level = zoom_profile[min(int(frame_count * zoom_fps), len(zoom_profile)-1)]
            
            # Mejorar contraste (opcional)
            frame = cv2.normalize(frame, None, 0, 255, cv2.NORM_MINMAX)
            
            # Aplicar transformación de zoom
            if zoom_level != 1.0:
                h, w = frame.shape[:2]
                new_h, new_w = int(h/zoom_level), int(w/zoom_level)
                start_h, start_w = (h - new_h) // 2, (w - new_w) // 2
                cropped = frame[start_h:start_h+new_h, start_w:start_w+new_w]
                frame = cv2.resize(cropped, (w, h), interpolation=cv2.INTER_LANCZOS4)
            
            writer.append_data(frame)
            frame_count += 1
            
        writer.close()
        reader.close()
        return True
        
    except Exception as e:
        st.error(f"Error procesando video: {str(e)}")
        return False

if uploaded_file is not None:
    st.video(uploaded_file)
    
    if st.button("✨ Procesar Video", type="primary", use_container_width=True):
        start_time = time.time()
        
        with st.spinner('Procesando... Esto puede tardar varios minutos'):
            # Paso 1: Extraer audio
            video_bytes = uploaded_file.getvalue()
            audio_bytes = extract_audio(video_bytes)
            
            if audio_bytes is None:
                st.error("No se pudo extraer audio del video")
                st.stop()
            
            # Paso 2: Analizar audio
            zoom_profile = analyze_audio(audio_bytes)
            
            # Paso 3: Procesar video
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp_in:
                tmp_in.write(video_bytes)
                input_path = tmp_in.name
            
            output_path = f"enhanced_{uploaded_file.name}"
            
            if enhance_video(input_path, output_path, zoom_profile):
                processing_time = time.time() - start_time
                
                # Mostrar resultados
                st.success(f"✅ Procesado en {processing_time:.1f} segundos")
                st.video(output_path)
                
                # Botón de descarga
                with open(output_path, "rb") as f:
                    st.download_button(
                        "⬇️ Descargar Video Mejorado",
                        f,
                        file_name=output_path,
                        mime="video/mp4"
                    )
            
            # Limpieza
            os.unlink(input_path)
            if os.path.exists(output_path):
                os.unlink(output_path)

# Pie de página
st.markdown("---")
st.caption("AutoZoom Pro v9.0 | Calidad profesional sin dependencias problemáticas")
