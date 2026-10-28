# Authorized 350 GB campaign

The user authorized this campaign on 2026-09-22. It does not unlock the legacy
450 GiB sync service. All limits here use decimal GB, not GiB.

- Metered HTTP allowance: 330 GB, including retries, metadata and conservative
  per-request overhead. Per-registry allocations total 320 GB.
- Additional guard: stop at 345 GB of RX+TX on enp2s0 since campaign creation.
  This includes unrelated traffic on this machine; it does not see other devices
  on the same Internet subscription or the ISP's accounting.
- Minimum disk reserve: 50 GB.
- Signed APT snapshots: Debian trixie and Ubuntu noble, including update/security
  pockets; amd64 packages. Components that cannot fit are skipped.
- Python: three recent stable versions plus versions selected by dependency
  constraints, Linux x86_64 and universal wheels plus source archives.
- npm: two recent stable versions plus dependency constraints, at most 2,000
  metadata jobs per language registry. This is curated coverage, not a guarantee
  that every project or optional build dependency installs offline.
- Docker images and AI model weights are not included in this campaign.

The queue, byte counters and partial files persist under
`/media/arshia/New Volume1/funmig-mirror/sync-state/2026-09-22-350gb`.
Interruptions use HTTP Range, checksum verification and increasing retry delays.
An upstream that ignores Range restarts that file and charges the repeated bytes.
Completed artifacts are reused. Budget exhaustion does not reset on restart.
Persistent failures remain visible in the SQLite jobs table.

```sh
systemctl --user status funmig-download-350gb
journalctl --user -u funmig-download-350gb -f
systemctl --user stop funmig-download-350gb
systemctl --user start funmig-download-350gb
python3 scripts/download_campaign.py status
```

The enabled user service and user lingering allow continuation after logout and
restart after reboot. Once the queue or budget is exhausted it exits successfully.
Do not remove the campaign state or create a second campaign against the same
Internet allowance. APT InRelease/indexes are published only after all selected
packages in that suite have completed; expired snapshots are not published.
