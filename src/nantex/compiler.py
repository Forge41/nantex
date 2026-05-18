import re
import requests


class CompileError(Exception):
    pass


def compile(content: str, compiler: str, api_url: str) -> bytes:
    payload = {
        "compiler": compiler,
        "resources": [{"main": True, "content": content}],
    }
    try:
        resp = requests.post(api_url, json=payload, timeout=30)
    except requests.exceptions.Timeout:
        raise CompileError("API timed out — check your connection or try again")
    except requests.exceptions.ConnectionError:
        raise CompileError("API unreachable — check your connection")
    except requests.exceptions.RequestException as e:
        raise CompileError(f"Request failed: {e}")

    if resp.status_code == 201:
        return resp.content

    if resp.status_code == 400:
        try:
            log = resp.json()["log_files"]["__main_document__.log"]
            msg = _extract_errors(log)
        except Exception:
            msg = resp.text[:300]
        raise CompileError(msg)

    raise CompileError(f"API error {resp.status_code}: {resp.text[:200]}")


def _extract_errors(log: str) -> str:
    lines = log.splitlines()
    result = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith("!"):
            result.append(line)
            # grab the following l.N line if present
            if i + 1 < len(lines) and re.match(r"l\.\d+", lines[i + 1]):
                result.append(lines[i + 1])
        i += 1
    return "\n".join(result) if result else "Compile failed (see terminal log)"
