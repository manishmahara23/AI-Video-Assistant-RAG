import os
import tempfile

import streamlit as st
import yt_dlp
from pydub import AudioSegment

DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)


def _create_cookie_file():
    """
    Create a temporary cookies.txt from Streamlit Secrets.
    Returns path if available, else None.
    """
    try:
        cookies = st.secrets["YOUTUBE_COOKIES"]

        temp = tempfile.NamedTemporaryFile(
            delete=False,suffix=".txt",mode="w",encoding="utf-8",
        )

        temp.write(cookies)
        temp.close()

        return temp.name

    except Exception:
        return None


def download_youtube_audio(url: str) -> str:
    output_path = os.path.join(DOWNLOAD_DIR, "%(title)s.%(ext)s")

    cookie_file = _create_cookie_file()

    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": output_path,
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "ignoreerrors": False,

        "retries": 10,
        "fragment_retries": 10,
        "extractor_retries": 10,

        "geo_bypass": True,
        "geo_bypass_country": "IN",

        "source_address": "0.0.0.0",

        "http_headers": {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/138.0.0.0 Safari/537.36"
            )
        },

        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "wav",
                "preferredquality": "192",
            }
        ],
    }

    if cookie_file:
        ydl_opts["cookiefile"] = cookie_file

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            downloaded_file = ydl.prepare_filename(info)

    finally:
        if cookie_file and os.path.exists(cookie_file):
            os.remove(cookie_file)

    wav_file = os.path.splitext(downloaded_file)[0] + ".wav"

    return wav_file


def convert_to_wav(input_path: str) -> str:
    output_path = os.path.splitext(input_path)[0] + "_converted.wav"

    audio = AudioSegment.from_file(input_path)
    audio = audio.set_channels(1).set_frame_rate(16000)

    audio.export(output_path, format="wav")

    return output_path


def chunk_audio(wav_path: str, chunk_minutes: int = 10) -> list:
    audio = AudioSegment.from_wav(wav_path)

    chunk_ms = chunk_minutes * 60 * 1000

    chunks = []

    for i, start in enumerate(range(0, len(audio), chunk_ms)):
        chunk = audio[start:start + chunk_ms]

        chunk_path = f"{wav_path}_chunk_{i}.wav"

        chunk.export(chunk_path, format="wav")

        chunks.append(chunk_path)

    return chunks


def process_input(source: str) -> list:
    if source.startswith(("http://", "https://")):
        print("Detected YouTube URL. Downloading audio...")
        wav_path = download_youtube_audio(source)
    else:
        print("Detected local file. Converting to WAV...")
        wav_path = convert_to_wav(source)

    print("Chunking audio...")

    chunks = chunk_audio(wav_path)

    print(f"Audio ready — {len(chunks)} chunk(s) created.")

    return chunks