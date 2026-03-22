#!/usr/bin/env python3
"""
sophia-edge-node: RetroAchievements -> RTC Reward Bridge

Polls RetroAchievements.org for recently unlocked achievements, classifies
them by point value into reward tiers, and submits RTC reward claims to the
RustChain network.

Hardcore mode achievements earn 2x multiplier.
Game mastery (100% completion) awards a bonus.
Daily cap prevents runaway spending.
"""

import json
import logging
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("sophia-achievements")

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
CONFIG_PATH = os.environ.get(
    "SOPHIA_CONFIG", "/opt/sophia-edge-node/config.json"
)
STATE_DIR = Path.home() / ".sophia-edge"
REPORTED_PATH = STATE_DIR / "reported.json"
DAILY_LOG_PATH = STATE_DIR / "daily_rewards.json"

# ---------------------------------------------------------------------------
# State persistence
# ---------------------------------------------------------------------------

def load_reported() -> Dict:
    """Load set of already-reported achievement IDs and mastered game IDs."""
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    if REPORTED_PATH.exists():
        try:
            return json.loads(REPORTED_PATH.read_text())
        except (json.JSONDecodeError, OSError):
            pass
    return {"achievements": [], "mastered_games": []}


def save_reported(data: Dict) -> None:
    """Persist reported achievement/mastery state."""
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    REPORTED_PATH.write_text(json.dumps(data, indent=2))


def get_daily_spent() -> float:
    """Return total RTC claimed today."""
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if DAILY_LOG_PATH.exists():
        try:
            daily = json.loads(DAILY_LOG_PATH.read_text())
            if daily.get("date") == today:
                return daily.get("total_rtc", 0.0)
        except (json.JSONDecodeError, OSError):
            pass
    return 0.0


def add_daily_spent(amount: float) -> float:
    """Record additional RTC spent today. Returns new total."""
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    daily = {"date": today, "total_rtc": 0.0, "claims": []}
    if DAILY_LOG_PATH.exists():
        try:
            loaded = json.loads(DAILY_LOG_PATH.read_text())
            if loaded.get("date") == today:
                daily = loaded
        except (json.JSONDecodeError, OSError):
            pass

    daily["date"] = today
    daily["total_rtc"] = daily.get("total_rtc", 0.0) + amount
    daily["claims"].append({
        "amount": amount,
        "time": datetime.now(timezone.utc).isoformat(),
    })
    DAILY_LOG_PATH.write_text(json.dumps(daily, indent=2))
    return daily["total_rtc"]


# ---------------------------------------------------------------------------
# Reward tier classification
# ---------------------------------------------------------------------------

def classify_achievement(points: int, tiers: Dict) -> tuple:
    """Classify an achievement by point value into a reward tier.

    Returns (tier_name, rtc_amount) or (None, 0) if below minimum.
    """
    # Check tiers from highest to lowest
    tier_order = ["legendary", "ultra_rare", "rare", "uncommon", "common"]
    for tier_name in tier_order:
        tier = tiers.get(tier_name)
        if tier is None:
            continue
        if isinstance(tier, dict) and points >= tier.get("min_points", 0):
            return tier_name, tier.get("rtc", 0)

    return None, 0.0


# ---------------------------------------------------------------------------
# RetroAchievements API
# ---------------------------------------------------------------------------

class RetroAchievementsClient:
    """Thin wrapper around the RetroAchievements.org web API."""

    def __init__(self, api_url: str, username: str, api_key: str):
        self.api_url = api_url.rstrip("/")
        self.username = username
        self.api_key = api_key
        self.session = requests.Session()
        self.session.headers["User-Agent"] = "sophia-edge-node/1.0"

    def _get(self, endpoint: str, params: Dict = None) -> Any:
        """Make authenticated GET request."""
        params = params or {}
        params["z"] = self.username
        params["y"] = self.api_key
        url = f"{self.api_url}/{endpoint}"

        try:
            resp = self.session.get(url, params=params, timeout=15)
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as e:
            log.error("RetroAchievements API error: %s", e)
            return None

    def get_recent_achievements(self, minutes: int = 60) -> Optional[List[Dict]]:
        """Fetch user's recently unlocked achievements.

        GET /API_GetUserRecentAchievements.php?z={}&y={}&u={}&m={}
        """
        data = self._get(
            "API_GetUserRecentAchievements.php",
            {"u": self.username, "m": minutes},
        )
        if isinstance(data, list):
            return data
        return None

    def get_game_progress(self, game_id: int) -> Optional[Dict]:
        """Fetch game info and user progress for mastery check.

        GET /API_GetGameInfoAndUserProgress.php?z={}&y={}&u={}&g={}
        """
        return self._get(
            "API_GetGameInfoAndUserProgress.php",
            {"u": self.username, "g": game_id},
        )


# ---------------------------------------------------------------------------
# RTC reward submission
# ---------------------------------------------------------------------------

def submit_achievement_reward(
    config: Dict,
    achievement: Dict,
    tier_name: str,
    rtc_amount: float,
    is_hardcore: bool,
) -> bool:
    """Submit an achievement reward claim to the RustChain node.

    Posts to /api/gaming/achievement on the configured node.
    Falls back to local storage if the endpoint is unavailable.
    """
    node_url = config["rustchain"]["node_url"].rstrip("/")
    verify_ssl = config["rustchain"].get("verify_ssl", False)
    wallet_id = os.environ.get("SOPHIA_WALLET", config.get("node_id", "sophia-edge-rpi"))

    payload = {
        "miner": wallet_id,
        "source": "retroachievements",
        "achievement_id": str(achievement.get("AchievementID", achievement.get("ID", ""))),
        "game_id": str(achievement.get("GameID", "")),
        "game_title": achievement.get("GameTitle", ""),
        "achievement_title": achievement.get("Title", ""),
        "points": achievement.get("Points", 0),
        "tier": tier_name,
        "rtc_amount": rtc_amount,
        "hardcore": is_hardcore,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    url = f"{node_url}/api/gaming/achievement"
    try:
        resp = requests.post(url, json=payload, verify=verify_ssl, timeout=15)
        if resp.status_code == 200:
            log.info("  Reward submitted to node: %.5f RTC", rtc_amount)
            return True
        else:
            log.warning("  Node rejected reward (HTTP %d): %s", resp.status_code, resp.text[:200])
    except requests.RequestException as e:
        log.warning("  Could not reach node for reward submission: %s", e)

    # Store locally for later batch submission
    pending_path = STATE_DIR / "pending_rewards.jsonl"
    with open(pending_path, "a") as f:
        f.write(json.dumps(payload) + "\n")
    log.info("  Stored reward locally for batch submission (%.5f RTC)", rtc_amount)
    return False


def submit_mastery_bonus(config: Dict, game_id: int, game_title: str, bonus_rtc: float) -> bool:
    """Submit a mastery bonus claim."""
    node_url = config["rustchain"]["node_url"].rstrip("/")
    verify_ssl = config["rustchain"].get("verify_ssl", False)
    wallet_id = os.environ.get("SOPHIA_WALLET", config.get("node_id", "sophia-edge-rpi"))

    payload = {
        "miner": wallet_id,
        "source": "retroachievements",
        "type": "mastery_bonus",
        "game_id": str(game_id),
        "game_title": game_title,
        "rtc_amount": bonus_rtc,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    url = f"{node_url}/api/gaming/achievement"
    try:
        resp = requests.post(url, json=payload, verify=verify_ssl, timeout=15)
        if resp.status_code == 200:
            log.info("  Mastery bonus submitted: %.5f RTC for %s", bonus_rtc, game_title)
            return True
    except requests.RequestException:
        pass

    pending_path = STATE_DIR / "pending_rewards.jsonl"
    with open(pending_path, "a") as f:
        f.write(json.dumps(payload) + "\n")
    log.info("  Mastery bonus stored locally: %.5f RTC for %s", bonus_rtc, game_title)
    return False


# ---------------------------------------------------------------------------
# Main polling loop
# ---------------------------------------------------------------------------

def process_achievements(config: Dict) -> None:
    """Single pass: fetch recent achievements, classify, submit rewards."""
    acfg = config.get("achievements", {})
    ra_cfg = acfg.get("retroachievements", {})
    tiers = acfg.get("reward_tiers", {})
    daily_cap = acfg.get("daily_cap_rtc", 0.05)
    hardcore_mult = acfg.get("hardcore_multiplier", 2.0)
    mastery_bonus = tiers.get("mastery_bonus", 0.01)

    username = os.environ.get("RA_USERNAME", ra_cfg.get("username", ""))
    api_key = os.environ.get("RA_API_KEY", ra_cfg.get("api_key", ""))

    if not username or not api_key:
        log.error("RetroAchievements credentials not configured. Set RA_USERNAME and RA_API_KEY.")
        return

    client = RetroAchievementsClient(
        api_url=ra_cfg.get("api_url", "https://retroachievements.org/API"),
        username=username,
        api_key=api_key,
    )

    # Check daily cap
    daily_spent = get_daily_spent()
    if daily_spent >= daily_cap:
        log.info("Daily cap reached (%.5f / %.5f RTC). Skipping.", daily_spent, daily_cap)
        return

    remaining = daily_cap - daily_spent

    # Fetch recent achievements (last 60 minutes)
    achievements = client.get_recent_achievements(minutes=60)
    if achievements is None:
        log.warning("Failed to fetch recent achievements")
        return

    if not achievements:
        log.info("No new achievements in the last 60 minutes")
        return

    reported = load_reported()
    reported_ids = set(str(a) for a in reported.get("achievements", []))
    mastered_games = set(str(g) for g in reported.get("mastered_games", []))
    new_reported = False
    games_to_check_mastery = set()

    for ach in achievements:
        ach_id = str(ach.get("AchievementID", ach.get("ID", "")))
        if not ach_id or ach_id in reported_ids:
            continue

        points = int(ach.get("Points", 0))
        is_hardcore = bool(ach.get("HardcoreMode", 0))
        game_id = ach.get("GameID", "")
        game_title = ach.get("GameTitle", "Unknown")

        tier_name, base_rtc = classify_achievement(points, tiers)
        if tier_name is None:
            log.info("  [%s] %s - %d pts - below minimum, skipping",
                     game_title, ach.get("Title", ""), points)
            reported_ids.add(ach_id)
            new_reported = True
            continue

        rtc_amount = base_rtc
        if is_hardcore:
            rtc_amount *= hardcore_mult

        # Enforce daily cap
        if rtc_amount > remaining:
            log.info("  Daily cap would be exceeded. Capping at %.5f RTC", remaining)
            rtc_amount = remaining

        if rtc_amount <= 0:
            log.info("  Daily cap reached. Stopping.")
            break

        mode_str = " [HARDCORE]" if is_hardcore else ""
        log.info("  [%s] %s - %d pts - %s%s - %.5f RTC",
                 game_title, ach.get("Title", ""), points, tier_name, mode_str, rtc_amount)

        submit_achievement_reward(config, ach, tier_name, rtc_amount, is_hardcore)
        add_daily_spent(rtc_amount)
        remaining -= rtc_amount

        reported_ids.add(ach_id)
        new_reported = True

        if game_id:
            games_to_check_mastery.add((int(game_id), game_title))

    # Check for game mastery (100% completion)
    for game_id, game_title in games_to_check_mastery:
        if str(game_id) in mastered_games:
            continue

        progress = client.get_game_progress(game_id)
        if progress is None:
            continue

        num_achievements = int(progress.get("NumAchievements", 0))
        num_awarded = int(progress.get("NumAwardedToUser", 0))

        if num_achievements > 0 and num_awarded >= num_achievements:
            log.info("  MASTERY! %s - all %d achievements unlocked!", game_title, num_achievements)
            if remaining >= mastery_bonus:
                submit_mastery_bonus(config, game_id, game_title, mastery_bonus)
                add_daily_spent(mastery_bonus)
                remaining -= mastery_bonus
            mastered_games.add(str(game_id))
            new_reported = True

    if new_reported:
        reported["achievements"] = list(reported_ids)
        reported["mastered_games"] = list(mastered_games)
        save_reported(reported)


def poll_loop(config: Dict) -> None:
    """Main polling loop."""
    interval = config.get("achievements", {}).get("poll_interval_seconds", 300)

    log.info("=== Sophia Achievement Bridge ===")
    log.info("Poll interval: %ds", interval)
    log.info("Daily cap: %.4f RTC", config.get("achievements", {}).get("daily_cap_rtc", 0.05))

    while True:
        try:
            process_achievements(config)
        except Exception:
            log.exception("Error in achievement processing")
        time.sleep(interval)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def load_config() -> Dict:
    """Load config from file."""
    cfg_path = Path(CONFIG_PATH)
    if cfg_path.exists():
        with open(cfg_path) as f:
            return json.load(f)
    else:
        log.error("Config not found at %s", cfg_path)
        sys.exit(1)


def main():
    config = load_config()
    if not config.get("achievements", {}).get("enabled", True):
        log.info("Achievements are disabled in config. Exiting.")
        sys.exit(0)
    try:
        poll_loop(config)
    except KeyboardInterrupt:
        log.info("Achievement bridge stopped by user.")


if __name__ == "__main__":
    main()
