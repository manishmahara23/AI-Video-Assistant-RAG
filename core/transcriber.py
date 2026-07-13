import whisper
import os
import time
import requests
from pydub import AudioSegment
from concurrent.futures import ThreadPoolExecutor, as_completed

# Sarvam's sync STT-translate API rejects audio longer than 30s.
# We slice each chunk into 25s pieces (with a 5s safety margin) before sending.
SARVAM_PIECE_SECONDS = 20


WHISPER_MODEL = os.getenv("WHISPER_MODEL", "small")


def _get_secret(key: str, default=None):
    """Read a config value from .env / OS env first, then fall back to
    Streamlit Cloud's st.secrets (which does NOT populate os.environ)."""
    val = os.getenv(key)
    if val:
        return val
    try:
        import streamlit as st
        if key in st.secrets:
            return st.secrets[key]
    except Exception:
        pass
    return default


SARVAM_API_KEY = _get_secret("SARVAM_API_KEY")
SARVAM_STT_TRANSLATE_URL = "https://api.sarvam.ai/speech-to-text-translate"
SARVAM_MODEL = _get_secret("SARVAM_STT_MODEL", "saaras:v2.5")

_model = None


def load_model():

    global _model  

    if _model is None: 
        print(f"Loading Whisper model: {WHISPER_MODEL} ...")
        _model = whisper.load_model(WHISPER_MODEL) 
        print("Whisper model loaded.")
    return _model 


def transcribe_chunk_whisper(chunk_path: str) -> str:

    model = load_model()  

    result = model.transcribe(chunk_path, task="transcribe")  
    return result["text"]  


def _send_to_sarvam(piece_path: str, max_retries: int = 3) -> str:
    """Send one ≤30s WAV file to Sarvam and return the English transcript.
    Retries on timeout/connection errors since Sarvam can be slow under load."""
    headers = {"api-subscription-key": SARVAM_API_KEY or _get_secret("SARVAM_API_KEY")}

    last_err = None
    for attempt in range(1, max_retries + 1):
        try:
            with open(piece_path, "rb") as f:
                files = {"file": (os.path.basename(piece_path), f, "audio/wav")}
                data = {"model": SARVAM_MODEL, "with_diarization": "false"}
                response = requests.post(
                    SARVAM_STT_TRANSLATE_URL,
                    headers=headers,
                    files=files,
                    data=data,
                    timeout=180,
                )

            if not response.ok:
                print(f"\n Sarvam returned {response.status_code}")
                print(f"Response body: {response.text}\n")
                response.raise_for_status()

            return response.json().get("transcript", "")

        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
            last_err = e
            print(f"Sarvam timeout/connection error (attempt {attempt}/{max_retries}): {e}")
            if attempt < max_retries:
                time.sleep(3 * attempt)  # backoff: 3s, 6s, 9s
                continue
            raise RuntimeError(
                f"Sarvam API timed out after {max_retries} attempts. "
                f"The service may be slow/down right now — try again in a bit "
                f"or switch language to 'english' (uses local Whisper instead)."
            ) from last_err


def transcribe_chunk_sarvam(chunk_path: str, max_workers: int = 5) -> str:
    """
    Sarvam sync API only accepts <=30s audio. We split this chunk into
    pieces and send them CONCURRENTLY (instead of one-by-one) to cut
    total wait time drastically, then reassemble in original order.
    """
    api_key = SARVAM_API_KEY or _get_secret("SARVAM_API_KEY")
    if not api_key:
        raise RuntimeError("SARVAM_API_KEY is not set in .env or Streamlit secrets")

    audio = AudioSegment.from_wav(chunk_path)
    piece_ms = SARVAM_PIECE_SECONDS * 1000

    # 1. Export all pieces to disk first
    piece_paths = []
    for i, start in enumerate(range(0, len(audio), piece_ms)):
        piece = audio[start: start + piece_ms]
        piece_path = f"{chunk_path}_sv_{i}.wav"
        piece.export(piece_path, format="wav")
        piece_paths.append(piece_path)

    total_pieces = len(piece_paths)
    results = [None] * total_pieces

    # 2. Send them concurrently, but keep track of index for correct order
    try:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_idx = {
                executor.submit(_send_to_sarvam, p): idx
                for idx, p in enumerate(piece_paths)
            }
            done_count = 0
            for future in as_completed(future_to_idx):
                idx = future_to_idx[future]
                results[idx] = future.result()
                done_count += 1
                print(f"  → Sarvam piece {done_count}/{total_pieces} done")
    finally:
        for p in piece_paths:
            if os.path.exists(p):
                os.remove(p)

    return " ".join(r or "" for r in results).strip()


def transcribe_chunk(chunk_path: str, language: str = "english") -> str:
    """
    Route one chunk to Whisper or Sarvam depending on language choice.
    - english  → Whisper (local model)
    - hinglish → Sarvam (translates to English while transcribing)
    """
    if language.lower() == "hinglish":
        return transcribe_chunk_sarvam(chunk_path)
    return transcribe_chunk_whisper(chunk_path)


def transcribe_all(chunks: list, language: str = "english") -> str:

    full_transcript = "" 

    engine = "Sarvam AI" if language.lower() == "hinglish" else "Whisper"
    print(f"Using {engine} for transcription.")

    for i, chunk in enumerate(chunks):  

        print(f"Transcribing chunk {i + 1}/{len(chunks)}...")

        text = transcribe_chunk(chunk, language=language)  

        full_transcript += text + " "  

    print("Transcription complete.")

    return full_transcript.strip()