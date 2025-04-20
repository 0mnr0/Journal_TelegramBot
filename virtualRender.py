from playwright.sync_api import sync_playwright
import subprocess
import os

# Пути
HTML_DIR = os.path.abspath("RenderMaterial")
LOCAL_HTML_PATH = os.path.join(HTML_DIR, "renderPage.html")
VIDEO_NAME = "RDR2.mp4"
VIDEO_PATH = os.path.join(HTML_DIR, VIDEO_NAME)
OUTPUT_DIR = os.path.abspath("videos")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Проверка файлов
if not os.path.exists(VIDEO_PATH):
    raise FileNotFoundError(f"Видео не найдено: {VIDEO_PATH}")
if not os.path.exists(LOCAL_HTML_PATH):
    raise FileNotFoundError(f"HTML не найден: {LOCAL_HTML_PATH}")

FILE_URL = f"file://{LOCAL_HTML_PATH}"

with sync_playwright() as p:
    browser = p.chromium.launch(
        headless=True,
        args=["--allow-file-access-from-files", "--disable-web-security"]
    )
    context = browser.new_context(
        viewport={"width": 1280, "height": 720},
        record_video_dir=OUTPUT_DIR
    )
    page = context.new_page()
    page.goto(FILE_URL)

    # Обновляем src видео
    video_element = page.wait_for_selector("video")
    page.evaluate(
        """(videoPath) => {
            const video = document.querySelector('video');
            video.src = 'file://' + videoPath;
            video.load();
        }""",
        VIDEO_PATH
    )

    # Запуск воспроизведения
    video_element.click()

    # Ожидание загрузки видео
    page.wait_for_function(
        """() => {
            const video = document.querySelector('video');
            return video.readyState === 4 && !isNaN(video.duration);
        }""",
        timeout=10000
    )

    # Ждем 10 секунд записи
    page.wait_for_timeout(10000)

    # Закрываем
    context.close()

# Конвертируем в MP4
video_path = page.video.path()
output_path = os.path.join(OUTPUT_DIR, "output.mp4")

subprocess.run([
    "ffmpeg",
    "-i", video_path,
    "-c:v", "libx264",
    "-crf", "20",
    "-preset", "fast",
    "-c:a", "aac",
    output_path
], check=True)

# Удаляем исходник
os.remove(video_path)