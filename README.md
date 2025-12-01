# Kingdom Archives Scraper

This repository provides a Python-based scraper for `kingdomarchives.com` that is designed to capture everything the site exposes: audio files, images (including agent portraits), downloadable documents, and supporting metadata. The tool crawls the site, queues discovered resources, and saves the content with descriptive filenames and JSON manifests for traceability.

## Features
- Recursive crawl constrained to `kingdomarchives.com` with optional depth and URL filters.
- Normalized output tree using slugs so assets are easy to identify by URL and media type.
- Persistent download queue to resume long runs.
- Metadata sidecars (content type, original URL, sha256 hash, size, and timestamp).
- CLI with configurable concurrency, rate limiting, and user agent.

## Quickstart
1. Create and activate a Python 3.10+ environment.
2. Install dependencies:
   ```bash
   pip install -e .
   ```
3. Run the scraper (dry run by default):
   ```bash
   kingdom-archives-scraper --output ./data/kingdomarchives --concurrency 8 --delay 0.5 --depth 3 --start-url https://kingdomarchives.com
   ```
   Use `--execute-downloads` to actually persist files once you are satisfied with the discovered queue.

## Output layout
```
output_root/
  manifests/
    crawl-state.json     # persisted queue and visited URLs
    downloads.log        # newline-delimited JSON of completed downloads
  media/
    audio/
    images/
    documents/
    other/
  html/
```

Each downloaded asset is accompanied by a `<name>.json` sidecar describing the retrieval.

## Notes
- The scraper respects the `kingdomarchives.com` host and will not follow links to other domains.
- A dry-run mode is enabled by default to let you inspect the crawl before downloading heavy assets.
- Adjust `--delay` if the target server needs more breathing room.
