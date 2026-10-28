#!/usr/bin/env python3
import hashlib
import http.client
import json
import os
from pathlib import Path
import re
import shutil
import sqlite3
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class BudgetReached(Exception):
    pass


class RegistryBudgetReached(Exception):
    pass


class IntegrityError(Exception):
    pass


class Meter:
    def __init__(self, config, state):
        self.config = config
        self.state = Path(state)
        self.state.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(self.state / "campaign.sqlite3")
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("PRAGMA synchronous=FULL")
        self.db.execute("CREATE TABLE IF NOT EXISTS counters (name TEXT PRIMARY KEY, value INTEGER NOT NULL)")
        self.db.commit()
        self.sample_interface()

    def get(self, key):
        row = self.db.execute("SELECT value FROM counters WHERE name=?", (key,)).fetchone()
        return row[0] if row else 0

    def put(self, key, value):
        self.db.execute("INSERT OR REPLACE INTO counters VALUES (?, ?)", (key, value))

    def sample_interface(self):
        interface = self.config.get("interface")
        if not interface:
            return
        root = Path("/sys/class/net") / interface / "statistics"
        if not root.exists():
            raise OSError(f"Network counter unavailable: {interface}")
        current = sum(int((root / name).read_text()) for name in ("rx_bytes", "tx_bytes"))
        previous = self.get("interface_last")
        delta = (current - previous if current >= previous else current) if previous else 0
        with self.db:
            self.put("interface_bytes", self.get("interface_bytes") + delta)
            self.put("interface_last", current)
        if self.get("interface_bytes") >= self.config["interface_limit_bytes"]:
            raise BudgetReached("Machine network allowance reached")

    def reserve(self, count, registry):
        self.sample_interface()
        if shutil.disk_usage(self.state).free < self.config["minimum_free_bytes"] + count:
            raise BudgetReached("Disk free-space reserve reached")
        with self.db:
            total, local = self.get("payload_bytes"), self.get(registry)
            if total + count > self.config["payload_limit_bytes"]:
                raise BudgetReached("Campaign transfer allowance reached")
            if local + count > self.config["budgets_bytes"][registry]:
                raise RegistryBudgetReached(registry)
            self.put("payload_bytes", total + count)
            self.put(registry, local + count)


class Downloader:
    def __init__(self, meter, opener=urlopen, sleeper=time.sleep):
        self.meter, self.opener, self.sleep = meter, opener, sleeper

    def fetch(self, url, target, registry, expected=None, algorithm="sha256", size=None):
        target = Path(target)
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists() and (expected is None or self.digest(target, algorithm) == expected):
            return target
        part = target.with_name(target.name + ".part")
        validator = target.with_name(target.name + ".validator")
        for attempt in range(8):
            try:
                offset = part.stat().st_size if part.exists() else 0
                if expected and offset and self.digest(part, algorithm) == expected:
                    os.replace(part, target)
                    return target
                if offset and not expected and not validator.exists():
                    part.unlink()
                    offset = 0
                headers = {"User-Agent": "Funmig-budget-mirror/1", "Accept-Encoding": "identity"}
                if offset:
                    headers["Range"] = f"bytes={offset}-"
                    if validator.exists():
                        headers["If-Range"] = validator.read_text()
                self.meter.reserve(65536, registry)
                with self.opener(Request(url, headers=headers), timeout=40) as response:
                    status = response.status
                    remaining = response.headers.get("Content-Length")
                    remaining = int(remaining) if remaining is not None else None
                    if status == 206:
                        match = re.fullmatch(r"bytes (\d+)-(\d+)/(\d+)", response.headers.get("Content-Range", ""))
                        if not match or int(match[1]) != offset:
                            raise IntegrityError("Invalid Content-Range")
                        total_size = int(match[3])
                    elif status == 200:
                        offset = 0
                        total_size = remaining
                    else:
                        raise IntegrityError(f"Unexpected HTTP status {status}")
                    if size is not None and total_size is not None and size != total_size:
                        raise IntegrityError("Upstream size differs from metadata")
                    etag = response.headers.get("ETag") or response.headers.get("Last-Modified")
                    if etag:
                        validator.write_text(etag)
                    elif validator.exists():
                        validator.unlink()
                    received = 0
                    last_report = 0
                    with part.open("ab" if offset else "wb") as output:
                        while remaining is None or received < remaining:
                            amount = min(1024 * 1024, remaining - received) if remaining is not None else 1024 * 1024
                            self.meter.reserve(amount, registry)
                            chunk = response.read(amount)
                            if not chunk:
                                break
                            output.write(chunk)
                            received += len(chunk)
                            if time.monotonic() - last_report >= 30:
                                progress = {"url": url, "file_bytes": offset + received,
                                            "total_bytes": total_size, "charged_bytes": self.meter.get("payload_bytes"),
                                            "machine_network_bytes": self.meter.get("interface_bytes")}
                                progress_path = self.meter.state / "transfer.json"
                                temporary = progress_path.with_suffix(".new")
                                temporary.write_text(json.dumps(progress) + "\n")
                                os.replace(temporary, progress_path)
                                last_report = time.monotonic()
                        output.flush()
                        os.fsync(output.fileno())
                    if remaining is not None and received != remaining:
                        raise OSError("Connection ended before Content-Length")
                    if size is not None and part.stat().st_size != size:
                        raise IntegrityError("Incomplete artifact")
                if expected and self.digest(part, algorithm) != expected:
                    part.unlink()
                    raise IntegrityError("Artifact checksum mismatch")
                os.replace(part, target)
                target.chmod(0o644)
                validator.unlink(missing_ok=True)
                return target
            except HTTPError as exc:
                if exc.code == 416:
                    part.unlink(missing_ok=True)
                    validator.unlink(missing_ok=True)
                elif exc.code not in (408, 429, 500, 502, 503, 504):
                    raise
                self.retry(url, attempt, exc)
            except (URLError, OSError, http.client.HTTPException, IntegrityError) as exc:
                self.retry(url, attempt, exc)
        raise OSError(f"Retry window exhausted: {url}")

    def retry(self, url, attempt, error):
        delay = min(300, 5 * 2 ** attempt)
        print(f"RETRY in {delay}s: {url}: {error}", flush=True)
        self.sleep(delay)

    @staticmethod
    def digest(path, algorithm):
        with Path(path).open("rb") as handle:
            return hashlib.file_digest(handle, algorithm).hexdigest()

    def json(self, url, registry):
        path = self.meter.state / "metadata" / (hashlib.sha256(url.encode()).hexdigest() + ".json")
        self.fetch(url, path, registry)
        try:
            return json.loads(path.read_text())
        except (ValueError, UnicodeError):
            path.unlink(missing_ok=True)
            raise
