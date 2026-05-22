import os
import time
import tempfile
import requests
from utils.config import UNSPLASH_KEY


def get_image_from_unsplash(keyword, output_folder, log_callback=None):
    """Download a high-quality image from Unsplash.

    Saves to a temp file so it can be cleaned up after placement.
    Returns the path on success, None on failure.
    """
    if log_callback:
        log_callback(f"[INFO] Fetching background from Unsplash: '{keyword}'...")

    # Build a list of search terms with fallbacks
    search_terms = [keyword]
    if len(keyword.split()) > 1:
        search_terms.append(keyword.split()[0])
    search_terms.append("abstract texture")

    for search_term in search_terms:
        try:
            api_url = (
                f"https://api.unsplash.com/photos/random"
                f"?query={search_term}"
                f"&orientation=landscape"
                f"&client_id={UNSPLASH_KEY}"
            )
            response = requests.get(api_url, timeout=15)
            if response.status_code == 200:
                data = response.json()
                image_url = data.get("urls", {}).get("regular")
                if not image_url:
                    continue

                # Download the actual image bytes
                img_response = requests.get(image_url, timeout=30)
                if img_response.status_code != 200:
                    continue

                # Validate we got actual image data (at least 5 KB)
                if len(img_response.content) < 5000:
                    if log_callback:
                        log_callback(f"[WARNING] Downloaded image too small, skipping.")
                    continue

                # Save to OS temp dir (not output folder) to avoid file-lock issues
                safe_keyword = "".join(c for c in search_term if c.isalnum())
                image_path = os.path.join(
                    tempfile.gettempdir(),
                    f"unsplash_{safe_keyword}_{int(time.time())}.jpg"
                )
                with open(image_path, "wb") as f:
                    f.write(img_response.content)

                # Verify the file was written correctly
                if os.path.getsize(image_path) < 5000:
                    os.remove(image_path)
                    continue

                if log_callback:
                    log_callback(f"[INFO] Unsplash image downloaded: '{search_term}'")
                return image_path
            else:
                if log_callback:
                    log_callback(
                        f"[WARNING] Unsplash search failed for '{search_term}' "
                        f"(Status: {response.status_code}). Trying fallback..."
                    )
        except Exception as e:
            if log_callback:
                log_callback(f"[WARNING] Unsplash error for '{search_term}': {e}")

    if log_callback:
        log_callback("[ERROR] All Unsplash fetch attempts failed.")
    return None
