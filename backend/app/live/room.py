"""LiveKit room and participant contract helpers."""

from dataclasses import dataclass

from app.config import settings


@dataclass
class LiveKitParticipantContract:
    livekit_url: str
    room_name: str
    participant_identity: str
    participant_name: str
    token: str


def create_livekit_participant(
    session_id: str,
    *,
    role: str,
    name: str,
    room_name: str | None = None,
    identity: str | None = None,
    can_publish: bool = True,
    can_subscribe: bool = True,
    can_publish_data: bool = True,
) -> LiveKitParticipantContract:
    """Create a LiveKit access token for a room participant."""
    from livekit import api as livekit_api

    resolved_room = room_name or f"demo-{session_id}"
    resolved_identity = identity or f"{role}-{session_id}"

    token = livekit_api.AccessToken(
        settings.livekit_api_key,
        settings.livekit_api_secret,
    )
    token.with_identity(resolved_identity)
    token.with_name(name)
    token.with_grants(
        livekit_api.VideoGrants(
            room_join=True,
            room=resolved_room,
            can_publish=can_publish,
            can_subscribe=can_subscribe,
            can_publish_data=can_publish_data,
        )
    )

    return LiveKitParticipantContract(
        livekit_url=settings.livekit_url,
        room_name=resolved_room,
        participant_identity=resolved_identity,
        participant_name=name,
        token=token.to_jwt(),
    )
