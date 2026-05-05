from __future__ import annotations

import argparse
import json
import logging
import os
import re
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

LOGGER = logging.getLogger("generate_wechat_tech_draft")
USER_AGENT = "Mozilla/5.0 (compatible; auto-video/1.0; +https://github.com/)"
DEFAULT_OPENAI_BASE_URL = "https://api.openai.com/v1"
DEFAULT_OPENAI_MODEL = "gpt-4o-mini"
DEFAULT_QWEN_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
DEFAULT_QWEN_MODEL = "qwen-plus"
DEFAULT_DEEPSEEK_BASE_URL = "https://api.deepseek.com/v1"
DEFAULT_DEEPSEEK_MODEL = "deepseek-chat"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate WeChat tech daily markdown draft from rendered prompt text."
    )
    parser.add_argument(
        "--input-prompt",
        type=Path,
        required=True,
        help="Rendered prompt text file.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="Output path for generated markdown draft.",
    )
    parser.add_argument(
        "--llm-provider",
        choices=("openai", "qwen", "deepseek"),
        default=_resolve_default_llm_provider(),
        help="LLM provider preset used to resolve default model and base URL.",
    )
    parser.add_argument(
        "--llm-base-url",
        default=_resolve_default_llm_base_url(),
        help="OpenAI-compatible base URL.",
    )
    parser.add_argument(
        "--llm-api-key",
        default=_resolve_default_llm_api_key(),
        help="LLM API key.",
    )
    parser.add_argument(
        "--llm-model",
        default=_resolve_default_llm_model(),
        help="Model name.",
    )
    parser.add_argument(
        "--system-prompt",
        default="你是一名专业的科技媒体编辑，请严格按用户提供的格式输出 Markdown 初稿。",
        help="Optional system prompt prepended to the request.",
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=0.4,
        help="Sampling temperature.",
    )
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=2200,
        help="Maximum output tokens.",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=int(os.getenv("LLM_TIMEOUT", "60")),
        help="HTTP timeout in seconds.",
    )
    parser.add_argument(
        "--save-raw-response",
        type=Path,
        help="Optional path to save raw JSON response for debugging.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable debug logging.",
    )
    return parser.parse_args()


def _resolve_default_llm_provider() -> str:
    provider = os.getenv("LLM_PROVIDER", "").strip().lower()
    if provider in {"openai", "qwen", "deepseek"}:
        return provider
    if os.getenv("DASHSCOPE_API_KEY", "").strip() or os.getenv("QWEN_API_KEY", "").strip():
        return "qwen"
    if os.getenv("DEEPSEEK_API_KEY", "").strip() or os.getenv("DEEPSEEK_KEY", "").strip():
        return "deepseek"
    return "openai"


def _resolve_default_llm_base_url() -> str:
    explicit = os.getenv("LLM_BASE_URL", "").strip()
    if explicit:
        return explicit

    provider = _resolve_default_llm_provider()
    if provider == "qwen":
        return os.getenv("DASHSCOPE_BASE_URL", "").strip() or DEFAULT_QWEN_BASE_URL
    if provider == "deepseek":
        return os.getenv("DEEPSEEK_BASE_URL", "").strip() or DEFAULT_DEEPSEEK_BASE_URL
    return os.getenv("OPENAI_BASE_URL", "").strip() or DEFAULT_OPENAI_BASE_URL


def _resolve_default_llm_api_key() -> str:
    explicit = os.getenv("LLM_API_KEY", "").strip()
    if explicit:
        return explicit

    provider = _resolve_default_llm_provider()
    if provider == "qwen":
        return os.getenv("DASHSCOPE_API_KEY", "").strip() or os.getenv("QWEN_API_KEY", "").strip()
    if provider == "deepseek":
        return os.getenv("DEEPSEEK_API_KEY", "").strip() or os.getenv("DEEPSEEK_KEY", "").strip()
    return os.getenv("OPENAI_API_KEY", "").strip()


def _resolve_default_llm_model() -> str:
    explicit = os.getenv("LLM_MODEL", "").strip()
    if explicit:
        return explicit

    provider = _resolve_default_llm_provider()
    if provider == "qwen":
        return os.getenv("QWEN_MODEL", "").strip() or DEFAULT_QWEN_MODEL
    if provider == "deepseek":
        return os.getenv("DEEPSEEK_MODEL", "").strip() or DEFAULT_DEEPSEEK_MODEL
    return os.getenv("OPENAI_MODEL", "").strip() or DEFAULT_OPENAI_MODEL


def setup_logging(verbose: bool) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


def load_prompt(input_path: Path) -> str:
    prompt = input_path.read_text(encoding="utf-8").strip()
    if not prompt:
        raise ValueError(f"Prompt file is empty: {input_path}")
    return prompt


def build_messages(system_prompt: str, user_prompt: str) -> list[dict[str, str]]:
    return [
        {"role": "system", "content": system_prompt.strip()},
        {"role": "user", "content": user_prompt.strip()},
    ]


def request_completion(
    *,
    base_url: str,
    api_key: str,
    model: str,
    messages: list[dict[str, str]],
    temperature: float,
    max_tokens: int,
    timeout: int,
) -> dict:
    if not api_key:
        raise ValueError("Missing LLM API key. Set --llm-api-key or environment variable.")

    url = f"{base_url.rstrip('/')}/chat/completions"
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    request = Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "User-Agent": USER_AGENT,
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json; charset=utf-8",
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        response_text = ""
        try:
            response_text = exc.read().decode("utf-8", errors="ignore").strip()
        except Exception:
            response_text = ""
        detail = response_text or exc.reason or "no response body"
        raise RuntimeError(
            f"LLM request failed model={model} base_url={base_url} status={exc.code} detail={detail}"
        ) from exc


def extract_content(raw_response: dict) -> str:
    choices = raw_response.get("choices")
    if not isinstance(choices, list) or not choices:
        raise ValueError(f"LLM response missing choices: {raw_response}")
    first_choice = choices[0]
    if not isinstance(first_choice, dict):
        raise ValueError(f"Invalid choice payload: {raw_response}")
    message = first_choice.get("message")
    if not isinstance(message, dict):
        raise ValueError(f"LLM response missing message: {raw_response}")
    content = message.get("content")
    if isinstance(content, list):
        text_parts = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                text_parts.append(str(item.get("text") or ""))
        content = "\n".join(part for part in text_parts if part)
    if not isinstance(content, str) or not content.strip():
        raise ValueError(f"LLM response missing content: {raw_response}")
    return content


def sanitize_markdown(content: str) -> str:
    text = content.strip()
    fenced = re.match(r"^```(?:markdown|md)?\s*\n([\s\S]*?)\n```\s*$", text, flags=re.IGNORECASE)
    if fenced:
        text = fenced.group(1).strip()
    return text + "\n"


def write_output(output_path: Path, content: str) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content, encoding="utf-8")


def maybe_write_raw_response(path: Path | None, raw_response: dict) -> None:
    if path is None:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(raw_response, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> int:
    args = parse_args()
    setup_logging(args.verbose)

    prompt_text = load_prompt(args.input_prompt)
    messages = build_messages(args.system_prompt, prompt_text)
    raw_response = request_completion(
        base_url=args.llm_base_url,
        api_key=args.llm_api_key,
        model=args.llm_model,
        messages=messages,
        temperature=args.temperature,
        max_tokens=args.max_tokens,
        timeout=args.timeout,
    )
    maybe_write_raw_response(args.save_raw_response, raw_response)
    markdown = sanitize_markdown(extract_content(raw_response))
    write_output(args.output, markdown)

    LOGGER.info("generated markdown draft written to %s", args.output)
    LOGGER.info("model=%s provider=%s", args.llm_model, args.llm_provider)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())