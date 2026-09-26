from pytgcalls.types import Update
from pytgcalls.types.groups import JoinedVoiceChat, LeftVoiceChat
from pytgcalls.types.stream import (
    PausedStream, ResumedStream, MutedStream, UnMutedStream,
    StreamAudioEnded, StreamVideoEnded,
)
from config import Config
from user import group_call
from utils import skip, LOGGER

@group_call.on_raw_update()
async def call_state(_, update: Update):
    if isinstance(update, JoinedVoiceChat):
        Config.CALL_STATUS = True
    elif isinstance(update, LeftVoiceChat):
        Config.CALL_STATUS = False
        Config.PAUSE = False
    elif isinstance(update, PausedStream):
        Config.PAUSE = True
    elif isinstance(update, ResumedStream):
        Config.PAUSE = False
    elif isinstance(update, MutedStream):
        Config.MUTED = True
    elif isinstance(update, UnMutedStream):
        Config.MUTED = False

@group_call.on_stream_end()
async def stream_end(_, update: Update):
    if isinstance(update, (StreamAudioEnded, StreamVideoEnded)):
        try:
            await skip()
        except Exception as e:
            LOGGER.error("Failed to advance after stream ended: %s", e, exc_info=True)
