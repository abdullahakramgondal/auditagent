"""The eval cache must know which code made a saved result (TODO item 57)."""

from eval.agent1_eval import CODE_FOLDERS, cache_state, code_fingerprint


def make_folder(root, files):
    """A folder called 'agents' under `root` that holds the given {file name: bytes} files."""
    folder = root / "agents"
    folder.mkdir(parents=True)
    for name, content in files.items():
        (folder / name).write_bytes(content)
    return folder


def test_the_same_code_gives_the_same_fingerprint(tmp_path):
    a = make_folder(tmp_path / "a", {"x.py": b"x = 1\n"})
    b = make_folder(tmp_path / "b", {"x.py": b"x = 1\n"})
    assert code_fingerprint([a]) == code_fingerprint([b])
    assert len(code_fingerprint([a])) == 12


def test_editing_a_file_changes_the_fingerprint(tmp_path):
    a = make_folder(tmp_path / "a", {"x.py": b"x = 1\n"})
    before = code_fingerprint([a])
    (a / "x.py").write_bytes(b"x = 2\n")
    assert code_fingerprint([a]) != before


def test_adding_a_file_changes_the_fingerprint(tmp_path):
    a = make_folder(tmp_path / "a", {"x.py": b"x = 1\n"})
    before = code_fingerprint([a])
    (a / "y.py").write_bytes(b"y = 1\n")
    assert code_fingerprint([a]) != before


def test_windows_and_unix_line_endings_give_the_same_fingerprint(tmp_path):
    unix = make_folder(tmp_path / "unix", {"x.py": b"x = 1\ny = 2\n"})
    windows = make_folder(tmp_path / "windows", {"x.py": b"x = 1\r\ny = 2\r\n"})
    assert code_fingerprint([unix]) == code_fingerprint([windows])


def test_a_saved_result_counts_only_if_the_current_code_made_it():
    assert cache_state({"code_hash": "abc"}, "abc") == "same"
    assert cache_state({"code_hash": "abc"}, "def") == "old"
    assert cache_state({"seconds": 1.0}, "abc") == "old"  # saved before fingerprints existed


def test_the_real_code_folders_exist_and_have_a_fingerprint():
    assert all(folder.is_dir() for folder in CODE_FOLDERS)
    assert len(code_fingerprint(CODE_FOLDERS)) == 12
