import os
import tempfile
import pytest
from app.core.storage import (
    LocalStorageService,
    get_storage_service,
    BaseStorageService,
)


def test_local_storage_lifecycle(tmp_path):
    storage = LocalStorageService(base_dir=str(tmp_path))

    # 1. Write binary data
    test_data = b"Preprocessed NASA Earth observation bytes"
    remote_path = "test/observations_sample.bin"
    saved_path = storage.write(remote_path, test_data)
    assert os.path.exists(saved_path)

    # 2. Exists
    assert storage.exists(remote_path) is True
    assert storage.exists("test/nonexistent.bin") is False

    # 3. Read
    content = storage.read(remote_path)
    assert content == test_data

    # 4. Metadata
    meta = storage.get_metadata(remote_path)
    assert meta["path"] == remote_path
    assert meta["size_bytes"] == len(test_data)
    assert meta["backend"] == "local"
    assert "updated_at" in meta

    # 5. List files
    files = storage.list_files(prefix="test")
    assert "test/observations_sample.bin" in files

    # 6. Upload & download
    local_src = os.path.join(tmp_path, "local_src.txt")
    with open(local_src, "w") as f:
        f.write("local file test")

    upload_dest = "uploaded/file.txt"
    assert storage.upload_file(local_src, upload_dest) is True
    assert storage.exists(upload_dest) is True

    download_dst = os.path.join(tmp_path, "downloaded.txt")
    assert storage.download_file(upload_dest, download_dst) is True
    with open(download_dst, "r") as f:
        assert f.read() == "local file test"

    # 7. Delete
    assert storage.delete(remote_path) is True
    assert storage.exists(remote_path) is False
    assert storage.delete(remote_path) is False


def test_storage_factory_fallback():
    """Verify that get_storage_service defaults safely to LocalStorageService without GCP credentials."""
    storage = get_storage_service()
    assert isinstance(storage, BaseStorageService)
    assert isinstance(storage, LocalStorageService)
