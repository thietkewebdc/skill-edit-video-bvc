#!/bin/bash
# Cài bộ skill vào Claude Code:  ./install.sh [--force] [tên-skill ...]
set -e
cd "$(dirname "$0")"; DEST="$HOME/.claude/skills"; FORCE=0; PICK=()
for a in "$@"; do [ "$a" = "--force" ] && FORCE=1 || PICK+=("$a"); done
[ ${#PICK[@]} -eq 0 ] && PICK=($(ls skills))
mkdir -p "$DEST"
for s in "${PICK[@]}"; do
  [ -d "skills/$s" ] || { echo "Không có skill: $s"; continue; }
  if [ -e "$DEST/$s" ] && [ $FORCE -eq 0 ]; then echo "• $s đã có (bỏ qua, thêm --force để ghi đè)"; continue; fi
  rm -rf "$DEST/$s"; cp -R "skills/$s" "$DEST/$s"; echo "✓ đã cài $s"
done
echo; echo "Kiểm tra phần mềm cần có:"
for c in ffmpeg ffprobe python3; do command -v $c >/dev/null && echo "  ✓ $c" || echo "  ✗ $c (chưa có)"; done
python3 - <<'PY'
import importlib
for m,pip in (("numpy","numpy"),("cv2","opencv-python"),("PIL","pillow"),("faster_whisper","faster-whisper")):
    try: importlib.import_module(m); print("  ✓",pip)
    except Exception: print("  ✗",pip,"→ pip install",pip)
PY
echo; echo "Xong. Mở Claude Code và gọi /edit-kieu-so-sanh-fdown, /video-auto-edit, /video-huong-dan-man-hinh-voice, /viral-reel-vn"
