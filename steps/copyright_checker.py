"""Check video clips for copyright risk using yt-dlp metadata."""

import json
import subprocess


# Keywords that indicate copyright restrictions
_HIGH_RISK_KEYWORDS = [
    "all rights reserved", "no reuse", "copyrighted", "do not copy",
    "unauthorized use", "dmca", "takedown",
]
_MEDIUM_RISK_KEYWORDS = [
    "copyright", "licensed", "exclusive", "proprietary",
    "official channel", "network",
]
_LOW_RISK_INDICATORS = [
    "creative commons", "cc by", "free to use", "royalty free",
    "no copyright", "stock footage", "public domain",
]


def check_clip_copyright(video_url: str) -> dict:
    """Check a video URL for copyright risk indicators.

    Uses yt-dlp to extract metadata and analyzes description,
    license field, and channel info for risk signals.
    """
    try:
        result = subprocess.run(
            [
                "yt-dlp",
                video_url,
                "--dump-json",
                "--no-download",
                "--quiet",
                "--no-warnings",
            ],
            capture_output=True,
            text=True,
            timeout=15,
        )

        if result.returncode != 0 or not result.stdout.strip():
            return {
                "url": video_url,
                "risk_level": "medium",
                "license": "unknown",
                "warnings": ["Kon metadata niet ophalen - wees voorzichtig"],
            }

        data = json.loads(result.stdout)

    except (subprocess.TimeoutExpired, json.JSONDecodeError, Exception):
        return {
            "url": video_url,
            "risk_level": "medium",
            "license": "unknown",
            "warnings": ["Metadata ophalen mislukt - wees voorzichtig"],
        }

    license_info = data.get("license", "Standard YouTube License")
    description = (data.get("description", "") or "").lower()
    channel = data.get("channel", data.get("uploader", ""))

    warnings = []
    risk_level = "low"

    # Check for low-risk indicators first
    text_to_check = f"{description} {license_info}".lower()
    is_free = any(kw in text_to_check for kw in _LOW_RISK_INDICATORS)

    if is_free:
        return {
            "url": video_url,
            "risk_level": "low",
            "license": license_info,
            "channel": channel,
            "warnings": [],
        }

    # Check high-risk keywords
    for kw in _HIGH_RISK_KEYWORDS:
        if kw in text_to_check:
            risk_level = "high"
            warnings.append(f"Gevonden: '{kw}' in beschrijving/licentie")

    # Check medium-risk keywords (only if not already high)
    if risk_level != "high":
        for kw in _MEDIUM_RISK_KEYWORDS:
            if kw in text_to_check:
                risk_level = "medium"
                warnings.append(f"Let op: '{kw}' gevonden")

    # Standard YouTube License is medium risk by default
    if license_info == "Standard YouTube License" and risk_level == "low":
        risk_level = "medium"
        warnings.append("Standaard YouTube licentie - geen expliciete toestemming voor hergebruik")

    return {
        "url": video_url,
        "risk_level": risk_level,
        "license": license_info,
        "channel": channel,
        "warnings": warnings,
    }
