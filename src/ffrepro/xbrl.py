from __future__ import annotations

import html
import re
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

_CONTEXT_RE = re.compile(
    r'<xbrli:context\b[^>]*\bid="(?P<id>[^"]+)"[^>]*>(?P<body>.*?)</xbrli:context>',
    re.IGNORECASE | re.DOTALL,
)
_FACT_RE = re.compile(
    r"<ix:nonfraction\b(?P<attrs>[^>]*)>(?P<body>.*?)</ix:nonfraction>",
    re.IGNORECASE | re.DOTALL,
)
_ATTR_RE = re.compile(r'(?P<name>[\w:-]+)="(?P<value>[^"]*)"', re.IGNORECASE)


@dataclass(frozen=True)
class Context:
    context_id: str
    start_date: str | None
    end_date: str | None
    instant: str | None
    members: tuple[str, ...]


@dataclass(frozen=True)
class Fact:
    concept: str
    context_id: str
    value: Decimal
    scale: int
    unit: str

    @property
    def usd_millions(self) -> Decimal:
        if self.unit.lower() != "usd":
            raise ValueError(f"Expected USD fact, got unit {self.unit!r}")
        return self.value * (Decimal(10) ** self.scale) / Decimal(1_000_000)


def _tag_text(body: str, local_name: str) -> str | None:
    match = re.search(
        rf"<[^>]*:?{re.escape(local_name)}[^>]*>(.*?)</[^>]*:?{re.escape(local_name)}>",
        body,
        re.IGNORECASE | re.DOTALL,
    )
    if not match:
        return None
    return html.unescape(re.sub(r"<[^>]+>", "", match.group(1))).strip()


def _parse_decimal(body: str, *, negative: bool) -> Decimal:
    text = html.unescape(re.sub(r"<[^>]+>", "", body))
    normalized = text.replace(",", "").replace("\xa0", " ").strip()
    normalized = re.sub(r"[^0-9.()\-]", "", normalized)
    if not normalized:
        raise ValueError(f"Could not parse numeric XBRL fact from {text!r}")
    paren_negative = normalized.startswith("(") and normalized.endswith(")")
    normalized = normalized.strip("()")
    value = Decimal(normalized)
    return -abs(value) if negative or paren_negative else value


class InlineXbrlDocument:
    def __init__(self, *, contexts: dict[str, Context], facts: list[Fact]) -> None:
        self.contexts = contexts
        self.facts = facts

    @classmethod
    def from_path(cls, path: Path) -> InlineXbrlDocument:
        return cls.from_text(path.read_text(encoding="utf-8", errors="replace"))

    @classmethod
    def from_text(cls, source: str) -> InlineXbrlDocument:
        contexts: dict[str, Context] = {}
        for match in _CONTEXT_RE.finditer(source):
            body = match.group("body")
            members = tuple(
                html.unescape(value).strip()
                for value in re.findall(
                    r"<xbrldi:explicitmember\b[^>]*>(.*?)</xbrldi:explicitmember>",
                    body,
                    re.IGNORECASE | re.DOTALL,
                )
            )
            context_id = match.group("id")
            contexts[context_id] = Context(
                context_id=context_id,
                start_date=_tag_text(body, "startDate"),
                end_date=_tag_text(body, "endDate"),
                instant=_tag_text(body, "instant"),
                members=members,
            )

        facts: list[Fact] = []
        for match in _FACT_RE.finditer(source):
            attrs = {
                item.group("name").lower(): html.unescape(item.group("value"))
                for item in _ATTR_RE.finditer(match.group("attrs"))
            }
            concept = attrs.get("name")
            context_id = attrs.get("contextref")
            if not concept or not context_id:
                continue
            visible_value = html.unescape(re.sub(r"<[^>]+>", "", match.group("body")))
            if not re.search(r"\d", visible_value):
                # Inline XBRL documents can contain nil/empty numeric facts.
                # They are not observations and must not abort unrelated facts.
                continue
            facts.append(
                Fact(
                    concept=concept,
                    context_id=context_id,
                    value=_parse_decimal(match.group("body"), negative=attrs.get("sign") == "-"),
                    scale=int(attrs.get("scale", "0")),
                    unit=attrs.get("unitref", ""),
                )
            )
        return cls(contexts=contexts, facts=facts)

    def usd_millions(
        self,
        *,
        concept: str,
        start_date: str,
        end_date: str,
        member_suffix: str | None,
    ) -> Decimal:
        values: set[Decimal] = set()
        for fact in self.facts:
            if fact.concept.lower() != concept.lower():
                continue
            context = self.contexts.get(fact.context_id)
            if not context:
                continue
            if (context.start_date, context.end_date) != (start_date, end_date):
                continue
            if member_suffix is None:
                if context.members:
                    continue
            elif not any(
                member.lower().endswith(member_suffix.lower()) for member in context.members
            ):
                continue
            values.add(fact.usd_millions)
        if not values:
            raise LookupError(
                f"No fact found for {concept}, {start_date}..{end_date}, member={member_suffix}"
            )
        if len(values) > 1:
            raise ValueError(
                f"Conflicting facts for {concept}, {start_date}..{end_date}, "
                f"member={member_suffix}: {sorted(values)}"
            )
        return values.pop()
