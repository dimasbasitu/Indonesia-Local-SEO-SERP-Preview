import os

import requests


SERPER_URL = "https://google.serper.dev/search"
DEFAULT_TIMEOUT = 90


class SerperError(RuntimeError):
    """Error aman untuk UI yang tidak membocorkan API key."""


def _request_search(payload: dict, api_key: str, timeout: int = DEFAULT_TIMEOUT) -> dict:
    if not api_key:
        raise SerperError("SERPER_API_KEY belum dikonfigurasi.")

    try:
        response = requests.post(
            SERPER_URL,
            json=payload,
            headers={
                "X-API-KEY": api_key,
                "Content-Type": "application/json",
            },
            timeout=timeout,
        )
    except requests.RequestException:
        raise SerperError("Tidak dapat terhubung ke Serper.dev.") from None

    if not response.ok:
        try:
            body = response.json()
            detail = body.get("message") or body.get("error") or response.reason
        except (ValueError, AttributeError):
            detail = response.reason
        raise SerperError(f"Serper.dev mengembalikan HTTP {response.status_code}: {detail}")

    try:
        result = response.json()
    except ValueError:
        raise SerperError("Serper.dev mengembalikan respons yang bukan JSON.") from None

    if not isinstance(result, dict):
        raise SerperError("Format respons Serper.dev tidak dikenali.")
    if result.get("error"):
        raise SerperError(f"Serper.dev gagal memproses pencarian: {result['error']}")
    return result


def run_serp_check(
    keyword: str,
    canonical_loc: str,
    gl: str = "id",
    hl: str = "id",
    api_key: str | None = None,
) -> dict:
    """Ambil hasil Google Search dari Serper.dev."""
    key = api_key or os.environ.get("SERPER_API_KEY", "")
    payload = {
        "q": keyword,
        "location": canonical_loc,
        "gl": gl,
        "hl": hl,
        "num": 10,
        "autocorrect": False,
    }
    return _request_search(payload, key)
