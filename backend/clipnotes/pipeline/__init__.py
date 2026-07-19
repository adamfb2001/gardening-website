import logging

from ..config import Settings
from .base import Pipeline, PipelineError
from .stub import build_stub_pipeline

log = logging.getLogger(__name__)

__all__ = ["Pipeline", "PipelineError", "build_pipeline", "build_stub_pipeline"]


def build_pipeline(settings: Settings) -> Pipeline:
    """Choose the pipeline per settings.pipeline_mode:

    - "real": yt-dlp + local Whisper (+ Claude synthesis when a key is set)
    - "stub": deterministic placeholders (used by the test suite)
    - "auto": real, degrading to stub only if the real deps aren't installed
    """
    mode = settings.pipeline_mode.lower()
    if mode == "stub":
        return build_stub_pipeline(settings)
    try:
        from .real import NoopVision, WhisperTranscriber, YtDlpResolver
        from .synth import build_synthesiser
    except ImportError as error:
        if mode == "real":
            raise
        log.warning("real pipeline unavailable (%s); falling back to stub", error)
        return build_stub_pipeline(settings)
    return Pipeline(
        resolver=YtDlpResolver(),
        transcriber=WhisperTranscriber(settings),
        vision=NoopVision(),
        synthesiser=build_synthesiser(settings),
    )
