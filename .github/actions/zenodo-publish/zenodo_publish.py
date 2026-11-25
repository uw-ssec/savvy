#!/usr/bin/env python3
"""Publish files to Zenodo as a new record, or as a new version of an existing one.

Adapted from uw-ssec/presentations' .github/scripts/zenodo_publish.py. Standard
library only, so the action needs nothing installed beyond the runner's python3.

The existing record is found by searching the token owner's depositions for a
keyword unique to the project (ZENODO_RECORD_KEYWORD). The keyword is added to
every version's metadata, so the next run finds it.

Environment (set by action.yml from its inputs):
    ZENODO_TOKEN           Token with deposit:write and deposit:actions scopes.
    ZENODO_SANDBOX         true/1 targets sandbox.zenodo.org instead of zenodo.org.
    ZENODO_METADATA        Path to a JSON file of deposition metadata, such as
                           `cffconvert -f zenodo` output.
    ZENODO_FILES           Newline-separated paths of the files to upload.
    ZENODO_RECORD_KEYWORD  Keyword that identifies the record across versions.
    ZENODO_VERSION         Version string; overrides the metadata's version.
    ZENODO_UPLOAD_TYPE     Zenodo upload type, such as software.
    ZENODO_COMMUNITY       Community identifier to submit the record to; empty for none.
"""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


def truthy(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes", "on"}


def required_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        sys.exit(f"missing required input: {name}")
    return value


class ZenodoError(RuntimeError):
    pass


class Zenodo:
    def __init__(self, token: str, sandbox: bool = False) -> None:
        host = "sandbox.zenodo.org" if sandbox else "zenodo.org"
        self.api = f"https://{host}/api"
        self.token = token

    def request(self, method: str, url: str, *, params: dict | None = None, json_body=None,
                file_path: Path | None = None, timeout: int = 60):
        """Send one request and return the decoded JSON body, or None when there is none."""
        if params:
            url = f"{url}?{urllib.parse.urlencode(params)}"
        headers = {"Authorization": f"Bearer {self.token}"}
        data = None
        if json_body is not None:
            data = json.dumps(json_body).encode()
            headers["Content-Type"] = "application/json"
        elif file_path is not None:
            data = file_path.open("rb")
            headers["Content-Type"] = "application/octet-stream"
            headers["Content-Length"] = str(file_path.stat().st_size)
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                body = resp.read()
        except urllib.error.HTTPError as err:
            raise ZenodoError(f"Zenodo {method} {url} failed: {err.code}\n{err.read().decode(errors='replace')}") from None
        finally:
            if file_path is not None:
                data.close()
        return json.loads(body) if body else None

    def find_existing(self, keyword: str) -> dict | None:
        """Return the newest deposition carrying the keyword, or None."""
        matches = self.request(
            "GET",
            f"{self.api}/deposit/depositions",
            params={"q": f'keywords:"{keyword}"', "size": 100, "sort": "mostrecent"},
        )
        return matches[0] if matches else None

    def new_record(self) -> dict:
        return self.request("POST", f"{self.api}/deposit/depositions", json_body={})

    def new_version(self, deposit_id: int) -> dict:
        """Open a draft new version of a published record and return the draft."""
        resp = self.request("POST", f"{self.api}/deposit/depositions/{deposit_id}/actions/newversion")
        return self.request("GET", resp["links"]["latest_draft"])

    def replace_files(self, deposit: dict, files: list[Path]) -> None:
        """Delete the files a draft inherited, then upload files to its bucket."""
        for f in deposit.get("files", []):
            self.request("DELETE", f"{self.api}/deposit/depositions/{deposit['id']}/files/{f['id']}")
        bucket = deposit["links"]["bucket"]
        for path in files:
            self.request("PUT", f"{bucket}/{urllib.parse.quote(path.name)}", file_path=path, timeout=600)

    def set_metadata(self, deposit_id: int, metadata: dict) -> dict:
        return self.request("PUT", f"{self.api}/deposit/depositions/{deposit_id}", json_body={"metadata": metadata})

    def publish(self, deposit_id: int) -> dict:
        return self.request("POST", f"{self.api}/deposit/depositions/{deposit_id}/actions/publish")


def build_metadata(base: dict, *, keyword: str, version: str | None, upload_type: str,
                   community: str | None) -> dict:
    """Return deposition metadata: base plus the upload type, version, community and record keyword."""
    metadata = dict(base)
    license_ = metadata.get("license")
    if isinstance(license_, dict):  # .zenodo.json / cffconvert form: {"id": "BSD-3-Clause"}
        license_ = license_.get("id")
    if license_:
        metadata["license"] = license_.lower()
    metadata["upload_type"] = upload_type
    metadata.setdefault("access_right", "open")
    if version:
        metadata["version"] = version
    keywords = list(metadata.get("keywords", []))
    if keyword not in keywords:
        keywords.append(keyword)
    metadata["keywords"] = keywords
    if community:
        metadata["communities"] = [{"identifier": community}]
    return metadata


def open_draft(zen: Zenodo, existing: dict | None) -> dict:
    """Return the draft to publish: a new record, a new version, or a draft an earlier failed run left."""
    if existing is None:
        print("no existing record; creating a new deposition")
        return zen.new_record()
    if not existing.get("submitted", True):
        print(f"reusing unpublished draft {existing['id']} left by an earlier run")
        return existing
    print(f"found published deposition {existing['id']}; opening a new version")
    return zen.new_version(existing["id"])


def write_results(record_url: str | None, doi: str | None, concept_doi: str | None, title: str) -> None:
    output = os.environ.get("GITHUB_OUTPUT")
    if output:
        with open(output, "a", encoding="utf-8") as fh:
            fh.write(f"record-url={record_url or ''}\ndoi={doi or ''}\nconcept-doi={concept_doi or ''}\n")
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as fh:
            fh.write(f"## Zenodo publish: {title}\n\n- Record: <{record_url}>\n- DOI: `{doi}`\n- Concept DOI: `{concept_doi}`\n")


def main() -> int:
    token = required_env("ZENODO_TOKEN")
    sandbox = truthy(os.environ.get("ZENODO_SANDBOX"))
    keyword = required_env("ZENODO_RECORD_KEYWORD")
    metadata_path = Path(required_env("ZENODO_METADATA"))
    files = [Path(p.strip()) for p in required_env("ZENODO_FILES").splitlines() if p.strip()]
    for path in files:
        if not path.is_file():
            sys.exit(f"file not found: {path}")

    metadata = build_metadata(
        json.loads(metadata_path.read_text(encoding="utf-8")),
        keyword=keyword,
        version=os.environ.get("ZENODO_VERSION", "").strip() or None,
        upload_type=os.environ.get("ZENODO_UPLOAD_TYPE", "").strip() or "software",
        community=os.environ.get("ZENODO_COMMUNITY", "").strip() or None,
    )
    print(f"target: {'sandbox.zenodo.org' if sandbox else 'zenodo.org'}")
    print(f"version: {metadata.get('version')}")

    zen = Zenodo(token, sandbox=sandbox)
    deposit = open_draft(zen, zen.find_existing(keyword))
    deposit = zen.set_metadata(deposit["id"], metadata)
    zen.replace_files(deposit, files)
    published = zen.publish(deposit["id"])

    links = published.get("links", {})
    record_url = links.get("record_html") or links.get("html")
    doi = published.get("doi") or published.get("metadata", {}).get("doi")
    concept_doi = published.get("conceptdoi")
    print(f"published: {record_url}\nDOI: {doi}\nconcept DOI: {concept_doi}")
    write_results(record_url, doi, concept_doi, metadata.get("title", ""))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except ZenodoError as err:
        sys.exit(str(err))
