from watchdog.events import PatternMatchingEventHandler
from watchdog.observers import Observer

from typing import Callable

from utils.constants import audio_extensions

import os

class DirectoryWatcher(PatternMatchingEventHandler):
    def __init__(self, trigger_function: Callable[[str, str], None]):
        patterns = [f"*.{ext}" for ext in audio_extensions]
        super().__init__(patterns=patterns, ignore_directories=True, case_sensitive=False)
        self.trigger_function = trigger_function

    def on_created(self, event):
        self.trigger_function("create", event.src_path)
        
    def on_deleted(self, event):
        self.trigger_function("delete", event.src_path)

def watch_directories(directory_paths: list[str], func: Callable[[str, str], None]):
    event_handler = DirectoryWatcher(func)
    observer = Observer()
    
    for directory_path in directory_paths:
        observer.schedule(event_handler, path=directory_path)

    observer.start()
    return observer

def file_hit(event_type: str, file_path: str, directories: dict[str, list[str]], func: Callable[[str, str], None]):
    directory = os.path.dirname(file_path)
    if directory in directories and file_path in directories[directory]:
        func(event_type, file_path)

def watch_files(file_paths: list[str], func: Callable[[str, str], None]):
    directories: dict[str, list[str]] = {}
    for file_path in file_paths:
        directory = os.path.dirname(file_path)
        directories.setdefault(directory, []).append(file_path)

    return watch_directories(
        list(directories.keys()),
        lambda event_type, file_path: file_hit(event_type, file_path, directories, func)
    )