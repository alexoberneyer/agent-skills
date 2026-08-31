# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "requests>=2.31",
#     "python-dotenv>=1.0",
# ]
# ///
"""Fetch a single Notion page by URL or ID, including properties, content, and comments.

Outputs structured JSON to stdout. Debug/progress info goes to stderr.

Requires NOTION_API_KEY, from the environment or a .env file in the current
directory. The Notion integration must be shared with the page being fetched.

Usage:
    uv run fetch_notion_page.py <url-or-id>
    uv run fetch_notion_page.py <url-or-id> --no-content
    uv run fetch_notion_page.py <url-or-id> --no-comments
"""

import argparse
import json
import os
import re
import sys
import time
from datetime import datetime, timezone

import requests
from dotenv import load_dotenv

NOTION_API_VERSION = "2022-06-28"
RATE_LIMIT_DELAY = 0.35
MAX_RETRIES = 3
BACKOFF_BASE = 1.0


def log(msg: str) -> None:
    print(msg, file=sys.stderr)


def error_json(message: str, hint: str = "") -> str:
    payload = {"error": True, "message": message}
    if hint:
        payload["hint"] = hint
    return json.dumps(payload, indent=2)


def extract_page_id(url_or_id: str) -> str:
    """Extract a Notion page ID from a URL or raw ID.

    Supports formats:
    - https://www.notion.so/workspace/Page-Title-abc123def456...
    - https://www.notion.so/workspace/abc123def456...?v=...
    - abc123def456... (raw 32-char hex, with or without dashes)
    """
    url_or_id = url_or_id.strip()

    # If it looks like a UUID already (with dashes)
    uuid_pattern = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', re.I)
    if uuid_pattern.match(url_or_id):
        return url_or_id

    # If it's a 32-char hex string (no dashes)
    hex32_pattern = re.compile(r'^[0-9a-f]{32}$', re.I)
    if hex32_pattern.match(url_or_id):
        h = url_or_id
        return f"{h[:8]}-{h[8:12]}-{h[12:16]}-{h[16:20]}-{h[20:]}"

    # Extract from URL — the page ID is the last 32 hex chars before any query string
    match = re.search(r'([0-9a-f]{32})', url_or_id.split('?')[0], re.I)
    if match:
        h = match.group(1)
        return f"{h[:8]}-{h[8:12]}-{h[12:16]}-{h[16:20]}-{h[20:]}"

    # Try extracting UUID with dashes from URL
    match = re.search(r'([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})', url_or_id, re.I)
    if match:
        return match.group(1)

    return url_or_id  # Return as-is, let the API fail with a clear error


def make_request(session: requests.Session, method: str, url: str, **kwargs) -> dict:
    """Make a Notion API request with rate limiting and retry on 429."""
    for attempt in range(MAX_RETRIES):
        time.sleep(RATE_LIMIT_DELAY)
        resp = session.request(method, url, **kwargs)

        if resp.status_code == 429:
            retry_after = float(resp.headers.get("Retry-After", BACKOFF_BASE * (2 ** attempt)))
            log(f"  Rate limited, retrying in {retry_after:.1f}s (attempt {attempt + 1}/{MAX_RETRIES})")
            time.sleep(retry_after)
            continue

        resp.raise_for_status()
        return resp.json()

    # Final attempt
    time.sleep(RATE_LIMIT_DELAY)
    resp = session.request(method, url, **kwargs)
    resp.raise_for_status()
    return resp.json()


def extract_property_value(prop: dict) -> object:
    """Extract a human-readable value from a Notion property object."""
    prop_type = prop.get("type", "")

    if prop_type == "title":
        return "".join(t.get("plain_text", "") for t in prop.get("title", []))
    elif prop_type == "rich_text":
        return "".join(t.get("plain_text", "") for t in prop.get("rich_text", []))
    elif prop_type == "number":
        return prop.get("number")
    elif prop_type == "select":
        sel = prop.get("select")
        return sel["name"] if sel else None
    elif prop_type == "multi_select":
        return [s["name"] for s in prop.get("multi_select", [])]
    elif prop_type == "status":
        st = prop.get("status")
        return st["name"] if st else None
    elif prop_type == "date":
        d = prop.get("date")
        if d:
            return {"start": d.get("start"), "end": d.get("end")}
        return None
    elif prop_type == "people":
        return [p.get("name", p.get("id", "")) for p in prop.get("people", [])]
    elif prop_type == "checkbox":
        return prop.get("checkbox")
    elif prop_type == "url":
        return prop.get("url")
    elif prop_type == "email":
        return prop.get("email")
    elif prop_type == "phone_number":
        return prop.get("phone_number")
    elif prop_type == "formula":
        formula = prop.get("formula", {})
        f_type = formula.get("type", "")
        return formula.get(f_type)
    elif prop_type == "relation":
        return [r["id"] for r in prop.get("relation", [])]
    elif prop_type == "rollup":
        rollup = prop.get("rollup", {})
        r_type = rollup.get("type", "")
        return rollup.get(r_type)
    elif prop_type == "created_time":
        return prop.get("created_time")
    elif prop_type == "created_by":
        cb = prop.get("created_by", {})
        return cb.get("name", cb.get("id", ""))
    elif prop_type == "last_edited_time":
        return prop.get("last_edited_time")
    elif prop_type == "last_edited_by":
        lb = prop.get("last_edited_by", {})
        return lb.get("name", lb.get("id", ""))
    elif prop_type == "files":
        return [f.get("name", f.get("external", {}).get("url", "")) for f in prop.get("files", [])]
    elif prop_type == "unique_id":
        uid = prop.get("unique_id", {})
        prefix = uid.get("prefix", "")
        number = uid.get("number", "")
        return f"{prefix}-{number}" if prefix else str(number)
    else:
        return f"<unsupported type: {prop_type}>"


def extract_block_text(block: dict) -> str:
    """Extract plain text from a single Notion block."""
    block_type = block.get("type", "")
    block_data = block.get(block_type, {})

    rich_text = block_data.get("rich_text", [])
    if rich_text:
        text = "".join(t.get("plain_text", "") for t in rich_text)
        if block_type == "bulleted_list_item":
            return f"• {text}"
        elif block_type == "numbered_list_item":
            return f"- {text}"
        elif block_type.startswith("heading"):
            level = block_type[-1]  # heading_1, heading_2, heading_3
            return f"{'#' * int(level)} {text}"
        elif block_type == "to_do":
            checked = "x" if block_data.get("checked") else " "
            return f"[{checked}] {text}"
        elif block_type == "code":
            lang = block_data.get("language", "")
            return f"```{lang}\n{text}\n```"
        elif block_type == "quote":
            return f"> {text}"
        elif block_type == "callout":
            icon = block_data.get("icon", {})
            emoji = icon.get("emoji", "") if icon.get("type") == "emoji" else ""
            return f"{emoji} {text}".strip()
        elif block_type == "toggle":
            return f"▸ {text}"
        return text

    if block_type == "divider":
        return "---"
    if block_type == "child_database":
        return f"[Database: {block_data.get('title', '')}]"
    if block_type == "child_page":
        return f"[Page: {block_data.get('title', '')}]"
    if block_type == "image":
        img = block_data.get("file", block_data.get("external", {}))
        url = img.get("url", "")
        caption = "".join(t.get("plain_text", "") for t in block_data.get("caption", []))
        return f"[Image: {caption or url}]"
    if block_type == "bookmark":
        url = block_data.get("url", "")
        caption = "".join(t.get("plain_text", "") for t in block_data.get("caption", []))
        return f"[Bookmark: {caption or url}]"
    if block_type == "table":
        return "[Table]"

    return ""


def fetch_page_content(session: requests.Session, page_id: str) -> str:
    """Fetch all block children of a page (recursively) and return as plain text."""
    lines = []
    _fetch_blocks_recursive(session, page_id, lines, depth=0)
    return "\n".join(lines)


def _fetch_blocks_recursive(session: requests.Session, block_id: str, lines: list, depth: int) -> None:
    """Recursively fetch blocks and their children."""
    url = f"https://api.notion.com/v1/blocks/{block_id}/children"
    params = {"page_size": 100}
    has_more = True

    while has_more:
        data = make_request(session, "GET", url, params=params)
        for block in data.get("results", []):
            indent = "  " * depth
            text = extract_block_text(block)
            if text:
                for line in text.split("\n"):
                    lines.append(f"{indent}{line}")

            # Recurse into children if present
            if block.get("has_children"):
                _fetch_blocks_recursive(session, block["id"], lines, depth + 1)

        has_more = data.get("has_more", False)
        if has_more:
            params["start_cursor"] = data["next_cursor"]


def fetch_comments(session: requests.Session, page_id: str) -> list[dict]:
    """Fetch all comments on a page via GET /v1/comments?block_id={page_id}."""
    url = "https://api.notion.com/v1/comments"
    params = {"block_id": page_id, "page_size": 100}
    comments = []
    has_more = True

    while has_more:
        data = make_request(session, "GET", url, params=params)
        for comment in data.get("results", []):
            rich_text = comment.get("rich_text", [])
            text = "".join(t.get("plain_text", "") for t in rich_text)
            author = comment.get("created_by", {})
            author_name = author.get("name", author.get("id", "unknown"))
            comments.append({
                "author": author_name,
                "created_time": comment.get("created_time", ""),
                "text": text,
            })
        has_more = data.get("has_more", False)
        if has_more:
            params["start_cursor"] = data["next_cursor"]

    return comments


def fetch_page(session: requests.Session, page_id: str) -> dict:
    """Fetch a single page's metadata and properties."""
    url = f"https://api.notion.com/v1/pages/{page_id}"
    return make_request(session, "GET", url)


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch a Notion page by URL or ID")
    parser.add_argument("page", help="Notion page URL or page ID")
    parser.add_argument("--no-content", action="store_true", help="Skip fetching page body content")
    parser.add_argument("--no-comments", action="store_true", help="Skip fetching comments")
    args = parser.parse_args()

    dotenv_path = os.path.join(os.getcwd(), ".env")
    load_dotenv(dotenv_path)

    api_key = os.environ.get("NOTION_API_KEY", "").strip()
    if not api_key:
        print(error_json(
            "Missing NOTION_API_KEY environment variable",
            "Export it, or add it to a .env file in the directory you run from:\n"
            "  NOTION_API_KEY=ntn_...\n\n"
            "Create the token at https://www.notion.so/my-integrations, then share\n"
            "the page with that integration (page > ... > Connections)."
        ))
        sys.exit(1)

    page_id = extract_page_id(args.page)
    log(f"Fetching page: {page_id}")

    session = requests.Session()
    session.headers.update({
        "Authorization": f"Bearer {api_key}",
        "Notion-Version": NOTION_API_VERSION,
        "Content-Type": "application/json",
    })

    try:
        # Fetch page metadata + properties
        log("Fetching page metadata...")
        page = fetch_page(session, page_id)

        # Extract properties
        props = page.get("properties", {})
        extracted_props = {}
        title = ""
        for name, prop in props.items():
            value = extract_property_value(prop)
            extracted_props[name] = value
            if prop.get("type") == "title":
                title = value

        log(f"  Title: {title}")

        # Fetch content
        content = ""
        if not args.no_content:
            log("Fetching page content (blocks)...")
            content = fetch_page_content(session, page_id)
            log(f"  Fetched {len(content.splitlines())} lines of content")

        # Fetch comments
        comments = []
        if not args.no_comments:
            log("Fetching comments...")
            comments = fetch_comments(session, page_id)
            log(f"  Fetched {len(comments)} comments")

        output = {
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "page_id": page_id,
            "url": page.get("url", ""),
            "title": title,
            "created_time": page.get("created_time", ""),
            "last_edited_time": page.get("last_edited_time", ""),
            "properties": extracted_props,
        }
        if not args.no_content:
            output["content"] = content
        if not args.no_comments:
            output["comments"] = comments

        print(json.dumps(output, indent=2, ensure_ascii=False, default=str))
        log("Done.")

    except requests.exceptions.HTTPError as e:
        status = e.response.status_code if e.response is not None else "unknown"
        body = ""
        if e.response is not None:
            try:
                body = e.response.json().get("message", e.response.text[:500])
            except Exception:
                body = e.response.text[:500]

        hint = "Check that your NOTION_API_KEY is valid and the integration has access to this page."
        if status == 404:
            hint = (
                "Page not found. Make sure:\n"
                "1. The URL/ID is correct\n"
                "2. The Notion integration is shared with this page "
                "(open the page → '...' → 'Add connections' → select your integration)"
            )

        print(error_json(f"Notion API error (HTTP {status}): {body}", hint))
        sys.exit(1)
    except requests.exceptions.ConnectionError:
        print(error_json("Could not connect to Notion API. Check your internet connection."))
        sys.exit(1)
    except Exception as e:
        print(error_json(f"Unexpected error: {type(e).__name__}: {e}"))
        sys.exit(1)


if __name__ == "__main__":
    main()
