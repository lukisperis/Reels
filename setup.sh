#!/usr/bin/env bash
# Instala dependencias y descarga las voces (una sola vez por máquina).
set -euo pipefail
cd "$(dirname "$0")"
pip install -q -r requirements.txt
mkdir -p .voces
for v in es_ES-davefx-medium es_ES-sharvard-medium es_ES-carlfm-x_low; do
  if [ ! -f ".voces/$v.onnx" ]; then
    curl -sSL -o "/tmp/$v.tar.bz2" "https://github.com/k2-fsa/sherpa-onnx/releases/download/tts-models/vits-piper-$v.tar.bz2"
    tar xjf "/tmp/$v.tar.bz2" -C /tmp
    cp "/tmp/vits-piper-$v/$v.onnx" .voces/
    cp "/tmp/vits-piper-$v/"*.json ".voces/$v.onnx.json"
  fi
done
command -v ffmpeg >/dev/null || (apt-get update -qq && apt-get install -y -qq ffmpeg)
echo "Listo."
