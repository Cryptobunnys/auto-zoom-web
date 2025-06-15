import streamlit as st
import numpy as np
import tempfile
import os
import librosa
import time
import io
from PIL import Image
from moviepy.editor import VideoFileClip, ImageSequenceClip
import warnings

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
st.title("🎬 AutoZoom Pro - Solución Definitiva")
st.subheader("Zoom automático profesional sin dependencias problemáticas")

# Parámetros ajustables
zoom_intensity = st.sidebar.slider("Intensidad de Zoom", 1.0, 1.5, 1.1, 0.01)
sensitivity = st.sidebar.slider("Sensibilidad de Voz", 0.1, 0.9, 0.3, 0.05)
smoothness = st.sidebar.slider("Suavidad", 0.1, 1.0, 0.5, 0.05)

# Subida de archivos
uploaded_file = st.file_uploader(
    "Sube tu video (MP4)",
    type=["mp4"],
    accept_multiple_files=False
)

def analyze_audio(audio_bytes):
    """Analiza el audio usando librosa"""
    try:
        # Cargar audio directamente desde bytes
        y, sr = librosa.load(io.BytesIO(audio_bytes), sr=16000, mono=True)
        
        # Calcular volumen
        volume = np.abs(y)
        if np.max(volume) > 0:
            volume = volume / np.max(volume)
        
        # Detectar voz
        is_speech = volume > sensitivity
        
        # Calcular puntos de zoom con suavizado
        zoom_profile = []
        current_zoom = 1.0
        window_size = max(100, int(5000 * smoothness))
        
        for i in range(0, len(is_speech), window_size):
            window = is_speech[i:i+window_size]
            if len(window) == 0:
                continue
                
            if np.mean(window) > 0.3:  # Segmento con voz
                target_zoom = zoom_intensity
            else:  # Silencio
                target_zoom = 1.0
                
            # Transición suave
            current_zoom += (target_zoom - current_zoom) * 0.1
            zoom_profile.append(current_zoom)
        
        return zoom_profile
        
    except Exception as e:
        st.error(f"Error en análisis de audio: {str(e)}")
        return [1.0] * 100  # Perfil plano como respaldo

def extract_audio(video_bytes):
    """Extrae audio usando moviepy"""
    try:
        # Guardar video temporalmente
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp_video:
            tmp_video.write(video_bytes)
            video_path = tmp_video.name
        
        # Extraer audio con moviepy
        video_clip = VideoFileClip(video_path)
        audio_bytes = io.BytesIO()
        video_clip.audio.write_audiofile(audio_bytes, codec='pcm_s16le', fps=16000, verbose=False)
        
        # Limpiar
        video_clip.close()
        os.unlink(video_path)
        
        return audio_bytes.getvalue()
        
    except Exception as e:
        st.error(f"Error extrayendo audio: {str(e)}")
        return None

def process_video(video_bytes, zoom_profile):
    """Procesa el video con calidad mejorada usando PIL y moviepy"""
    try:
        # Guardar video temporalmente
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp_video:
            tmp_video.write(video_bytes)
            input_path = tmp_video.name
        
        # Cargar video con moviepy
        video_clip = VideoFileClip(input_path)
        fps = video_clip.fps
        total_frames = int(video_clip.duration * fps)
        
        # Calcular fps del perfil de zoom
        zoom_fps = len(zoom_profile) / video_clip.duration
        
        # Procesar frames
        processed_frames = []
        progress_bar = st.progress(0)
        
        for i, frame in enumerate(video_clip.iter_frames()):
            # Obtener nivel de zoom
            zoom_level = zoom_profile[min(int(i / fps * zoom_fps), len(zoom_profile)-1)]
            
            # Convertir a imagen PIL
            img = Image.fromarray(frame)
            
            # Aplicar zoom
            if zoom_level > 1.0:
                width, height = img.size
                new_width, new_height = int(width / zoom_level), int(height / zoom_level)
                left = (width - new_width) // 2
                top = (height - new_height) // 2
                img = img.crop((left, top, left + new_width, top + new_height))
                img = img.resize((width, height), Image.LANCZOS)
            
            # Convertir de nuevo a array
            processed_frames.append(np.array(img))
            
            # Actualizar progreso
            if i % 10 == 0:
                progress_bar.progress(i / total_frames)
        
        # Crear nuevo clip
        processed_clip = ImageSequenceClip(processed_frames, fps=fps)
        
        # Exportar
        output_path = f"procesado_{uploaded_file.name}"
        processed_clip.write_videofile(
            output_path,
            codec='libx264',
            audio_codec='aac',
            fps=fps,
            preset='fast',
            threads=4
        )
        
        # Limpiar
        video_clip.close()
        processed_clip.close()
        os.unlink(input_path)
        progress_bar.empty()
        
        return output_path
        
    except Exception as e:
        st.error(f"Error procesando video: {str(e)}")
        return None

if uploaded_file is not None:
    st.video(uploaded_file)
    
    if st.button("✨ Procesar Video", type="primary", use_container_width=True):
        start_time = time.time()
        
        with st.spinner('Procesando... Esto puede tardar varios minutos'):
            # Leer el contenido del archivo
            video_bytes = uploaded_file.getvalue()
            
            # Paso 1: Extraer audio
            audio_bytes = extract_audio(video_bytes)
            
            if audio_bytes is None:
                st.error("No se pudo extraer audio del video")
                st.stop()
            
            # Paso 2: Analizar audio
            zoom_profile = analyze_audio(audio_bytes)
            
            # Paso 3: Procesar video
            output_path = process_video(video_bytes, zoom_profile)
            
            if output_path:
                processing_time = time.time() - start_time
                
                # Mostrar resultados
                st.success(f"✅ Procesado en {processing_time:.1f} segundos")
                st.video(output_path)
                
                # Botón de descarga
                with open(output_path, "rb") as f:
                    st.download_button(
                        "⬇️ Descargar Video Procesado",
                        f,
                        file_name=output_path,
                        mime="video/mp4"
                    )
                
                # Limpiar
                os.unlink(output_path)

# Pie de página
st.markdown("---")
st.caption("AutoZoom Pro vFinal | Solución estable y confiable")
