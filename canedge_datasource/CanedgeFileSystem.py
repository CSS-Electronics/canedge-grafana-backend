import os
import re
from canedge_browser import RelativeFileSystem


class CanedgeFileSystem(RelativeFileSystem):
    """Extends the RelativeFileSystem class with CANedge specific methods
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def get_device_ids(self, reverse: bool = False) -> str:
        """Get device IDs """
        for elm in sorted(self.listdir("/", detail=False), reverse=reverse):
            if self.isdir(elm):
                device, _, _, _ = self.path_to_pars(elm)
                if device is not None:
                    yield device

    def get_device_sessions(self, device: str, reverse: bool = False) -> (str, str):
        """Get sessions of device ID"""
        for elm in sorted(self.listdir(os.path.join("/", device), detail=False), reverse=reverse):
            if self.isdir(elm):
                device, session, _, _ = self.path_to_pars(elm)
                if None not in [device, session]:
                    yield session, elm

    def get_device_splits(self, device: str, session: str, reverse: bool = False) -> (str, str):
        """Get splits of device ID and session"""
        for elm in sorted(self.listdir(os.path.join("/", device, session), detail=False), reverse=reverse):
            if self.isfile(elm):
                device, session, split, _ = self.path_to_pars(elm)
                if None not in [device, session, split]:
                    yield split, elm

    def get_device_log_files(self, device, reverse: bool = False):
        """Gets all device log files. Note that this can be expensive"""
        for session, _ in self.get_device_sessions(device, reverse=reverse):
            for split, log_file in self.get_device_splits(device, session, reverse=reverse):
                yield log_file, session, split

    def path_to_pars(self, path):
        """Matches as much as possible of path to CANedge pars (device id, session, split, extension)"""
        pattern = r"^(?P<device_id>[0-9A-F]{8})?((/)(?P<session_no>\d{8}))?((/)(?P<split_no>\d{8})(?:-[0-9A-F]{8}){0,1}(?P<ext>\.(MF4|MFC|MFM|MFE)))?$"
        match = re.match(pattern, path, re.IGNORECASE)
        if match:
            return match.group("device_id"), match.group("session_no"), match.group("split_no"), match.group("ext")
        else:
            return None, None, None, None
