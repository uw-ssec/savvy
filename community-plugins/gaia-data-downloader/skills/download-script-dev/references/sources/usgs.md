# USGS Streamflow

**Description:** Real-time and historical streamflow, stage, and water temperature data from USGS stream gages across the US.

**Access Pattern:** REST API returning RDB (tab-separated) format

**Endpoint:** `https://nwis.waterservices.usgs.gov/nwis/iv/`

**Authentication:** None

**Key Libraries:** `requests`, `pandas`

**API Parameters:**
| Parameter | Description | Example |
|-----------|-------------|---------|
| `sites` | Comma-separated site numbers | `12200500,12201500` |
| `startDT` | Start date (ISO 8601) | `2024-01-01` |
| `endDT` | End date (ISO 8601) | `2024-01-31` |
| `parameterCd` | Parameter codes | `00060` (discharge), `00065` (stage), `00010` (temperature) |
| `format` | Response format | `rdb` |

**Access Example:**
```python
import requests
import pandas as pd
import io
import re

params = {
    "sites": "12200500",
    "startDT": "2024-01-01",
    "endDT": "2024-01-31",
    "parameterCd": "00060,00065",
    "format": "rdb",
}
response = requests.get("https://nwis.waterservices.usgs.gov/nwis/iv/", params=params)


def parse_rdb(text):
    """Parse an NWIS RDB response into one DataFrame.

    A multi-site response holds one table per site: each has its own
    `agency_cd ...` header and data-type row (5s 15s 20d ...), and the value
    columns carry a per-site time-series ID (e.g. 151445_00060).
    """
    blocks, skip_type_row = [], False
    for line in text.splitlines():
        if line.startswith("#") or not line.strip():
            continue
        if line.startswith("agency_cd"):
            blocks.append([line])           # header of a new site table
            skip_type_row = True
        elif skip_type_row:
            skip_type_row = False           # data-type row under each header
        elif blocks:
            blocks[-1].append(line)
    frames = []
    for block in blocks:
        df = pd.read_csv(io.StringIO("\n".join(block)), sep="\t", dtype={"site_no": str})
        # Drop the time-series ID prefix: 151445_00060 -> 00060, 151445_00060_cd -> 00060_cd,
        # unless a site has two series for one parameter (then keep the IDs)
        names = [re.sub(r"^\d+_(\d{5})", r"\1", c) for c in df.columns]
        if len(set(names)) == len(names):
            df.columns = names
        frames.append(df)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


df = parse_rdb(response.text)
```

**Notes:**
- Returns data in **local time zones** — convert to UTC using station timezone metadata
- RDB format has comment headers (`#`) and a data-type row below the column headers
- A multi-site request returns one table per site, each with its own header and data-type row; value columns are prefixed with a per-site time-series ID (`151445_00060`), so parse each block separately (`parse_rdb` above)
- Keep `site_no` as a string: site numbers can have leading zeros (`01646500`)
- Small data volumes (KB-MB per station)
- Rate limiting may apply for bulk requests — use delays between API calls
