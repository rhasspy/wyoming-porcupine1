#!/usr/bin/env python3
import argparse
import asyncio
import logging
import platform
import struct
import time
from collections import defaultdict
from dataclasses import dataclass
from functools import partial
from pathlib import Path
from typing import Dict, List, Optional

import pvporcupine
from wyoming.audio import AudioChunk, AudioChunkConverter, AudioStart, AudioStop
from wyoming.event import Event
from wyoming.info import Attribution, Describe, Info, WakeModel, WakeProgram
from wyoming.server import AsyncEventHandler, AsyncServer
from wyoming.wake import Detect, Detection, NotDetected

from . import __version__

_LOGGER = logging.getLogger()
_DIR = Path(__file__).parent

DEFAULT_KEYWORD = "porcupine"


@dataclass
class Keyword:
    """Single porcupine keyword"""

    language: str
    name: str
    model_path: Path


@dataclass
class Detector:
    porcupine: pvporcupine.Porcupine
    sensitivity: float


class State:
    """State of system"""

    def __init__(self, pv_lib_paths: Dict[str, Path], keywords: Dict[str, Keyword]):
        self.pv_lib_paths = pv_lib_paths
        self.keywords = keywords

        # keyword name -> [detector]
        self.detector_cache: Dict[str, List[Detector]] = defaultdict(list)
        self.detector_lock = asyncio.Lock()

    async def get_porcupine(self, keyword_name: str, sensitivity: float, access_key: str) -> Detector:
        keyword = self.keywords.get(keyword_name)
        if keyword is None:
            raise ValueError(f"No keyword {keyword_name}")

        # Check cache first for matching detector
        async with self.detector_lock:
            detectors = self.detector_cache.get(keyword_name)
            if detectors:
                detector = next(
                    (d for d in detectors if d.sensitivity == sensitivity), None
                )
                if detector is not None:
                    # Remove from cache for use
                    detectors.remove(detector)

                    _LOGGER.debug(
                        "Using detector for %s from cache (%s)",
                        keyword_name,
                        len(detectors),
                    )
                    return detector

        _LOGGER.debug("Loading %s for %s", keyword.name, keyword.language)
        porcupine = pvporcupine.create(
            access_key=access_key,
            model_path=str(self.pv_lib_paths[keyword.language]),
            keyword_paths=[str(keyword.model_path)],
            sensitivities=[sensitivity],
        )

        return Detector(porcupine, sensitivity)


async def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--uri", default="stdio://", help="unix:// or tcp://")
    parser.add_argument(
        "--data-dir", default=_DIR / "data", help="Path to directory lib/resources"
    )
    parser.add_argument(
        "--custom-wake-words-dir",
        help="Path to directory for custom wake words",
    )
    parser.add_argument("--system", help="linux or raspberry-pi")
    parser.add_argument("--sensitivity", type=float, default=0.5)
    parser.add_argument("--access-key", help="Access key for porcupine", type=str, default="")
    parser.add_argument("--debug", action="store_true", help="Log DEBUG messages")
    parser.add_argument(
        "--log-format", default=logging.BASIC_FORMAT, help="Format for log messages"
    )
    parser.add_argument("--version", action="store_true", help="Print version and exit")

    args = parser.parse_args()
    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.INFO, format=args.log_format
    )
    _LOGGER.debug(args)

    if args.version:
        print(__version__)
        return

    if not args.system:
        machine = platform.machine().lower()
        machine_platform = platform.platform().lower()
        if ("macos" in machine_platform):
            args.system = "mac"
        elif ("arm" in machine) or ("aarch" in machine):
            args.system = "raspberry-pi"
        else:
            args.system = "linux"

    args.data_dir = Path(args.data_dir)

    # lang -> path
    pv_lib_paths: Dict[str, Path] = {}
    for lib_path in (args.data_dir / "lib" / "common").glob("*.pv"):
        lib_lang = lib_path.stem.split("_")[-1]
        pv_lib_paths[lib_lang] = lib_path

    # name -> keyword
    keywords: Dict[str, Keyword] = {}
    for kw_path in (args.data_dir / "resources").rglob("*.ppn"):
        kw_system = kw_path.stem.split("_")[-1]
        if kw_system != args.system:
            continue

        kw_lang = kw_path.parent.parent.name
        kw_name = kw_path.stem.rsplit("_", maxsplit=1)[0]
        keywords[kw_name] = Keyword(language=kw_lang, name=kw_name, model_path=kw_path)

    if (args.custom_wake_words_dir is not None):
        args.custom_wake_words_dir = Path(args.custom_wake_words_dir)
        for custom_kw_path in (args.custom_wake_words_dir).rglob("*.ppn"):
            kw_lang = custom_kw_path.stem.rsplit("_")[1]
            kw_name = custom_kw_path.stem.rsplit("_")[0]
            keywords[kw_name] = Keyword(language=kw_lang, name=kw_name, model_path=custom_kw_path)
            _LOGGER.info(kw_lang)
            _LOGGER.info(kw_name)

    wyoming_info = Info(
        wake=[
            WakeProgram(
                name="porcupine3",
                description="On-device wake word detection powered by deep learning ",
                attribution=Attribution(
                    name="Picovoice", url="https://github.com/Picovoice/porcupine"
                ),
                installed=True,
                version=__version__,
                models=[
                    WakeModel(
                        name=kw.name,
                        description=f"{kw.name} ({kw.language})",
                        attribution=Attribution(
                            name="Picovoice",
                            url="https://github.com/Picovoice/porcupine",
                        ),
                        installed=True,
                        languages=[kw.language],
                        version="3.0.2",
                    )
                    for kw in keywords.values()
                ],
            )
        ],
    )

    state = State(pv_lib_paths=pv_lib_paths, keywords=keywords)

    _LOGGER.info("Ready")

    # Start server
    server = AsyncServer.from_uri(args.uri)

    try:
        await server.run(partial(Porcupine3EventHandler, wyoming_info, args, state))
    except KeyboardInterrupt:
        pass


# -----------------------------------------------------------------------------


class Porcupine3EventHandler(AsyncEventHandler):
    """Event handler for clients."""

    def __init__(
        self,
        wyoming_info: Info,
        cli_args: argparse.Namespace,
        state: State,
        *args,
        **kwargs,
    ) -> None:
        super().__init__(*args, **kwargs)

        self.cli_args = cli_args
        self.wyoming_info_event = wyoming_info.event()
        self.client_id = str(time.monotonic_ns())
        self.state = state
        self.converter = AudioChunkConverter(rate=16000, width=2, channels=1)
        self.audio_buffer = bytes()
        self.detected = False

        self.detector: Optional[Detector] = None
        self.keyword_name: str = ""
        self.chunk_format: str = ""
        self.bytes_per_chunk: int = 0

        _LOGGER.debug("Client connected: %s", self.client_id)

    async def handle_event(self, event: Event) -> bool:
        if Describe.is_type(event.type):
            await self.write_event(self.wyoming_info_event)
            _LOGGER.debug("Sent info to client: %s", self.client_id)
            return True

        if Detect.is_type(event.type):
            detect = Detect.from_event(event)
            if detect.names:
                # TODO: use all names
                await self._load_keyword(detect.names[0])
        elif AudioStart.is_type(event.type):
            self.detected = False
        elif AudioChunk.is_type(event.type):
            if self.detector is None:
                # Default keyword
                await self._load_keyword(DEFAULT_KEYWORD)

            assert self.detector is not None

            chunk = AudioChunk.from_event(event)
            chunk = self.converter.convert(chunk)
            self.audio_buffer += chunk.audio

            while len(self.audio_buffer) >= self.bytes_per_chunk:
                unpacked_chunk = struct.unpack_from(
                    self.chunk_format, self.audio_buffer[: self.bytes_per_chunk]
                )
                keyword_index = self.detector.porcupine.process(unpacked_chunk)
                if keyword_index >= 0:
                    _LOGGER.debug(
                        "Detected %s from client %s", self.keyword_name, self.client_id
                    )
                    await self.write_event(
                        Detection(
                            name=self.keyword_name, timestamp=chunk.timestamp
                        ).event()
                    )

                self.audio_buffer = self.audio_buffer[self.bytes_per_chunk :]

        elif AudioStop.is_type(event.type):
            # Inform client if not detections occurred
            if not self.detected:
                # No wake word detections
                await self.write_event(NotDetected().event())

                _LOGGER.debug(
                    "Audio stopped without detection from client: %s", self.client_id
                )

            return False
        else:
            _LOGGER.debug("Unexpected event: type=%s, data=%s", event.type, event.data)

        return True

    async def disconnect(self) -> None:
        _LOGGER.debug("Client disconnected: %s", self.client_id)

        if self.detector is not None:
            # Return detector to cache
            async with self.state.detector_lock:
                self.state.detector_cache[self.keyword_name].append(self.detector)
                self.detector = None
                _LOGGER.debug(
                    "Detector for %s returned to cache (%s)",
                    self.keyword_name,
                    len(self.state.detector_cache[self.keyword_name]),
                )

    async def _load_keyword(self, keyword_name: str):
        self.detector = await self.state.get_porcupine(
            keyword_name, self.cli_args.sensitivity, self.cli_args.access_key
        )
        self.keyword_name = keyword_name
        self.chunk_format = "h" * self.detector.porcupine.frame_length
        self.bytes_per_chunk = self.detector.porcupine.frame_length * 2


# -----------------------------------------------------------------------------


def run() -> None:
    asyncio.run(main())


if __name__ == "__main__":
    try:
        run()
    except KeyboardInterrupt:
        pass
