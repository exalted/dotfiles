#!/usr/bin/env -S uv run --quiet --no-project --script
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""Read-only check of which teammates are free to pair on Tuple right now.

Never calls, messages, joins or changes anything in Slack or Tuple.
"""

import argparse
import html
import json
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import StrEnum
from pathlib import Path
from typing import Any, cast

# Who is on the team is per-machine data, kept out of the public dotfiles repo this skill lives in.
CONFIG_DIR = Path.home() / ".config" / "dotfiles" / "pairing-candidates"
ROSTER_FILE = CONFIG_DIR / "roster.txt"
CHANNEL_FILE = CONFIG_DIR / "channel"
TACTICAL_FILE = CONFIG_DIR / "tactical.txt"
KEYCHAIN_SERVICE = "pairing-candidates-slack-token"
WORKDAY_START_HOUR = 9
WORKDAY_END_HOUR = 18
REQUIRED_SCOPES = "channels:read, channels:history, users:read, users:read.email, dnd:read"
# :pair: and :tuple-pear: are workspace aliases of :pear:; match every name in case Slack reports the alias.
PAIR_REACTIONS = frozenset({"tuple", "pear", "pair", "tuple-pear"})
MESSAGE_PREVIEW_LENGTH = 300
EXIT_SETUP_ERROR = 2
EXIT_TACTICAL_PAIRS_NEEDED = 3

type Json = dict[str, Any]


def status_pattern(*, words: tuple[str, ...], emojis: tuple[str, ...]) -> re.Pattern[str]:
    return re.compile(rf"\b({'|'.join(words)})\b|:({'|'.join(emojis)}):", re.IGNORECASE)


OUT_OF_OFFICE_STATUS = status_pattern(
    words=(
        "ooo",
        "out of (the )?office",
        "vacation",
        "holiday",
        "pto",
        "on leave",
        "parental leave",
        "sick",
        "day off",
        "off today",
    ),
    emojis=("palm_tree", "face_with_thermometer", "airplane", "beach_with_umbrella", "desert_island"),
)
OCCUPIED_STATUS = status_pattern(
    words=(
        "huddle",
        "meeting",
        "call",
        "focus(ing)?",
        "lunch",
        "commuting",
        "busy",
        "presenting",
        "interview",
        "heads[- ]down",
        "dnd",
        "do not disturb",
        "break",
        "brb",
    ),
    emojis=(
        "spiral_calendar_pad",
        "calendar",
        "headphones",
        "no_entry",
        "red_circle",
        "knife_fork_plate",
        "hamburger",
        "sandwich",
        "car",
        "bus",
        "train",
        "tomato",
    ),
)


class SetupError(Exception):
    pass


class TacticalPairsNeeded(Exception):
    pass


TUPLE_ONLINE_STATUSES = frozenset({"online", "available"})


class Tier(StrEnum):
    CANDIDATE = "Can pair now"
    MAYBE = "Maybe"
    NOT_AVAILABLE = "Not available"


class Blocker(StrEnum):
    """Why a teammate cannot pair; the declaration order is the display order."""

    IN_CALL = "In a Tuple call"
    OUT_OF_OFFICE = "Out of office"
    OFFLINE = "Tuple offline"
    NOT_ON_TUPLE = "Not on Tuple"


@dataclass(frozen=True)
class SlackMember:
    user_id: str
    handle: str
    name: str
    email: str
    status: str
    utc_offset: timedelta


class RosterGroup(StrEnum):
    PAIRING = "pairing"
    ON_REQUEST = "on request"


@dataclass(frozen=True)
class RosterEntry:
    handle: str
    role: str
    group: RosterGroup


@dataclass(frozen=True)
class TupleContact:
    contact_id: int
    email: str
    name: str
    status: str


@dataclass(frozen=True)
class Verdict:
    member: SlackMember
    roster_entry: RosterEntry
    blocker: Blocker | None
    soft_signals: tuple[str, ...]
    call_group: tuple[str, ...] = ()  # sorted names of everyone in the member's Tuple call, the member included

    @property
    def tier(self) -> Tier:
        if self.blocker is not None:
            return Tier.NOT_AVAILABLE
        return Tier.MAYBE if self.soft_signals else Tier.CANDIDATE


@dataclass(frozen=True)
class UnansweredMessage:
    member: SlackMember
    posted_at: datetime
    text: str


@dataclass(frozen=True)
class PairingCheck:
    verdicts: tuple[Verdict, ...]
    dnd_known: bool
    unanswered_messages: tuple[UnansweredMessage, ...]
    history_known: bool
    missing_handles: tuple[str, ...]
    channel_name: str
    own_handle: str
    tactical_pairs: tuple[tuple[str, str], ...]

    @property
    def tactical_partner(self) -> str | None:
        return next(
            (b if a == self.own_handle else a for a, b in self.tactical_pairs if self.own_handle in (a, b)), None
        )


class SlackClient:
    def __init__(self, token: str) -> None:
        self._token = token

    def call(self, method: str, **params: str) -> Json:
        url = f"https://slack.com/api/{method}?{urllib.parse.urlencode(params)}"
        request = urllib.request.Request(url, headers={"Authorization": f"Bearer {self._token}"})
        for _ in range(3):
            try:
                with urllib.request.urlopen(request, timeout=15) as response:
                    body = cast(Json, json.load(response))
            except urllib.error.HTTPError as error:
                if error.code == 429:
                    time.sleep(int(error.headers.get("Retry-After", "1")))
                    continue
                raise
            if body.get("ok"):
                return body
            if body.get("error") in ("missing_scope", "invalid_auth", "not_authed", "token_revoked", "token_expired"):
                needed = body.get("needed", "?")
                raise SetupError(
                    f"Slack {method} failed: {body['error']} (needed: {needed}). Token user scopes: {REQUIRED_SCOPES}."
                )
            raise RuntimeError(f"Slack {method} failed: {body.get('error')}")
        raise RuntimeError(f"Slack {method} stayed rate-limited after 3 attempts")


def read_slack_token() -> str:
    result = subprocess.run(
        ["/usr/bin/security", "find-generic-password", "-s", KEYCHAIN_SERVICE, "-w"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0 or not result.stdout.strip():
        raise SetupError(f"No Slack token in Keychain service '{KEYCHAIN_SERVICE}'. See 'One-time setup' in SKILL.md.")
    return result.stdout.strip()


def run_tuple(*arguments: str) -> Any:
    try:
        result = subprocess.run(["tuple", *arguments, "--format", "json"], capture_output=True, text=True)
    except FileNotFoundError as error:
        raise SetupError("The `tuple` CLI is not installed or not on PATH.") from error
    if result.returncode != 0:
        raise SetupError(f"`tuple {' '.join(arguments)}` failed (is the Tuple app running?): {result.stderr.strip()}")
    return json.loads(result.stdout)


def read_channel_id() -> str:
    channel_id = CHANNEL_FILE.read_text().strip() if CHANNEL_FILE.exists() else ""
    if not channel_id:
        raise SetupError(f"Missing team channel ID in {CHANNEL_FILE}. See 'One-time setup' in SKILL.md.")
    return channel_id


def read_roster() -> dict[str, RosterEntry]:
    if not ROSTER_FILE.exists():
        raise SetupError(f"Missing roster file {ROSTER_FILE}.")
    roster: dict[str, RosterEntry] = {}
    group: RosterGroup | None = None
    for number, raw_line in enumerate(ROSTER_FILE.read_text().splitlines(), start=1):
        line = raw_line.split("#", 1)[0].strip()
        if not line:
            continue
        if line.startswith("[") and line.endswith("]"):
            try:
                group = RosterGroup(line[1:-1].strip().lower())
            except ValueError as error:
                raise SetupError(f"{ROSTER_FILE.name}:{number}: unknown section {line}") from error
            continue
        if group is None:
            raise SetupError(f"{ROSTER_FILE.name}:{number}: '{line}' is not under a [pairing] or [on request] section")
        handle, *role = line.split(maxsplit=1)
        handle = handle.lstrip("@").lower()
        roster[handle] = RosterEntry(handle=handle, role=role[0] if role else "", group=group)
    return roster


def iso_week(now: datetime) -> str:
    year, week, _ = now.isocalendar()
    return f"{year}-W{week:02d}"


def to_handle(text: str) -> str:
    return text.strip().lstrip("@").lower()


def read_tactical_pairs(*, now: datetime) -> tuple[tuple[str, str], ...] | None:
    """Return this week's tactical pairs, or None when they were not recorded for the current ISO week."""
    if not TACTICAL_FILE.exists():
        return None
    week = ""
    pairs: list[tuple[str, str]] = []
    for number, raw_line in enumerate(TACTICAL_FILE.read_text().splitlines(), start=1):
        line = raw_line.split("#", 1)[0].strip()
        if not line:
            continue
        if line.startswith("week "):
            week = line.removeprefix("week ").strip()
            continue
        handles = [to_handle(part) for part in line.split("+")]
        if len(handles) != 2 or not all(handles):
            raise SetupError(f"{TACTICAL_FILE.name}:{number}: '{line}' is not a 'handle + handle' pair")
        pairs.append((handles[0], handles[1]))
    return tuple(pairs) if week == iso_week(now) else None


def pairing_handles_hint(*, roster: dict[str, RosterEntry], own_handle: str) -> str:
    handles = [f"{h} ({e.role})" if e.role else h for h, e in roster.items() if e.group is RosterGroup.PAIRING]
    return f"[pairing] handles: {', '.join(handles)}; your own handle: {own_handle}"


def record_tactical_pairs(*, arguments: list[str], own_handle: str, now: datetime) -> None:
    roster = read_roster()
    allowed = {h for h, e in roster.items() if e.group is RosterGroup.PAIRING} | {own_handle}
    hint = pairing_handles_hint(roster=roster, own_handle=own_handle)
    pairs: list[tuple[str, str]] = []
    if arguments != ["none"]:
        for argument in arguments:
            handles = [to_handle(part) for part in argument.split("+")]
            if len(handles) != 2 or not all(handles):
                raise TacticalPairsNeeded(f"'{argument}' is not a 'handle+handle' pair. {hint}")
            if unknown := [h for h in handles if h not in allowed]:
                raise TacticalPairsNeeded(f"not a [pairing] handle: {', '.join(unknown)}. {hint}")
            pairs.append((handles[0], handles[1]))
    seen = [h for pair in pairs for h in pair]
    if len(seen) != len(set(seen)):
        raise TacticalPairsNeeded(f"a handle is in more than one pair: {' '.join(arguments)}. {hint}")
    lines = ["# Written by check.py --tactical; stale once the ISO week changes.", f"week {iso_week(now)}"]
    TACTICAL_FILE.write_text("\n".join([*lines, *(f"{a} + {b}" for a, b in pairs)]) + "\n")


def list_channel_member_ids(*, slack: SlackClient, channel_id: str) -> list[str]:
    member_ids: list[str] = []
    cursor = ""
    while True:
        page = slack.call("conversations.members", channel=channel_id, limit="200", cursor=cursor)
        member_ids.extend(page["members"])
        cursor = page.get("response_metadata", {}).get("next_cursor", "")
        if not cursor:
            return member_ids


def current_status(profile: Json) -> str:
    expiration = profile.get("status_expiration") or 0
    if expiration and expiration < time.time():
        return ""
    return " ".join(part for part in (profile.get("status_emoji", ""), profile.get("status_text", "")) if part)


def to_member(user: Json) -> SlackMember | None:
    if user.get("deleted") or user.get("is_bot") or user.get("id") == "USLACKBOT":
        return None
    profile = user.get("profile", {})
    return SlackMember(
        user_id=user["id"],
        handle=user["name"],
        name=profile.get("real_name") or user.get("real_name") or user["name"],
        email=(profile.get("email") or "").lower(),
        status=current_status(profile),
        utc_offset=timedelta(seconds=user.get("tz_offset", 0)),
    )


def read_dnd_user_ids(*, slack: SlackClient, user_ids: list[str]) -> frozenset[str] | None:
    """Return who is in scheduled DND now, or None when the token lacks dnd:read.

    Slack does not expose another user's manual snooze, only the schedule.
    """
    now = time.time()
    in_dnd: set[str] = set()
    try:
        for start in range(0, len(user_ids), 50):
            batch = user_ids[start : start + 50]
            response = slack.call("dnd.teamInfo", users=",".join(batch))
            for user_id, dnd in response.get("users", {}).items():
                if dnd.get("dnd_enabled") and dnd.get("next_dnd_start_ts", 0) <= now < dnd.get("next_dnd_end_ts", 0):
                    in_dnd.add(user_id)
    except SetupError:
        return None
    return frozenset(in_dnd)


def read_messages_since(*, slack: SlackClient, channel_id: str, oldest: datetime) -> list[Json] | None:
    """Return the channel's messages since `oldest`, or None when the token lacks channels:history."""
    messages: list[Json] = []
    cursor = ""
    try:
        while True:
            page = slack.call(
                "conversations.history",
                channel=channel_id,
                oldest=f"{oldest.timestamp():.6f}",
                limit="200",
                cursor=cursor,
            )
            messages.extend(page["messages"])
            cursor = page.get("response_metadata", {}).get("next_cursor", "")
            if not cursor:
                return messages
    except SetupError:
        return None


def start_of_their_day(*, member: SlackMember, now: datetime) -> datetime:
    return now.astimezone(timezone(member.utc_offset)).replace(hour=0, minute=0, second=0, microsecond=0)


def is_answered(*, message: Json, channel_messages: list[Json]) -> bool:
    asker = message["user"]
    if any(user != asker for user in message.get("reply_users", [])):
        return True
    for reaction in message.get("reactions", []):
        is_pair_reaction = reaction["name"].split("::")[0] in PAIR_REACTIONS
        if is_pair_reaction and any(user != asker for user in reaction.get("users", [])):
            return True
    mention = f"<@{asker}>"
    return any(
        float(later["ts"]) > float(message["ts"]) and later.get("user") != asker and mention in later.get("text", "")
        for later in channel_messages
    )


SLACK_MARKUP = re.compile(r"<([^>|]+)(?:\|([^>]+))?>")


def plain_text(*, text: str, handles: dict[str, str]) -> str:
    def replace(match: re.Match[str]) -> str:
        target, label = match.groups()
        if target.startswith("@"):
            return f"@{handles.get(target[1:], label or 'someone')}"
        if target.startswith("!"):
            return f"@{label or target[1:].split('^')[0]}"
        if target.startswith("#"):
            return f"#{label or target[1:]}"
        return label or target

    flattened = " ".join(html.unescape(SLACK_MARKUP.sub(replace, text)).split())
    if len(flattened) <= MESSAGE_PREVIEW_LENGTH:
        return flattened
    return flattened[: MESSAGE_PREVIEW_LENGTH - 1] + "…"


def find_unanswered_messages(
    *, channel_messages: list[Json], members: list[SlackMember], handles: dict[str, str], now: datetime
) -> tuple[UnansweredMessage, ...]:
    members_by_id = {m.user_id: m for m in members}
    unanswered: list[UnansweredMessage] = []
    for message in channel_messages:
        member = members_by_id.get(message.get("user", ""))
        is_top_level = "subtype" not in message and message.get("thread_ts", message["ts"]) == message["ts"]
        if member is None or not is_top_level:
            continue
        posted_at = datetime.fromtimestamp(float(message["ts"]), tz=now.tzinfo)
        if posted_at < start_of_their_day(member=member, now=now):
            continue
        if is_answered(message=message, channel_messages=channel_messages):
            continue
        unanswered.append(
            UnansweredMessage(
                member=member,
                posted_at=posted_at,
                text=plain_text(text=message.get("text", ""), handles=handles),
            )
        )
    return tuple(sorted(unanswered, key=lambda m: m.posted_at))


def read_tuple_contacts() -> list[TupleContact]:
    rows = cast(list[Json], run_tuple("contacts", "list"))
    return [
        TupleContact(
            contact_id=int(row["id"]),
            email=str(row["email"]).lower(),
            name=str(row["full_name"]),
            status=str(row["status"]),
        )
        for row in rows
    ]


def read_call_participant_ids(contact: TupleContact) -> frozenset[int]:
    details = cast(Json, run_tuple("contacts", "show", contact.email))
    call = cast(Json, details.get("call") or {})
    return frozenset(cast(list[int], call.get("participant_ids", []))) | {contact.contact_id}


def find_blocker(*, member: SlackMember, contact: TupleContact | None) -> Blocker | None:
    if contact is not None and contact.status == "busy":
        return Blocker.IN_CALL
    if member.status and OUT_OF_OFFICE_STATUS.search(member.status):
        return Blocker.OUT_OF_OFFICE
    if contact is None:
        return Blocker.NOT_ON_TUPLE
    if contact.status not in TUPLE_ONLINE_STATUSES:
        return Blocker.OFFLINE
    return None


def find_soft_signals(*, member: SlackMember, presence: str, in_dnd: bool, now: datetime) -> tuple[str, ...]:
    signals: list[str] = []
    if member.status and OCCUPIED_STATUS.search(member.status):
        signals.append(f'status "{member.status}"')
    if presence != "active":
        signals.append("Slack away")
    if in_dnd:
        signals.append("Slack DND")
    if not WORKDAY_START_HOUR <= now.astimezone(timezone(member.utc_offset)).hour < WORKDAY_END_HOUR:
        signals.append("outside working hours")
    return tuple(signals)


def describe_reachable(*, verdict: Verdict, checked_at: datetime) -> str:
    member = verdict.member
    details = list(verdict.soft_signals)
    if member.status and not OCCUPIED_STATUS.search(member.status):
        details.append(f'status "{member.status}"')
    if member.utc_offset != checked_at.utcoffset():
        details.append(f"{checked_at.astimezone(timezone(member.utc_offset)):%H:%M} their time")
    return " · ".join([f"{member.name} (@{member.handle})", *details])


def describe_unavailable(verdicts: list[Verdict]) -> list[str]:
    lines: list[str] = []
    for blocker in Blocker:
        blocked = [v for v in verdicts if v.blocker is blocker]
        if not blocked:
            continue
        if blocker is Blocker.IN_CALL:
            names = " · ".join(" + ".join(group) for group in sorted({v.call_group for v in blocked}))
        else:
            names = ", ".join(v.member.name for v in blocked)
        lines.append(f"  {blocker}: {names}")
    return lines


def describe_partner(*, verdict: Verdict, checked_at: datetime) -> str:
    member = verdict.member
    if verdict.blocker is Blocker.IN_CALL:
        details = f"{member.name} (@{member.handle}) · {Blocker.IN_CALL}: {' + '.join(verdict.call_group)}"
    elif verdict.blocker is not None:
        details = f"{member.name} (@{member.handle}) · {verdict.blocker}"
    else:
        details = describe_reachable(verdict=verdict, checked_at=checked_at)
    return f"Your tactical partner ({verdict.tier}): {details}"


def describe_tactical_pairs(*, check: PairingCheck, names: dict[str, str]) -> str:
    def name(handle: str) -> str:
        return "you" if handle == check.own_handle else names.get(handle, f"@{handle}")

    return f"Tactical this week: {' · '.join(f'{name(a)} + {name(b)}' for a, b in check.tactical_pairs)}"


def describe_around(verdict: Verdict) -> str:
    role = verdict.roster_entry.role
    return f"{verdict.member.name} ({role})" if role else verdict.member.name


def describe_age(*, posted_at: datetime, checked_at: datetime) -> str:
    minutes = max(0, int((checked_at - posted_at).total_seconds() // 60))
    hours, minutes = divmod(minutes, 60)
    return f"{hours} h {minutes} min ago" if hours else f"{minutes} min ago"


def describe_unanswered(*, message: UnansweredMessage, checked_at: datetime) -> str:
    age = describe_age(posted_at=message.posted_at, checked_at=checked_at)
    return f"  - {message.member.name} · {message.posted_at:%H:%M} ({age}): {message.text}"


def render(*, check: PairingCheck, checked_at: datetime) -> str:
    verdicts = sorted(check.verdicts, key=lambda v: v.member.name.lower())
    tactical = {handle for pair in check.tactical_pairs for handle in pair}
    partner = check.tactical_partner
    pairing = [
        v for v in verdicts if v.roster_entry.group is RosterGroup.PAIRING and v.member.handle.lower() not in tactical
    ]
    by_tier = {tier: [v for v in pairing if v.tier is tier] for tier in Tier}
    around = [v for v in verdicts if v.roster_entry.group is RosterGroup.ON_REQUEST and v.tier is Tier.CANDIDATE]
    candidates = by_tier[Tier.CANDIDATE]
    lines = [f"Pairing check at {checked_at:%H:%M}: {len(candidates)} of {len(pairing)} teammates can pair now"]
    if partner is not None:
        partner_verdict = next((v for v in verdicts if v.member.handle.lower() == partner), None)
        lines += [
            "",
            describe_partner(verdict=partner_verdict, checked_at=checked_at)
            if partner_verdict
            else f"Your tactical partner: @{partner}, not found in #{check.channel_name}",
        ]
    for tier in (Tier.CANDIDATE, Tier.MAYBE):
        if by_tier[tier] or tier is Tier.CANDIDATE:
            lines += ["", f"{tier} ({len(by_tier[tier])})"]
            lines += [f"  - {describe_reachable(verdict=v, checked_at=checked_at)}" for v in by_tier[tier]] or [
                "  (none)"
            ]
    if unavailable := by_tier[Tier.NOT_AVAILABLE]:
        lines += ["", f"{Tier.NOT_AVAILABLE} ({len(unavailable)})", *describe_unavailable(unavailable)]
    if check.tactical_pairs:
        names = {v.member.handle.lower(): v.member.name for v in verdicts}
        lines += ["", describe_tactical_pairs(check=check, names=names)]
    if around:
        lines += ["", f"Also around (on request): {', '.join(describe_around(v) for v in around)}"]
    if check.missing_handles:
        missing = ", ".join(f"@{handle}" for handle in check.missing_handles)
        lines += ["", f"Not found in #{check.channel_name}, check {ROSTER_FILE}: {missing}"]
    if not check.dnd_known:
        lines += ["", "DND not checked: the Slack token lacks the dnd:read scope."]
    # Tactical people already have a partner, so only your own partner's requests concern you.
    unanswered = [m for m in check.unanswered_messages if m.member.handle.lower() not in tactical - {partner}]
    if not check.history_known:
        lines += ["", "Pair requests not checked: the Slack token lacks the channels:history scope."]
    elif unanswered:
        lines += ["", f"Unanswered messages to judge ({len(unanswered)}), today in #{check.channel_name}"]
        lines += [describe_unanswered(message=m, checked_at=checked_at) for m in unanswered]
    return "\n".join(lines)


def check_team(*, slack: SlackClient, now: datetime) -> PairingCheck:
    roster = read_roster()
    channel_id = read_channel_id()
    contacts = read_tuple_contacts()
    own_identity = slack.call("auth.test")
    own_user_id = cast(str, own_identity["user_id"])
    own_handle = to_handle(cast(str, own_identity["user"]))
    tactical_pairs = read_tactical_pairs(now=now)
    if tactical_pairs is None:
        raise TacticalPairsNeeded(
            f"no tactical pairs recorded for week {iso_week(now)}. {pairing_handles_hint(roster=roster, own_handle=own_handle)}"
        )
    channel_name = cast(str, slack.call("conversations.info", channel=channel_id)["channel"]["name"])
    member_ids = [i for i in list_channel_member_ids(slack=slack, channel_id=channel_id) if i != own_user_id]

    def fetch_user(user_id: str) -> Json:
        return cast(Json, slack.call("users.info", user=user_id)["user"])

    def fetch_presence(member: SlackMember) -> str:
        return cast(str, slack.call("users.getPresence", user=member.user_id)["presence"])

    with ThreadPoolExecutor(max_workers=8) as pool:
        users = list(pool.map(fetch_user, member_ids))
        members = [m for m in (to_member(u) for u in users) if m is not None and m.handle.lower() in roster]
        presences = list(pool.map(fetch_presence, members))
    dnd_user_ids = read_dnd_user_ids(slack=slack, user_ids=[m.user_id for m in members])
    channel_messages = (
        read_messages_since(
            slack=slack,
            channel_id=channel_id,
            oldest=min(start_of_their_day(member=m, now=now) for m in members),
        )
        if members
        else []
    )
    handles = {cast(str, u["id"]): cast(str, u["name"]) for u in users}
    found_handles = {m.handle.lower() for m in members} | {own_handle}
    missing_handles = tuple(sorted(set(roster) - found_handles))

    contacts_by_email = {c.email: c for c in contacts}
    # Prefer Slack names so both sides of a pair render the same call group.
    display_names = {c.contact_id: c.name for c in contacts} | {
        contacts_by_email[m.email].contact_id: m.name for m in members if m.email in contacts_by_email
    }
    verdicts: list[Verdict] = []
    for member, presence in zip(members, presences, strict=True):
        contact = contacts_by_email.get(member.email)
        blocker = find_blocker(member=member, contact=contact)
        call_group: tuple[str, ...] = ()
        if contact is not None and blocker is Blocker.IN_CALL:
            call_group = tuple(sorted(display_names.get(i, "someone") for i in read_call_participant_ids(contact)))
        in_dnd = dnd_user_ids is not None and member.user_id in dnd_user_ids
        verdicts.append(
            Verdict(
                member=member,
                roster_entry=roster[member.handle.lower()],
                blocker=blocker,
                soft_signals=find_soft_signals(member=member, presence=presence, in_dnd=in_dnd, now=now),
                call_group=call_group,
            )
        )
    return PairingCheck(
        verdicts=tuple(verdicts),
        dnd_known=dnd_user_ids is not None,
        unanswered_messages=find_unanswered_messages(
            channel_messages=channel_messages or [], members=members, handles=handles, now=now
        ),
        history_known=channel_messages is not None,
        missing_handles=missing_handles,
        channel_name=channel_name,
        own_handle=own_handle,
        tactical_pairs=tactical_pairs,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--tactical",
        nargs="+",
        metavar="HANDLE+HANDLE",
        help="record this ISO week's tactical pairs (or 'none'), then run the check",
    )
    arguments = parser.parse_args()
    now = datetime.now().astimezone()
    try:
        slack = SlackClient(read_slack_token())
        if arguments.tactical:
            own_handle = to_handle(cast(str, slack.call("auth.test")["user"]))
            record_tactical_pairs(arguments=arguments.tactical, own_handle=own_handle, now=now)
        check = check_team(slack=slack, now=now)
    except SetupError as error:
        print(f"SETUP ERROR: {error}", file=sys.stderr)
        return EXIT_SETUP_ERROR
    except TacticalPairsNeeded as error:
        print(f"TACTICAL PAIRS NEEDED: {error}", file=sys.stderr)
        return EXIT_TACTICAL_PAIRS_NEEDED
    except (RuntimeError, urllib.error.URLError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(render(check=check, checked_at=now))
    return 0


if __name__ == "__main__":
    sys.exit(main())
