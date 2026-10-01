import hashlib

from ingestion.download import sha256_file


def test_sha256_file(tmp_path):
    path = tmp_path / "sample.bin"
    payload = b"rockets-data\n"
    path.write_bytes(payload)

    assert sha256_file(path) == hashlib.sha256(payload).hexdigest()
