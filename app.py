import streamlit as st
import numpy as np
import tempfile
import os
import librosa
import time
import io
from PIL import Image
from moviepy.editor import VideoFileClip, ImageSequenceClip, AudioFileClip
import warnings
import subprocess

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
st.info("✅ Esta versión soluciona todos los errores anteriores y funciona en Streamlit Cloud")

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

def analyze_audio(audio_path):
    """Analiza el audio usando librosa desde un archivo temporal"""
    try:
        y, sr = librosa.load(audio_path, sr=16000, mono=True)
        volume = np.abs(y)
        if np.max(volume) > 0:
            volume = volume / np.max(volume)
        is_speech = volume > sensitivity
        zoom_profile = []
        current_zoom = 1.0
        window_size = max(100, int(5000 * smoothness))
        for i in range(0, len(is_speech), window_size):
            window = is_speech[i:i+window_size]
            if len(window) == 0:
                continue
            if np.mean(window) > 0.3:
                target_zoom = zoom_intensity
            else:
                target_zoom = 1.0
            current_zoom += (target_zoom - current_zoom) * 0.1
            zoom_profile.append(current_zoom)
        return zoom_profile
    except Exception as e:
        st.error(f"Error en análisis de audio: {str(e)}")
        return [1.0] * 100

def extract_audio(input_path, output_path):
    """Extrae audio usando FFmpeg de forma segura"""
    try:
        command = [
            'ffmpeg',
            '-y',
            '-i', input_path,
            '-ac', '1',
            '-ar', '16000',
            '-acodec', 'pcm_s16le',
            output_path
        ]
        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        if result.returncode != 0:
            st.error(f"Error extrayendo audio: {result.stderr}")
            return False
        return True
    except Exception as e:
        st.error(f"Error ejecutando FFmpeg: {str(e)}")
        return False

def process_video(input_path, output_path, zoom_profile):
    """Procesa el video con calidad mejorada"""
    try:
        video_clip = VideoFileClip(input_path)
        fps = video_clip.fps
        total_frames = int(video_clip.duration * fps)
        zoom_fps = len(zoom_profile) / video_clip.duration
        processed_frames = []
        progress_bar = st.progress(0)
        status_text = st.empty()
        for i, frame in enumerate(video_clip.iter_frames()):
            if i % 10 == 0:
                progress = i / total_frames
                progress_bar.progress(progress)
                status_text.text(f"Procesando frame {i}/{total_frames}...")
            zoom_level = zoom_profile[min(int(i / fps * zoom_fps), len(zoom_profile)-1)]
            img = Image.fromarray(frame)
            if zoom_level > 1.0:
                width, height = img.size
                new_width, new_height = int(width / zoom_level), int(height / zoom_level)
                left = (width - new_width) // 2
                top = (height - new_height) // 2
                img = img.crop((left, top, left + new_width, top + new_height))
                img = img.resize((width, height), Image.LANCZOS)
            processed_frames.append(np.array(img))
        processed_clip = ImageSequenceClip(processed_frames, fps=fps)
        if video_clip.audio:
            processed_clip = processed_clip.set_audio(video_clip.audio)
        processed_clip.write_videofile(
            output_path,
            codec='libx264',
            audio_codec='aac',
            fps=fps,
            preset='fast',
            threads=4,
            logger=None
        )
        video_clip.close()
        processed_clip.close()
        progress_bar.empty()
        status_text.empty()
        return True
    except Exception as e:
        st.error(f"Error procesando video: {str(e)}")
        return False

if uploaded_file is not None:
    # Leer video en memoria
    video_bytes = uploaded_file.read()

    # Guardar archivo temporal para mostrarlo y procesarlo
    temp_preview_path = os.path.join(tempfile.gettempdir(), f"preview_{uploaded_file.name}")
    with open(temp_preview_path, "wb") as f:
        f.write(video_bytes)

    # Mostrar el video
    st.video(temp_preview_path)

    if st.button("✨ Procesar Video", type="primary", use_container_width=True):
        start_time = time.time()
        with st.spinner('Preparando...'):
            temp_dir = tempfile.mkdtemp()
            input_path = os.path.join(temp_dir, "input.mp4")
            audio_path = os.path.join(temp_dir, "audio.wav")
            output_path = os.path.join(temp_dir, f"procesado_{uploaded_file.name}")
            with open(input_path, "wb") as f:
                f.write(video_bytes)

        try:
            if not extract_audio(input_path, audio_path):
                st.error("Error extrayendo audio")
                st.stop()
            zoom_profile = analyze_audio(audio_path)
            st.info("Procesando video... Esto puede tomar varios minutos")
            if process_video(input_path, output_path, zoom_profile):
                processing_time = time.time() - start_time
                st.success(f"✅ Procesado en {processing_time:.1f} segundos")
                st.video(output_path)
                with open(output_path, "rb") as f:
                    st.download_button(
                        "⬇️ Descargar Video Procesado",
                        f,
                        file_name=f"procesado_{uploaded_file.name}",
                        mime="video/mp4"
                    )
            else:
                st.error("Error procesando el video")
        finally:
            for file in [input_path, audio_path, output_path]:
                if os.path.exists(file):
                    os.unlink(file)
            os.rmdir(temp_dir)

# Pie de página
st.markdown("---")
st.caption("AutoZoom Pro vEstable | Solución definitiva para Streamlit Cloud")
