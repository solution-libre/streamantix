"""Download the word embedding model into the models/ directory."""

import pathlib

MODELS_DIR = pathlib.Path("models")


def download_model() -> None:
    """Download and save the word2vec model for semantic similarity scoring.

    This function is a placeholder. Implement the actual download logic here,
    e.g. using gensim.downloader or fetching a custom model file.
    """
    MODELS_DIR.mkdir(exist_ok=True)
    print("Model download not yet implemented. Place your model in the models/ directory.")


if __name__ == "__main__":
    download_model()
