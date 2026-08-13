"""Read-only validation of Supabase environment configuration."""

import os
from urllib.parse import urlparse


def main():
    url = os.getenv("SUPABASE_URL", "").strip()
    key = os.getenv("SUPABASE_KEY", "").strip()
    parsed = urlparse(url) if url else None
    valid_url = bool(parsed and parsed.scheme == "https" and parsed.netloc)

    print(f"SUPABASE_URL configured: {'YES' if url else 'NO'}")
    print(f"SUPABASE_KEY configured: {'YES' if key else 'NO'}")
    print(f"SUPABASE_URL basic format valid: {'YES' if valid_url else 'NO'}")
    return 0 if url and key and valid_url else 1


if __name__ == "__main__":
    raise SystemExit(main())
