from pytgcalls import filters as call_filters
from pytgcalls.types import ChatUpdate, StreamEnded

from config import Config
from user import group_call
from utils import skip, LOGGER


@group_call.on_update(
    call_filters.chat_update(
        ChatUpdate.Status.KICKED | ChatUpdate.Status.LEFT_GROUP,
    )
)
async def call_state(_, update: ChatUpdate):
    Config.CALL_STATUS = False
    Config.PAUSE = False
    Config.MUTED = False


@group_call.on_update(call_filters.stream_end())
async def stream_end(_, update: StreamEnded):
    try:
        await skip()
    except Exception as e:
        LOGGER.error("Failed to advance after stream ended: %s", e, exc_info=True)
