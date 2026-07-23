from dataclasses import dataclass


@dataclass
class Connector:
    word: str
    type: str
    category: str


@dataclass
class Token:
    text: str
    lemma: str
    pos: str
    dep: str
    head: str


@dataclass
class Proposition:
    text: str
    verb: str | None
