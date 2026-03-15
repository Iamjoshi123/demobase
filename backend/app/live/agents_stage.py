"""LiveKit Agents-backed browser stage primitives."""

from __future__ import annotations

import asyncio
from contextlib import suppress

from livekit import rtc
from livekit.agents.voice.avatar import AvatarOptions, AvatarRunner
from livekit.agents.voice.avatar._queue_io import QueueAudioOutput
from livekit.agents.voice.avatar._types import AudioSegmentEnd, VideoGenerator


class BrowserFrameGenerator(VideoGenerator):
    """Merge browser video frames and agent audio frames into one AV queue."""

    def __init__(self, *, max_queue_size: int = 256) -> None:
        self._queue: asyncio.Queue[rtc.VideoFrame | rtc.AudioFrame | AudioSegmentEnd | object] = asyncio.Queue(
            maxsize=max_queue_size
        )
        self._closed = False
        self._sentinel = object()

    async def push_audio(self, frame: rtc.AudioFrame | AudioSegmentEnd) -> None:
        await self._enqueue(frame)

    async def push_video(self, frame: rtc.VideoFrame) -> None:
        await self._enqueue(frame)

    def clear_buffer(self) -> None:
        while True:
            try:
                item = self._queue.get_nowait()
            except asyncio.QueueEmpty:
                break
            if item is self._sentinel:
                self._queue.put_nowait(self._sentinel)
                break

    async def aclose(self) -> None:
        if self._closed:
            return
        self._closed = True
        await self._enqueue(self._sentinel)

    async def __aiter__(self):
        while True:
            item = await self._queue.get()
            if item is self._sentinel:
                break
            yield item

    async def _enqueue(self, item: rtc.VideoFrame | rtc.AudioFrame | AudioSegmentEnd | object) -> None:
        if self._closed and item is not self._sentinel:
            return
        while self._queue.full():
            with suppress(asyncio.QueueEmpty):
                self._queue.get_nowait()
        await self._queue.put(item)


class BrowserStageRunner(AvatarRunner):
    """AvatarRunner variant that publishes the track names expected by the buyer UI."""

    def __init__(
        self,
        room: rtc.Room,
        *,
        audio_recv: QueueAudioOutput,
        video_gen: BrowserFrameGenerator,
        options: AvatarOptions,
        audio_track_name: str = "agent-audio",
        video_track_name: str = "browser-video",
        _queue_size_ms: int = 100,
        _lazy_publish: bool = True,
    ) -> None:
        super().__init__(
            room,
            audio_recv=audio_recv,
            video_gen=video_gen,
            options=options,
            _queue_size_ms=_queue_size_ms,
            _lazy_publish=_lazy_publish,
        )
        self._audio_track_name = audio_track_name
        self._video_track_name = video_track_name

    async def _publish_track(self) -> None:
        async with self._lock:
            await self._room_connected_fut

            if self._audio_publication is not None:
                with suppress(Exception):
                    await self._room.local_participant.unpublish_track(self._audio_publication.sid)
                self._audio_publication = None
            if self._video_publication is not None:
                with suppress(Exception):
                    await self._room.local_participant.unpublish_track(self._video_publication.sid)
                self._video_publication = None

            audio_track = rtc.LocalAudioTrack.create_audio_track(self._audio_track_name, self._audio_source)
            audio_options = rtc.TrackPublishOptions(source=rtc.TrackSource.SOURCE_MICROPHONE)
            self._audio_publication = await self._room.local_participant.publish_track(audio_track, audio_options)
            await self._audio_publication.wait_for_subscription()

            video_track = rtc.LocalVideoTrack.create_video_track(self._video_track_name, self._video_source)
            video_options = rtc.TrackPublishOptions(source=rtc.TrackSource.SOURCE_CAMERA)
            self._video_publication = await self._room.local_participant.publish_track(video_track, video_options)
            await self._video_publication.wait_for_subscription()


def build_stage_options(
    *,
    video_width: int = 1280,
    video_height: int = 720,
    video_fps: float = 4.0,
    audio_sample_rate: int = 24000,
    audio_channels: int = 1,
) -> AvatarOptions:
    return AvatarOptions(
        video_width=video_width,
        video_height=video_height,
        video_fps=video_fps,
        audio_sample_rate=audio_sample_rate,
        audio_channels=audio_channels,
    )
