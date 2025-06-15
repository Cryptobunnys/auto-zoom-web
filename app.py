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
        audio = audio.set_channels(1).set_frame_rate(16000)
        
        # Exportar a bytes
        audio_bytes = io.BytesIO()
        audio.export(audio_bytes, format="wav")
        
        return audio_bytes.getvalue()
        
    except Exception as e:
        st.error(f"Error extrayendo audio: {str(e)}")
        return None

def process_video(input_path, output_path, zoom_profile):
    """Procesa el video con el perfil de zoom"""
    try:
        # Cargar video con OpenCV
        cap = cv2.VideoCapture(input_path)
        fps = cap.get(cv2.CAP_PROP_FPS)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        # Configurar writer
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
        
        frame_count = 0
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        progress_bar = st.progress(0)
        
        # Calcular fps del perfil de zoom
        zoom_fps = len(zoom_profile) / (total_frames / fps)
        
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
            
            # Obtener nivel de zoom
            zoom_level = zoom_profile[min(int(frame_count * zoom_fps), len(zoom_profile)-1)]
            
            # Aplicar zoom
            if zoom_level > 1.0:
                h, w = frame.shape[:2]
                new_h, new_w = int(h/zoom_level), int(w/zoom_level)
                start_h, start_w = (h - new_h) // 2, (w - new_w) // 2
                frame = frame[start_h:start_h+new_h, start_w:start_w+new_w]
                frame = cv2.resize(frame, (w, h), interpolation=cv2.INTER_LANCZOS4)
            
            # Escribir frame
            out.write(frame)
            frame_count += 1
            
            # Actualizar progreso
            if frame_count % 10 == 0:
                progress_bar.progress(frame_count / total_frames)
        
        # Liberar recursos
        cap.release()
        out.release()
        cv2.destroyAllWindows()
        progress_bar.empty()
        return True
        
    except Exception as e:
        st.error(f"Error procesando video: {str(e)}")
        return False

if uploaded_file is not None:
    st.video(uploaded_file)
    
    if st.button("✨ Procesar Video", type="primary", use_container_width=True):
        start_time = time.time()
        
        with st.spinner('Procesando... Esto puede tardar varios minutos'):
            # Leer el contenido del archivo subido
            video_bytes = uploaded_file.getvalue()
            
            # Paso 1: Extraer audio
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
            
            try:
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
            
            finally:
                # Limpiar archivos temporales
                os.unlink(input_path)
                if os.path.exists(output_path):
                    os.unlink(output_path)

# Pie de página
st.markdown("---")
st.caption("AutoZoom Pro v11.0 | Solución robusta y confiable")
