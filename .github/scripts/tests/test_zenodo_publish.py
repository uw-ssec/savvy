import importlib.util
import json
from pathlib import Path

import pytest
import yaml
from conftest import WORKFLOWS, run_step, workflow_step

ACTION_DIR = WORKFLOWS.parent / "actions" / "zenodo-publish"


@pytest.fixture(scope="module")
def zp():
    spec = importlib.util.spec_from_file_location("zenodo_publish", ACTION_DIR / "zenodo_publish.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# --- build_metadata -------------------------------------------------------------


def test_build_metadata_normalizes_cffconvert_license_and_adds_fields(zp):
    base = {"title": "savvy", "license": {"id": "BSD-3-Clause"}, "keywords": ["a"], "version": "26.11.0"}
    md = zp.build_metadata(base, keyword="uw-ssec-software:savvy", version="26.11.0+gabc1234",
                           upload_type="software", community="uw-ssec")
    assert md["license"] == "bsd-3-clause"
    assert md["version"] == "26.11.0+gabc1234"
    assert md["upload_type"] == "software"
    assert md["access_right"] == "open"
    assert md["communities"] == [{"identifier": "uw-ssec"}]
    assert md["keywords"] == ["a", "uw-ssec-software:savvy"]
    assert base["keywords"] == ["a"], "the input metadata must not be modified"


def test_build_metadata_keeps_keyword_once_and_version_without_override(zp):
    base = {"title": "t", "license": "cc-by-4.0", "keywords": ["k"], "version": "1.0"}
    md = zp.build_metadata(base, keyword="k", version=None, upload_type="presentation", community=None)
    assert md["keywords"] == ["k"]
    assert md["version"] == "1.0"
    assert md["license"] == "cc-by-4.0"
    assert "communities" not in md


# --- the publish flow against a fake Zenodo ---------------------------------------


class FakeZenodo:
    """Records calls; answers like the legacy deposit API."""

    def __init__(self, existing=None):
        self.existing = existing
        self.calls = []

    def find_existing(self, keyword):
        self.calls.append(("find", keyword))
        return self.existing

    def new_record(self):
        self.calls.append(("new_record",))
        return {"id": 1, "files": [], "links": {"bucket": "https://b/1"}}

    def new_version(self, deposit_id):
        self.calls.append(("new_version", deposit_id))
        return {"id": 2, "files": [{"id": "old"}], "links": {"bucket": "https://b/2"}}


def test_open_draft_creates_a_record_when_none_exists(zp):
    zen = FakeZenodo(existing=None)
    assert zp.open_draft(zen, None)["id"] == 1
    assert zen.calls == [("new_record",)]


def test_open_draft_opens_a_new_version_of_a_published_record(zp):
    zen = FakeZenodo()
    assert zp.open_draft(zen, {"id": 9, "submitted": True})["id"] == 2
    assert zen.calls == [("new_version", 9)]


def test_open_draft_reuses_a_draft_a_failed_run_left(zp):
    zen = FakeZenodo()
    draft = {"id": 7, "submitted": False}
    assert zp.open_draft(zen, draft) is draft
    assert zen.calls == []


def test_main_publishes_new_version_with_metadata_and_files(zp, tmp_path, monkeypatch):
    archive = tmp_path / "savvy-26.11.0.zip"
    archive.write_bytes(b"zip")
    metadata = tmp_path / "zenodo.json"
    metadata.write_text(json.dumps({"title": "savvy", "license": {"id": "BSD-3-Clause"}, "keywords": []}))
    output = tmp_path / "out"
    output.write_text("")

    calls = []

    def fake_request(self, method, url, *, params=None, json_body=None, file_path=None, timeout=60):
        calls.append((method, url, json_body, file_path))
        if method == "GET" and url.endswith("/deposit/depositions"):
            assert params["q"] == 'keywords:"uw-ssec-software:savvy"'
            return [{"id": 9, "submitted": True}]
        if url.endswith("/actions/newversion"):
            return {"links": {"latest_draft": "https://zenodo.org/api/deposit/depositions/10"}}
        if method == "GET":
            return {"id": 10, "files": [{"id": "f-old"}], "links": {"bucket": "https://zenodo.org/api/files/b10"}}
        if method == "PUT" and url.endswith("/deposit/depositions/10"):
            return {"id": 10, "files": [{"id": "f-old"}], "links": {"bucket": "https://zenodo.org/api/files/b10"}}
        if url.endswith("/actions/publish"):
            return {"doi": "10.5281/zenodo.10", "conceptdoi": "10.5281/zenodo.8",
                    "links": {"record_html": "https://zenodo.org/records/10"}}
        return None

    monkeypatch.setattr(zp.Zenodo, "request", fake_request)
    monkeypatch.setenv("ZENODO_TOKEN", "t")
    monkeypatch.setenv("ZENODO_SANDBOX", "false")
    monkeypatch.setenv("ZENODO_METADATA", str(metadata))
    monkeypatch.setenv("ZENODO_FILES", f"{archive}\n")
    monkeypatch.setenv("ZENODO_RECORD_KEYWORD", "uw-ssec-software:savvy")
    monkeypatch.setenv("ZENODO_VERSION", "26.11.0")
    monkeypatch.setenv("ZENODO_COMMUNITY", "uw-ssec")
    monkeypatch.setenv("GITHUB_OUTPUT", str(output))
    monkeypatch.delenv("GITHUB_STEP_SUMMARY", raising=False)

    assert zp.main() == 0

    assert all(url.startswith("https://zenodo.org/") for _, url, _, _ in calls), "production host"
    put_md = next(body for m, url, body, _ in calls if m == "PUT" and url.endswith("/deposit/depositions/10"))
    assert put_md["metadata"]["version"] == "26.11.0"
    assert put_md["metadata"]["license"] == "bsd-3-clause"
    assert "uw-ssec-software:savvy" in put_md["metadata"]["keywords"]
    assert ("DELETE", "https://zenodo.org/api/deposit/depositions/10/files/f-old", None, None) in calls
    assert ("PUT", "https://zenodo.org/api/files/b10/savvy-26.11.0.zip", None, archive) in calls
    assert calls[-1][1].endswith("/deposit/depositions/10/actions/publish")
    assert "doi=10.5281/zenodo.10" in output.read_text()
    assert "concept-doi=10.5281/zenodo.8" in output.read_text()


def test_sandbox_flag_targets_the_sandbox_host(zp):
    assert zp.Zenodo("t", sandbox=True).api == "https://sandbox.zenodo.org/api"
    assert zp.Zenodo("t", sandbox=False).api == "https://zenodo.org/api"


# --- the workflow ---------------------------------------------------------------------


def _set_version(tmp_path, cff_version, **env):
    (tmp_path / "CITATION.cff").write_text(f"cff-version: 1.2.0\ntitle: savvy\nversion: {cff_version}\n")
    script = workflow_step("zenodo-publish.yml", "Set version")
    return run_step(script, tmp_path, env, stubs={"pixi": "exit 0"})


def test_set_version_release_uses_tag_without_v(tmp_path):
    proc, out = _set_version(tmp_path, "26.11.0", EVENT="release", TAG="v26.11.0", SHA="1ad2911abcdef")
    assert proc.returncode == 0, proc.stderr
    assert out["version"] == "26.11.0"


def test_set_version_release_fails_when_tag_and_citation_disagree(tmp_path):
    proc, out = _set_version(tmp_path, "26.11.0", EVENT="release", TAG="v26.12.0", SHA="1ad2911abcdef")
    assert proc.returncode != 0
    assert "does not match CITATION.cff" in proc.stdout
    assert "version" not in out


def test_set_version_main_push_appends_commit(tmp_path):
    proc, out = _set_version(tmp_path, '"26.11.0"', EVENT="push", TAG="", SHA="1ad2911abcdef")
    assert proc.returncode == 0, proc.stderr
    assert out["version"] == "26.11.0+g1ad2911"


def test_set_version_manual_run_matches_a_main_push(tmp_path):
    proc, out = _set_version(tmp_path, "26.11.0", EVENT="workflow_dispatch", TAG="", SHA="2d6be7aabcdef")
    assert proc.returncode == 0, proc.stderr
    assert out["version"] == "26.11.0+g2d6be7a"


def test_only_a_published_release_reaches_production():
    doc = yaml.safe_load((WORKFLOWS / "zenodo-publish.yml").read_text(encoding="utf-8"))
    job = doc["jobs"]["publish"]
    assert "!github.event.release.prerelease" in job["if"]
    step = next(s for s in job["steps"] if s.get("name") == "Publish to Zenodo")
    assert step["with"]["token"] == (
        "${{ github.event_name == 'release' && secrets.ZENODO_TOKEN || secrets.ZENODO_SANDBOX_TOKEN }}"
    )
    assert step["with"]["sandbox"] == "${{ github.event_name == 'release' && 'false' || 'true' }}"
    triggers = doc.get("on", doc.get(True))
    assert triggers["release"]["types"] == ["published"]
    assert triggers["push"]["branches"] == ["main"]
    assert "workflow_dispatch" in triggers
