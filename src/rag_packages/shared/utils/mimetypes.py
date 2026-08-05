import mimetypes
import requests
import base64
# import magic


# extension can be of the form ".png" or "png"
def get_mime_type(extension: str = "png", default: str = "image/png"):
    if not extension.startswith("."):
        extension = "." + extension

    mime_type = mimetypes.types_map.get(extension.lower(), default)

    print(mime_type)  # eg. image/jpeg, image/png, application/pdf, etc.

    return mime_type


def guess_mime_type(filename: str, default: str = "application/octet-stream") -> str:
    mime_type, _ = mimetypes.guess_type(filename)
    return mime_type or default


def get_accurate_mime_type_content_type(file_url: str) -> str:
    content_type: str
    try:
        response = requests.head(file_url, allow_redirects=True, timeout=10)
        response.raise_for_status()

        content_type = response.headers.get("Content-Type")

    except requests.RequestException:
        response = requests.get(file_url, stream=True, timeout=10)
        response.raise_for_status()
        content_type = response.headers.get("Content-Type", "application/octet-stream")

    mime_type = content_type.split(";", 1)[0].strip()
    return mime_type


# def get_accurate_mime_type_python_magic(file_url: str) -> str:
#     response = requests.get(file_url, stream=True, timeout=10)
#     response.raise_for_status()
#     content_type = response.headers.get("Content-Type", "application/octet-stream")
#     fallback_mime_type = content_type.split(";", 1)[0].strip()

#     # Read the first 8 KB without downloading the entire file.
#     chunk = next(response.iter_content(chunk_size=8192), b"")
#     if not chunk:
#         return fallback_mime_type

#     mime_type = magic.from_buffer(chunk, mime=True)
#     if mime_type is not None and mime_type != "application/octet-stream":
#         return mime_type

#     return fallback_mime_type
