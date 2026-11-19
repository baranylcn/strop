"""Prompt template types."""

import hashlib
import json
from dataclasses import dataclass

from strop.llm.types import Role
from strop.prompts.template import find_variables, strip_markers


@dataclass(frozen=True, slots=True)
class PromptMessage:
    role: Role
    content: str


@dataclass(frozen=True, slots=True)
class PromptTemplate:
    """Chat messages plus the roles whose messages the optimizer may rewrite."""

    messages: tuple[PromptMessage, ...]
    optimize: frozenset[Role]

    @property
    def variables(self) -> tuple[str, ...]:
        """Variable names used anywhere in the template, in order of first use."""
        names: dict[str, None] = {}
        for message in self.messages:
            names.update(dict.fromkeys(find_variables(message.content)))
        return tuple(names)

    def is_editable(self, message: PromptMessage) -> bool:
        return message.role in self.optimize

    def without_markers(self) -> "PromptTemplate":
        """The same template with every ``<strop:fixed>`` marker removed and its text kept."""
        messages = tuple(PromptMessage(m.role, strip_markers(m.content)) for m in self.messages)
        return PromptTemplate(messages, self.optimize)

    def to_json(self) -> str:
        """Canonical JSON used for storage and hashing."""
        payload = {
            "messages": [{"role": m.role, "content": m.content} for m in self.messages],
            "optimize": sorted(self.optimize),
        }
        return json.dumps(payload, sort_keys=True, ensure_ascii=False)

    @classmethod
    def from_json(cls, text: str) -> "PromptTemplate":
        data = json.loads(text)
        messages = tuple(PromptMessage(m["role"], m["content"]) for m in data["messages"])
        return cls(messages, frozenset(data["optimize"]))

    @property
    def content_hash(self) -> str:
        return hashlib.sha256(self.to_json().encode("utf-8")).hexdigest()
