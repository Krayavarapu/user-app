"""Deterministic free-text -> equipment ID matching.

The legacy request field ``equipment`` is free text ("Dumbbells, resistance bands, bench").
The plan pre-filter needs exact equipment IDs, and equipment is a safety-relevant hard
constraint, so matching is deliberately conservative:

* Only exact alias phrases from the catalog match (plus simple plurals). Nothing is guessed.
* Unmatched words are *reported*, never used to unlock exercises.
* Anything following a negation word ("no", "without", ...) in the same clause is treated as
  *not owned*, so "no barbell" can never unlock a barbell. This errs on the side of
  under-matching ("no barbell or rack, just dumbbells" is split by the comma and works,
  but "no barbell and dumbbells" drops the dumbbells).
* An alias claimed by two different equipment items is ambiguous and unlocks neither.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Dict, Iterable, List, Mapping, Optional, Sequence, Set, Tuple

logger = logging.getLogger(__name__)

_CLAUSE_SPLIT = re.compile(r"[,;.\n|/]+|\bbut\b|\bhowever\b|\balthough\b")
_NON_ALNUM = re.compile(r"[^a-z0-9]+")

NEGATION_WORDS = frozenset(
    {"no", "not", "without", "dont", "cant", "never", "lack", "lacking", "except", "excluding", "minus"}
)

# Words that carry no equipment information. Skipped silently (not reported as unmatched).
STOPWORDS = frozenset(
    {
        "a", "an", "the", "and", "or", "with", "some", "my", "i", "ive", "have", "has", "got", "only",
        "just", "also", "plus", "at", "of", "for", "to", "use", "using", "can", "access", "available",
        "equipment", "gear", "any", "all", "few", "set", "sets", "pair", "pairs", "basic", "are", "is",
        "am", "me", "we", "our", "that", "this", "it", "as", "well", "other", "stuff", "things",
    }
)

# Phrases that mean "no equipment". They match to nothing, which resolves to bodyweight-only.
NOOP_PHRASES = frozenset({"bodyweight", "body weight", "calisthenics", "none", "nothing"})

_MAX_PHRASE_TOKENS = 4


def normalize_text(text: str) -> str:
    """Lowercase, drop apostrophes, and collapse everything non-alphanumeric to single spaces."""
    lowered = (text or "").lower().replace("'", "").replace("\u2019", "")
    return _NON_ALNUM.sub(" ", lowered).strip()


@dataclass(frozen=True)
class EquipmentAliasSource:
    equipment_id: str
    name: str
    aliases: Sequence[str] = ()


@dataclass(frozen=True)
class EquipmentMatch:
    equipment_ids: Tuple[str, ...]
    unmatched_terms: Tuple[str, ...] = ()
    negated_ids: Tuple[str, ...] = ()


def _phrases_for(source: EquipmentAliasSource) -> Set[str]:
    phrases = {normalize_text(source.equipment_id.replace("_", " ")), normalize_text(source.name)}
    phrases.update(normalize_text(alias) for alias in source.aliases)
    phrases.discard("")
    return phrases


def find_alias_collisions(sources: Iterable[EquipmentAliasSource]) -> Dict[str, Set[str]]:
    """Return {normalized phrase: {equipment_ids}} for phrases claimed by more than one item."""
    owners: Dict[str, Set[str]] = {}
    for source in sources:
        for phrase in _phrases_for(source):
            owners.setdefault(phrase, set()).add(source.equipment_id)
    return {phrase: ids for phrase, ids in owners.items() if len(ids) > 1}


def _singular_variants(token: str) -> List[str]:
    variants = []
    if token.endswith("es") and len(token) > 3:
        variants.append(token[:-2])
    if token.endswith("s") and len(token) > 2:
        variants.append(token[:-1])
    return variants


class EquipmentAliasIndex:
    """Immutable phrase -> equipment_id lookup built from the active catalog."""

    def __init__(self, sources: Iterable[EquipmentAliasSource]) -> None:
        sources = list(sources)
        collisions = find_alias_collisions(sources)
        for phrase, ids in sorted(collisions.items()):
            logger.warning(
                "equipment_aliases: ambiguous alias dropped phrase=%r equipment_ids=%s", phrase, sorted(ids)
            )

        phrase_to_id: Dict[str, Optional[str]] = {}
        for source in sources:
            for phrase in _phrases_for(source):
                if phrase not in collisions:
                    phrase_to_id[phrase] = source.equipment_id
        for phrase in NOOP_PHRASES:
            phrase_to_id.setdefault(phrase, None)

        self._phrase_to_id: Mapping[str, Optional[str]] = phrase_to_id
        self._max_tokens = min(
            _MAX_PHRASE_TOKENS, max((len(phrase.split()) for phrase in phrase_to_id), default=1)
        )

    def _lookup(self, tokens: Sequence[str]) -> Tuple[bool, Optional[str]]:
        """Return (found, equipment_id). equipment_id is None for no-op phrases."""
        phrase = " ".join(tokens)
        if phrase in self._phrase_to_id:
            return True, self._phrase_to_id[phrase]
        for variant in _singular_variants(tokens[-1]):
            candidate = " ".join([*tokens[:-1], variant])
            if candidate in self._phrase_to_id:
                return True, self._phrase_to_id[candidate]
        return False, None

    def match(self, text: Optional[str]) -> EquipmentMatch:
        matched: List[str] = []
        negated: List[str] = []
        unmatched: List[str] = []

        for clause in _CLAUSE_SPLIT.split((text or "").lower()):
            tokens = normalize_text(clause).split()
            is_negated = False
            index = 0
            while index < len(tokens):
                token = tokens[index]
                if token in NEGATION_WORDS:
                    is_negated = True
                    index += 1
                    continue

                found = False
                for size in range(min(self._max_tokens, len(tokens) - index), 0, -1):
                    hit, equipment_id = self._lookup(tokens[index : index + size])
                    if hit:
                        found = True
                        if equipment_id is not None:
                            (negated if is_negated else matched).append(equipment_id)
                        index += size
                        break
                if found:
                    continue

                if token not in STOPWORDS:
                    unmatched.append(token)
                index += 1

        # An item can't be both owned and not owned: if it's negated anywhere, it stays out.
        negated_set = set(negated)
        return EquipmentMatch(
            equipment_ids=tuple(item for item in _dedupe(matched) if item not in negated_set),
            unmatched_terms=_dedupe(unmatched),
            negated_ids=_dedupe(negated),
        )


def _dedupe(items: Iterable[str]) -> Tuple[str, ...]:
    seen: Set[str] = set()
    ordered: List[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            ordered.append(item)
    return tuple(ordered)
