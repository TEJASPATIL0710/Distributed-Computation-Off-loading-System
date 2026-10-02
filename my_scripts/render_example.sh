ffmpeg -f lavfi -i testsrc=duration=3:size=320x240:rate=15 -c:v libx264 -y /task/output.mp4 2>&1 | tail -n 5
ffprobe -v error -show_entries format=duration,size -of default=noprint_wrappers=1 /task/output.mp4
echo "Render complete"
