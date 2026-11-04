"""
Installing CReaper on any drive: the pointer file shared by the bootstrapper and the app, where bulky data and TEMP
go, and moving an existing install. A drive other than C: is simulated with plain folders (the rules never look at
the drive letter except to check that it exists); tests/test_install_location_d_drive.py uses a real second drive
when the machine has one.
"""
import importlib.util
import json
import os
import tempfile

import pytest

from utils import install_location as il

BOOT = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "bootstrapper", "main.py")


@pytest.fixture
def appdata(tmp_path, monkeypatch):
    local = tmp_path / "local"
    local.mkdir()
    monkeypatch.setenv("LOCALAPPDATA", str(local))
    return local


@pytest.fixture
def boot(appdata):
    """The bootstrapper module, loaded fresh against this test's %LOCALAPPDATA%."""
    spec = importlib.util.spec_from_file_location("creaper_bootstrapper_loc", BOOT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.REAL_MAX_ROOT_LEN = mod.MAX_ROOT_LEN
    mod.MAX_ROOT_LEN = 400          # pytest's temp folders are deep; the length rule has its own test
    return mod


# ------------------------------------------------------------------------------------------------ the pointer
def test_no_pointer_means_the_default_layout(appdata):
    assert il.install_root() == il.anchor() == str(appdata / "CReaper")
    assert il.data_root() == il.anchor()
    assert il.data_path("projects", "a") == os.path.join(il.anchor(), "projects", "a")


def test_pointer_round_trip_and_relative_paths_are_ignored(appdata, tmp_path):
    il.write_location(str(tmp_path / "D" / "CReaper"), str(tmp_path / "D" / "CReaper" / "data"))
    loc = il.read_location()
    assert loc["install_root"] == os.path.normpath(str(tmp_path / "D" / "CReaper"))
    (appdata / "CReaper" / il.LOCATION_FILE).write_text(json.dumps({"install_root": "relative\\dir", "data_root": 5}))
    assert il.read_location() == {"install_root": "", "data_root": ""}
    (appdata / "CReaper" / il.LOCATION_FILE).write_text("{not json")
    assert il.read_location() == {"install_root": "", "data_root": ""}


def test_writing_the_default_folder_removes_the_entry(appdata):
    il.write_location(il.anchor(), il.anchor())
    assert json.loads((appdata / "CReaper" / il.LOCATION_FILE).read_text()) == {"version": 1}


# ------------------------------------------------------------------------------------------------ data paths
def test_bulky_folders_follow_the_data_root_but_settings_stay(appdata, tmp_path):
    drive = tmp_path / "D"
    drive.mkdir()
    il.write_location(str(drive / "CReaper"), str(drive / "CReaper" / "data"))
    data = str(drive / "CReaper" / "data")
    for name in il.BULK_DIRS:
        assert il.data_path(name, "x") == os.path.join(data, name, "x")
    assert il.data_path("settings.json") == os.path.join(il.anchor(), "settings.json")
    assert il.data_path("ui") == os.path.join(il.anchor(), "ui")
    assert il.data_path() == il.anchor()


def test_older_data_not_yet_carried_over_is_never_hidden(appdata, tmp_path):
    drive = tmp_path / "D"
    drive.mkdir()
    il.write_location(str(drive / "CReaper"), str(drive / "CReaper" / "data"))
    old = appdata / "CReaper" / "projects"
    old.mkdir(parents=True)
    assert il.data_path("projects", "p1") == os.path.join(str(old), "p1")          # only the old copy exists
    new = drive / "CReaper" / "data" / "projects"
    new.mkdir(parents=True)
    assert il.data_path("projects", "p1") == os.path.join(str(new), "p1")          # the new one wins once it exists


def test_a_missing_data_drive_falls_back_instead_of_inventing_a_tree(appdata):
    il.write_location(r"Q:\CReaper", r"Q:\CReaper\data")          # no such drive here
    assert not os.path.isdir("Q:" + os.sep)
    assert il.data_root() == il.anchor()
    assert il.install_root() == r"Q:\CReaper"                       # the install itself is not silently rerouted


def test_user_data_dir_and_the_whisper_models_use_the_data_root(appdata, tmp_path):
    from utils.app_paths import user_data_dir
    from services import caption_engine, storage_service
    drive = tmp_path / "D"
    drive.mkdir()
    il.write_location(str(drive / "CReaper"), str(drive / "CReaper" / "data"))
    data = str(drive / "CReaper" / "data")
    assert user_data_dir("cache", "plans") == os.path.join(data, "cache", "plans") and os.path.isdir(
        os.path.join(data, "cache", "plans"))
    assert caption_engine.get_models_dir() == os.path.join(data, "models", "whisper")
    assert storage_service.data_dir("music") == os.path.join(data, "music")
    assert user_data_dir() == il.anchor() and user_data_dir("ui") == os.path.join(il.anchor(), "ui")


def test_temp_follows_the_data_root(appdata, tmp_path, monkeypatch):
    drive = tmp_path / "D"
    drive.mkdir()
    for name in ("TEMP", "TMP", "TMPDIR"):
        monkeypatch.setenv(name, "C:\\Windows\\Temp")
    monkeypatch.setattr(tempfile, "tempdir", None)
    assert il.apply_temp_dir() == ""                                 # default layout: untouched
    il.write_location(str(drive / "CReaper"), str(drive / "CReaper" / "data"))
    tmp = il.apply_temp_dir()
    assert tmp == str(drive / "CReaper" / "data" / "tmp") and os.environ["TEMP"] == tmp
    assert tempfile.mkdtemp(prefix="creaper_t_").startswith(tmp)


def test_the_app_finds_its_install_root_from_its_own_exe():
    assert il.app_root_from_exe(r"D:\CReaper\versions\3.5.8\CReaper.exe") == r"D:\CReaper"
    assert il.app_root_from_exe(r"E:\My Games & Apps\CReaper\versions\3.5.8\CReaper.exe") == r"E:\My Games & Apps\CReaper"
    assert il.app_root_from_exe(r"C:\Python\python.exe") == ""


def test_the_bundled_bootstrapper_is_swapped_in_the_real_install_root(tmp_path):
    from utils import bootstrapper_refresh as br
    new, installed = br.paths(str(tmp_path / "app"), str(tmp_path / "local"), install_root=str(tmp_path / "D" / "CReaper"))
    assert installed == str(tmp_path / "D" / "CReaper" / br.BOOT_EXE) and new.endswith(os.path.join("bootstrapper", br.BOOT_EXE))
    assert br.paths("a", "b")[1] == os.path.join("b", "CReaper", br.BOOT_EXE)           # unchanged default


# ------------------------------------------------------------------------------------------------ bootstrapper
def test_bootstrapper_and_app_agree_on_the_pointer(boot, appdata, tmp_path):
    root = str(tmp_path / "D" / "CReaper")
    boot.write_location(root, os.path.join(root, "data"))
    assert il.read_location() == {"install_root": root, "data_root": os.path.join(root, "data")}
    il.write_location(root + "2", "")
    assert boot.read_location() == {"install_root": root + "2", "data_root": ""}
    assert boot.BULK_DIRS == il.BULK_DIRS and boot.LOCATION_FILE == os.path.join(il.anchor(), il.LOCATION_FILE)
    assert boot.FOLDER_NAME == il.FOLDER_NAME


def test_every_install_path_follows_the_chosen_folder(boot, appdata, tmp_path):
    assert boot.ROOT == str(appdata / "CReaper")                       # no pointer: where it always was
    root = str(tmp_path / "My Drive (D)" / "CReaper & co")
    boot.set_root(root)
    for p in (boot.VERSIONS_DIR, boot.STAGING_DIR, boot.DOWNLOAD_DIR, boot.STATE_FILE, boot.version_exe("3.5.8")):
        assert p.startswith(root)
    # what the app and the launcher must find in the SAME place whatever the root is
    assert boot.HANDOFF_FILE == os.path.join(il.anchor(), ".bootstrapper_handoff")
    assert boot.LOG_FILE == os.path.join(il.anchor(), "debug.log")


def test_a_fresh_start_reads_the_pointer(appdata, tmp_path):
    root = str(tmp_path / "E" / "CReaper")
    il.write_location(root, os.path.join(root, "data"))
    spec = importlib.util.spec_from_file_location("creaper_bootstrapper_loc2", BOOT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert mod.ROOT == root and mod.STATE_FILE == os.path.join(root, "state.json")
    assert not mod.is_first_run()


def test_the_folder_is_always_a_dedicated_creaper_folder(boot, tmp_path):
    d = boot.dedicated_folder
    assert d(str(tmp_path / "Games")) == str(tmp_path / "Games" / "CReaper")
    assert d(str(tmp_path / "creaper")) == str(tmp_path / "creaper")             # already named so (any case)
    assert d("D:\\") == os.path.join("D:\\", "CReaper")
    assert d("relative") == "" and d("") == ""
    assert d(f'"{tmp_path}"') == str(tmp_path / "CReaper")                        # quotes pasted from Explorer


def test_folder_checks_reject_what_cannot_work(boot, tmp_path):
    root, err = boot.check_install_folder(str(tmp_path / "My Videos & Stuff (new)" / "ünï"))
    assert err == "" and os.path.isdir(root) and not os.path.exists(os.path.join(root, ".write_test"))   # spaces, &, ()
    assert boot.check_install_folder("folder")[1]
    assert "Network folders" in boot.check_install_folder("\\\\server\\share\\x")[1]
    assert "not available" in boot.check_install_folder("Q:\\apps")[1]
    blocked = tmp_path / "file"
    blocked.write_text("x")
    assert "can't write" in boot.check_install_folder(str(blocked / "sub"))[1]


def test_too_little_free_space_is_refused(boot, tmp_path, monkeypatch):
    monkeypatch.setattr(boot.shutil, "disk_usage", lambda p: type("U", (), {"free": 10 * 1024 ** 2, "total": 1, "used": 0})())
    assert "free" in boot.check_install_folder(str(tmp_path / "x"))[1]


def test_first_run_is_asked_once_and_existing_installs_are_not(boot, appdata, tmp_path):
    assert boot.is_first_run()
    boot.apply_new_location(str(tmp_path / "D" / "CReaper"))
    assert not boot.is_first_run()
    # an install from before this feature: a state.json and the exe, no pointer -> never asked, nothing changes
    (appdata / "CReaper" / il.LOCATION_FILE).unlink()
    boot.set_root(str(appdata / "CReaper"))
    (appdata / "CReaper" / "versions" / "3.5.8").mkdir(parents=True)
    (appdata / "CReaper" / "versions" / "3.5.8" / "CReaper.exe").write_bytes(b"x")
    boot.write_state({"current": "3.5.8"})
    assert not boot.is_first_run() and boot.ROOT == str(appdata / "CReaper")


def test_choosing_the_default_folder_keeps_the_default_layout(boot, appdata):
    boot.apply_new_location(str(appdata / "CReaper"))
    assert il.read_location() == {"install_root": "", "data_root": ""} and il.install_root() == il.anchor()


def test_data_root_is_next_to_the_install(boot, appdata, tmp_path):
    assert boot.data_root_for(boot.ANCHOR) == boot.ANCHOR
    assert boot.data_root_for(str(tmp_path / "CReaper")) == str(tmp_path / "CReaper" / "data")


# ------------------------------------------------------------------------------------------------ moving an install
def _old_install(appdata):
    root = appdata / "CReaper"
    for v in ("3.5.7", "3.5.8"):
        (root / "versions" / v).mkdir(parents=True, exist_ok=True)
        (root / "versions" / v / "CReaper.exe").write_bytes(b"exe" + v.encode())
        (root / "versions" / v / "lib.dll").write_bytes(b"d" * 1000)
    (root / "versions" / "3.5.1").mkdir()                           # an old leftover: not carried
    (root / "projects" / "p1").mkdir(parents=True)
    (root / "projects" / "p1" / "project.json").write_text("{}")
    (root / "models" / "whisper").mkdir(parents=True)
    (root / "models" / "whisper" / "m.bin").write_bytes(b"m" * 500)
    (root / "settings.json").write_text('{"k": 1}')
    (root / "session.dat").write_bytes(b"token")
    state = {"current": "3.5.8", "previous": "3.5.7", "shortcut_target": "old"}
    return root, state


def test_moving_an_install_carries_the_app_and_the_data_and_keeps_the_account(boot, appdata, tmp_path):
    root, state = _old_install(appdata)
    boot.write_state(state)
    (root / boot.BOOT_EXE).write_bytes(b"old launcher")
    new = tmp_path / "D" / "CReaper"
    new.mkdir(parents=True)
    said = []
    data = boot.migrate_install(str(root), str(root), str(new), str(new / "data"), dict(state), said.append)
    assert data == str(new / "data")
    for v in ("3.5.7", "3.5.8"):
        assert (new / "versions" / v / "CReaper.exe").read_bytes() == b"exe" + v.encode()
        assert not (root / "versions" / v).exists()
    assert not (new / "versions" / "3.5.1").exists()
    assert (new / "data" / "projects" / "p1" / "project.json").exists() and not (root / "projects").exists()
    assert (new / "data" / "models" / "whisper" / "m.bin").read_bytes() == b"m" * 500
    # settings, sign-in and the pointer stay at the anchor; the state follows the install
    assert (root / "settings.json").read_text() == '{"k": 1}' and (root / "session.dat").read_bytes() == b"token"
    assert boot.ROOT == str(new) and json.loads((new / "state.json").read_text())["current"] == "3.5.8"
    assert "shortcut_target" not in json.loads((new / "state.json").read_text())
    assert not (root / "state.json").exists()
    assert il.read_location() == {"install_root": str(new), "data_root": str(new / "data")}
    # the app side now resolves everything to the new place
    assert il.data_path("projects", "p1") == str(new / "data" / "projects" / "p1")
    assert any("Moving" in m for m in said)
    # and the old launcher is retired on a later run, without touching settings or the sign-in
    boot.retire_old_install()
    assert not (root / boot.BOOT_EXE).exists() and (root / "settings.json").exists() and (root / "session.dat").exists()


def test_a_failed_move_leaves_the_old_install_untouched(boot, appdata, tmp_path, monkeypatch):
    root, state = _old_install(appdata)
    boot.write_state(state)
    new = tmp_path / "D" / "CReaper"
    new.mkdir(parents=True)
    real = boot.shutil.copytree

    def boom(src, dst, *a, **k):
        if os.path.basename(src) == "3.5.8":
            os.makedirs(dst)
            raise OSError("disk full")
        return real(src, dst, *a, **k)
    monkeypatch.setattr(boot.shutil, "copytree", boom)
    with pytest.raises(boot.UpdateError, match="Couldn't copy"):
        boot.migrate_install(str(root), str(root), str(new), str(new / "data"), dict(state), lambda m: None)
    assert (root / "versions" / "3.5.8" / "CReaper.exe").exists() and (root / "versions" / "3.5.7" / "CReaper.exe").exists()
    assert not (new / "versions" / "3.5.8").exists() and not (new / "versions" / "3.5.7").exists()
    assert boot.ROOT == str(root) and il.read_location()["install_root"] == ""      # still pointing at the old one
    assert (root / "projects" / "p1" / "project.json").exists()


def test_a_data_folder_that_cannot_move_stays_visible_to_the_app(boot, appdata, tmp_path, monkeypatch):
    root, state = _old_install(appdata)
    boot.write_state(state)
    new = tmp_path / "D" / "CReaper"
    new.mkdir(parents=True)
    real = boot.shutil.copytree

    def flaky(src, dst, *a, **k):
        if os.path.basename(src) == "projects":
            os.makedirs(dst)
            (open(os.path.join(dst, "half.bin"), "wb")).write(b"h")
            raise PermissionError("locked")
        return real(src, dst, *a, **k)
    monkeypatch.setattr(boot.shutil, "copytree", flaky)
    boot.migrate_install(str(root), str(root), str(new), str(new / "data"), dict(state), lambda m: None)
    assert (root / "projects" / "p1" / "project.json").exists()                      # original intact
    assert not (new / "data" / "projects").exists()                                    # no half copy to hide it
    assert il.data_path("projects", "p1") == str(root / "projects" / "p1")           # the app still finds the projects
    assert (new / "data" / "models" / "whisper" / "m.bin").exists()                  # the rest did move


def test_moving_needs_the_free_space_up_front(boot, appdata, tmp_path, monkeypatch):
    root, state = _old_install(appdata)
    new = tmp_path / "D" / "CReaper"
    new.mkdir(parents=True)
    monkeypatch.setattr(boot.shutil, "disk_usage", lambda p: type("U", (), {"free": 1024, "total": 1, "used": 0})())
    with pytest.raises(boot.UpdateError, match="enough free space"):
        boot.migrate_install(str(root), str(root), str(new), str(new / "data"), dict(state), lambda m: None)
    assert (root / "versions" / "3.5.8" / "CReaper.exe").exists()


def test_the_stale_default_install_is_cleaned_only_when_the_root_moved(boot, appdata, tmp_path):
    anchor = appdata / "CReaper"
    (anchor / "versions" / "3.5.8").mkdir(parents=True)
    (anchor / "settings.json").write_text("{}")
    boot.retire_old_install()                                          # root == anchor: nothing is removed
    assert (anchor / "versions" / "3.5.8").exists()
    boot.set_root(str(tmp_path / "D" / "CReaper"))
    boot.retire_old_install()
    assert not (anchor / "versions").exists() and (anchor / "settings.json").exists()


def test_install_dir_can_be_given_on_the_command_line(boot, monkeypatch):
    monkeypatch.setattr(boot.sys, "argv", ["boot.exe", "--install-dir", r"D:\My Apps\CReaper"])
    assert boot.command_line_value("--install-dir") == r"D:\My Apps\CReaper"
    monkeypatch.setattr(boot.sys, "argv", ["boot.exe", r"--install-dir=E:\x y"])
    assert boot.command_line_value("--install-dir") == r"E:\x y"
    monkeypatch.setattr(boot.sys, "argv", ["boot.exe", "--install-dir"])               # no value: ignored
    assert boot.command_line_value("--install-dir") == ""
    monkeypatch.setattr(boot.sys, "argv", ["boot.exe"])
    assert boot.command_line_value("--install-dir") == ""


def test_scripted_installs_can_skip_the_shortcuts(boot, appdata, monkeypatch, tmp_path):
    monkeypatch.setattr(boot.sys, "frozen", True, raising=False)
    root = tmp_path / "CReaper"
    root.mkdir()
    (root / boot.BOOT_EXE).write_bytes(b"x")
    boot.set_root(str(root))
    made = []
    monkeypatch.setattr(boot, "_make_shortcut", lambda *a: made.append(a))
    monkeypatch.setenv("CREAPER_NO_SHORTCUTS", "1")
    boot.ensure_shortcuts({}, True)
    assert made == []
    monkeypatch.delenv("CREAPER_NO_SHORTCUTS")
    boot.ensure_shortcuts({}, True)
    assert made and made[0][1] == str(root / boot.BOOT_EXE)


def test_a_folder_that_would_break_windows_path_limit_is_refused(boot, tmp_path):
    boot.MAX_ROOT_LEN = boot.REAL_MAX_ROOT_LEN
    assert boot.MAX_ROOT_LEN == 100
    deep = tmp_path
    while len(str(deep)) < boot.MAX_ROOT_LEN + 5:
        deep = deep / "a-long-folder-name"
    root, err = boot.check_install_folder(str(deep))
    assert root == "" and "too long" in err and "260" in err
    # the package's deepest file stays inside Windows' limit with the longest accepted folder
    longest_in_package = 101
    assert boot.MAX_ROOT_LEN + len("\versions\\") + len("99.99.99.99") + 1 + longest_in_package < 260 - 20


class _FakeWindow:
    closed = False

    def close(self):
        self.closed = True


def test_settings_shows_the_location_and_hands_over_to_the_launcher(appdata, tmp_path, monkeypatch):
    from ui import main_window_storage as ms
    mgr = ms.StorageManager(_FakeWindow())
    assert "Installed in" in mgr.install_location_text() and "stay in your Windows profile" in mgr.install_location_text()
    drive = tmp_path / "D"
    drive.mkdir()
    il.write_location(str(drive / "CReaper"), str(drive / "CReaper" / "data"))
    text = mgr.install_location_text()
    assert str(drive / "CReaper") in text and str(drive / "CReaper" / "data") in text

    started = []
    boot_exe = str(drive / "CReaper" / "CReaperBootstrapper.exe")
    monkeypatch.setattr(mgr, "bootstrapper_path", lambda: boot_exe)
    monkeypatch.setattr(mgr, "active_jobs", lambda: [])
    monkeypatch.setattr(ms, "ask", lambda *a, **k: "Continue")
    monkeypatch.setattr(ms.subprocess, "Popen", lambda cmd, **k: started.append(cmd))
    mgr.change_install_location()
    assert started == [[boot_exe, "--change-location"]] and mgr.mw.closed

    # a running job, a declined prompt, or a developer run (no launcher) change nothing
    mgr2 = ms.StorageManager(_FakeWindow())
    started.clear()
    monkeypatch.setattr(mgr2, "bootstrapper_path", lambda: boot_exe)
    monkeypatch.setattr(mgr2, "_status", lambda *a, **k: None)
    monkeypatch.setattr(mgr2, "active_jobs", lambda: ["Auto Clipper"])
    mgr2.change_install_location()
    monkeypatch.setattr(mgr2, "active_jobs", lambda: [])
    monkeypatch.setattr(ms, "ask", lambda *a, **k: "Cancel")
    mgr2.change_install_location()
    informed = []
    monkeypatch.setattr(mgr2, "bootstrapper_path", lambda: "")
    monkeypatch.setattr(ms, "inform", lambda *a, **k: informed.append(a))
    mgr2.change_install_location()
    assert started == [] and not mgr2.mw.closed and len(informed) == 1
