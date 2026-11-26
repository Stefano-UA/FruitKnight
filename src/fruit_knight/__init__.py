"""Fruit Knight: webcam-controlled serious game for upper-limb rehabilitation."""

__version__ = "1.0.0"

import os as _os

# Must be set before OpenCV loads: avoids the very slow hardware-transform start-up of the Windows MSMF backend.
_os.environ.setdefault("OPENCV_VIDEOIO_MSMF_ENABLE_HW_TRANSFORMS", "0")
