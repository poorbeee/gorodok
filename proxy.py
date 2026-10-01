import os
import time
import uuid
import asyncio
import edge_tts
import requests
import urllib3
from flask import Flask, request, Response, send_from_directory

urllib3.disable_warnings()

app = Flask(__name__, static_folder='.', static_url_path='')

# --- CORS ---
@app.after_request
def add_cors(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    return response

# --- GigaChat ---
_key_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'key.txt')
if os.path.exists(_key_file):
    with open(_key_file, 'r', encoding='utf-8') as f:
        GIGACHAT_KEY = f.read().strip()
else:
    GIGACHAT_KEY = os.environ.get('GIGACHAT_KEY', '').strip()

AUTH_URL = 'https://ngw.devices.sberbank.ru:9443/api/v2/oauth'
GIGACHAT_URL = 'https://gigachat.devices.sberbank.ru/api/v1/chat/completions'
_token = {'value': None, 'expires': 0}


def get_token():
    if _token['value'] and time.time() < _token['expires'] - 60:
        return _token['value']
    resp = requests.post(AUTH_URL, headers={
        'Authorization': f'Basic {GIGACHAT_KEY}',
        'RqUID': str(uuid.uuid4()),
        'Content-Type': 'application/x-www-form-urlencoded',
    }, data={'scope': 'GIGACHAT_API_PERS'}, verify=False, timeout=20)
    if resp.status_code != 200:
        raise RuntimeError(f'GigaChat OAuth {resp.status_code}: {resp.text[:300]}')
    data = resp.json()
    _token['value'] = data['access_token']
    _token['expires'] = data['expires_at'] / 1000
    return _token['value']


@app.route('/')
def index():
    return send_from_directory('.', 'index.html')


@app.route('/api/health')
def health():
    return {'status': 'ok', 'has_key': bool(GIGACHAT_KEY)}


@app.route('/api/chat', methods=['POST', 'OPTIONS'])
def chat():
    if request.method == 'OPTIONS':
        return Response('', status=204)

    if not GIGACHAT_KEY:
        return Response('GIGACHAT_KEY пустой', status=500)
    try:
        token = get_token()
    except Exception as e:
        return Response(f'Ошибка токена: {e}', status=500)

    body = request.get_json()
    upstream = requests.post(GIGACHAT_URL, headers={
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json',
        'Accept': 'text/event-stream',
    }, json=body, stream=True, verify=False, timeout=90)

    def generate():
        for chunk in upstream.iter_content(chunk_size=None):
            if chunk:
                yield chunk
    return Response(generate(), content_type='text/event-stream')


@app.route('/api/speech', methods=['POST', 'OPTIONS'])
def speech():
    if request.method == 'OPTIONS':
        return Response('', status=204)

    data = request.get_json()
    text = data.get('text', '').strip()
    voice = data.get('voice', 'ru-RU-DmitryNeural')
    if not text:
        return Response('Пустой текст', status=400)
    if len(text) > 5000:
        text = text[:5000]

    print(f"[TTS] Синтез {len(text)} символов, голос: {voice}")

    try:
        async def generate_audio():
            communicate = edge_tts.Communicate(text, voice)
            audio_data = b''
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    audio_data += chunk["data"]
            return audio_data

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        audio_bytes = loop.run_until_complete(generate_audio())
        loop.close()

        print(f"[TTS] OK, {len(audio_bytes)} байт")
        return Response(audio_bytes, content_type='audio/mpeg')
    except Exception as e:
        print(f"[TTS] Ошибка: {e}")
        return Response(f'Ошибка синтеза: {e}', status=500)


if __name__ == '__main__':
    if not GIGACHAT_KEY:
        print('Нет GigaChat ключа. Создай key.txt.')
        exit(1)
    port = int(os.environ.get('PORT', 8080))
    print(f'Сервер: http://0.0.0.0:{port}')
    print(f'GigaChat ключ: {len(GIGACHAT_KEY)} символов')
    app.run(host='0.0.0.0', port=port, threaded=True)