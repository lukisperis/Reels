"""Fábrica de vídeos verticales: guion JSON -> voz + imágenes + montaje -> MP4 listo para subir."""
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
CACHE = RAIZ / ".cache"
VOCES_DIR = RAIZ / ".voces"
SR = 44100          # frecuencia de audio de la mezcla final
W, H, FPS = 1080, 1920, 30
