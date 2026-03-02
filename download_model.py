"""Download the word embedding model into the models/ directory.

Usage::

    python download_model.py

The script downloads the French Word2Vec model
``frWac_no_postag_no_phrase_700_skip_cut50.bin`` from
https://embeddings.net into ``models/``.  It is idempotent: if the file
already exists it prints a confirmation message and exits without
re-downloading.

Model details
-------------
* Source: https://embeddings.net/embeddings/frWac_no_postag_no_phrase_700_skip_cut50.bin
* Format: binary Word2Vec (readable by :func:`gensim.models.KeyedVectors.load_word2vec_format`)
* Approx. disk space: ~1 GB
* Licence: `CC BY 3.0 <https://creativecommons.org/licenses/by/3.0/>`_ – please
  attribute *ATILF / CNRS & Université de Lorraine* when redistributing.
"""

import pathlib
import sys
import urllib.request

MODEL_URL = (
    "https://embeddings.net/embeddings/frWac_no_postag_no_phrase_700_skip_cut50.bin"
)
MODEL_FILENAME = "frWac_no_postag_no_phrase_700_skip_cut50.bin"
MODELS_DIR = pathlib.Path("models")
BYTES_PER_MIB = 1_048_576


def download_model(dest_dir: pathlib.Path = MODELS_DIR) -> pathlib.Path:
    """Download the Word2Vec model into *dest_dir*.

    The download is skipped when the file is already present.

    Args:
        dest_dir: Directory where the model file will be saved.
            Defaults to ``models/`` relative to the current working directory.

    Returns:
        Path to the (existing or newly downloaded) model file.
    """
    dest_dir.mkdir(parents=True, exist_ok=True)
    model_path = dest_dir / MODEL_FILENAME

    if model_path.exists():
        print(f"Model already present at {model_path} — skipping download.")
        return model_path

    print(f"Downloading model to {model_path} …")
    print(f"Source: {MODEL_URL}")
    print("(~1 GB — this may take a while)\n")

    def _reporthook(block_count: int, block_size: int, total_size: int) -> None:
        downloaded = block_count * block_size
        if total_size > 0:
            pct = min(downloaded / total_size * 100, 100)
            sys.stdout.write(
                f"\r  {pct:5.1f}%  ({downloaded // BYTES_PER_MIB} MB"
                f" / {total_size // BYTES_PER_MIB} MB)"
            )
            sys.stdout.flush()

    urllib.request.urlretrieve(MODEL_URL, model_path, reporthook=_reporthook)
    print("\nDownload complete.")
    return model_path


if __name__ == "__main__":
    download_model()

