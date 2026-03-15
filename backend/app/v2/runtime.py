"""In-memory runtime registry for v2 meetings."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class MeetingRuntimeState:
    session_id: str
    workspace_id: str
    room_name: Optional[str] = None
    rtc_ready: bool = False
    browser_planned: bool = False
    last_recipe_id: Optional[str] = None
    last_focus: Optional[str] = None


class MeetingRuntimeRegistry:
    def __init__(self) -> None:
        self._states: dict[str, MeetingRuntimeState] = {}

    def ensure(self, session_id: str, workspace_id: str) -> MeetingRuntimeState:
        state = self._states.get(session_id)
        if state is None:
            state = MeetingRuntimeState(session_id=session_id, workspace_id=workspace_id)
            self._states[session_id] = state
        return state

    def get(self, session_id: str) -> Optional[MeetingRuntimeState]:
        return self._states.get(session_id)

    def reset(self, session_id: str) -> None:
        self._states.pop(session_id, None)


runtime_registry = MeetingRuntimeRegistry()
