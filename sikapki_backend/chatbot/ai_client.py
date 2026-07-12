from __future__ import annotations

from dataclasses import dataclass

import requests
from django.conf import settings


class AIProviderError(Exception):
    pass


@dataclass(frozen=True)
class AIConfig:
    provider: str
    model: str
    timeout_seconds: int = 120


def generate_answer(prompt: str, config: AIConfig | None = None) -> str:
    config = config or AIConfig(
        provider=settings.AI_PROVIDER,
        model=settings.AI_MODEL,
    )
    provider = config.provider.lower().strip()

    if provider == 'ollama':
        return _generate_ollama(prompt, config)
    if provider == 'gemini':
        return _generate_gemini(prompt, config)
    if provider == 'deepseek':
        return _generate_deepseek(prompt, config)

    raise AIProviderError(
        f'AI_PROVIDER "{config.provider}" belum didukung. Gunakan: ollama, gemini, atau deepseek.'
    )


def _generate_ollama(prompt: str, config: AIConfig) -> str:
    base_url = settings.OLLAMA_BASE_URL.rstrip('/')
    payload = {
        'model': config.model,
        'prompt': prompt,
        'stream': False,
        'options': {'temperature': 0.2},
    }
    data = _post_json(
        url=f'{base_url}/api/generate',
        payload=payload,
        timeout=config.timeout_seconds,
        error_prefix=(
            'Ollama tidak bisa dihubungi. Pastikan Ollama berjalan di '
            f'{base_url} dan model {config.model} tersedia.'
        ),
    )
    answer = data.get('response')
    if not answer:
        raise AIProviderError('Ollama tidak mengembalikan field "response" yang valid.')
    return answer.strip()


def _generate_gemini(prompt: str, config: AIConfig) -> str:
    if not settings.GEMINI_API_KEY:
        raise AIProviderError('GEMINI_API_KEY belum diisi di file .env.')

    url = (
        f'{settings.GEMINI_BASE_URL.rstrip("/")}/v1beta/models/'
        f'{config.model}:generateContent?key={settings.GEMINI_API_KEY}'
    )
    payload = {
        'contents': [
            {
                'role': 'user',
                'parts': [{'text': prompt}],
            }
        ],
        'generationConfig': {
            'temperature': 0.2,
        },
    }
    data = _post_json(
        url=url,
        payload=payload,
        timeout=config.timeout_seconds,
        error_prefix='Gemini API gagal dihubungi atau menolak request.',
    )

    try:
        parts = data['candidates'][0]['content']['parts']
    except (KeyError, IndexError, TypeError) as exc:
        raise AIProviderError(f'Gemini tidak mengembalikan format jawaban yang valid: {data}') from exc

    answer = ''.join(part.get('text', '') for part in parts).strip()
    if not answer:
        raise AIProviderError('Gemini mengembalikan jawaban kosong.')
    return answer


def _generate_deepseek(prompt: str, config: AIConfig) -> str:
    if not settings.DEEPSEEK_API_KEY:
        raise AIProviderError('DEEPSEEK_API_KEY belum diisi di file .env.')

    payload = {
        'model': config.model,
        'messages': [
            {'role': 'user', 'content': prompt},
        ],
        'temperature': 0.2,
        'stream': False,
    }
    data = _post_json(
        url=f'{settings.DEEPSEEK_BASE_URL.rstrip("/")}/chat/completions',
        payload=payload,
        timeout=config.timeout_seconds,
        headers={'Authorization': f'Bearer {settings.DEEPSEEK_API_KEY}'},
        error_prefix='DeepSeek API gagal dihubungi atau menolak request.',
    )

    try:
        answer = data['choices'][0]['message']['content']
    except (KeyError, IndexError, TypeError) as exc:
        raise AIProviderError(f'DeepSeek tidak mengembalikan format jawaban yang valid: {data}') from exc

    if not answer:
        raise AIProviderError('DeepSeek mengembalikan jawaban kosong.')
    return answer.strip()


def _post_json(
    url: str,
    payload: dict,
    timeout: int,
    error_prefix: str,
    headers: dict | None = None,
) -> dict:
    request_headers = {'Content-Type': 'application/json'}
    if headers:
        request_headers.update(headers)

    try:
        response = requests.post(url, json=payload, headers=request_headers, timeout=timeout)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.ConnectionError as exc:
        raise AIProviderError(error_prefix) from exc
    except requests.exceptions.Timeout as exc:
        raise AIProviderError('Request ke provider AI timeout. Coba ulangi atau gunakan model yang lebih ringan.') from exc
    except requests.exceptions.HTTPError as exc:
        status_code = exc.response.status_code if exc.response is not None else 'unknown'
        detail = exc.response.text if exc.response is not None else ''
        raise AIProviderError(f'{error_prefix} HTTP {status_code}: {detail[:500]}') from exc
    except requests.exceptions.JSONDecodeError as exc:
        raise AIProviderError('Provider AI tidak mengembalikan JSON yang valid.') from exc
    except requests.exceptions.RequestException as exc:
        raise AIProviderError(f'Terjadi error saat memanggil provider AI: {exc}') from exc
