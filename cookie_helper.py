#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ASCII-named launcher for the Chinese-named Cookie helper."""

from pathlib import Path
import runpy


if __name__ == "__main__":
    target = Path(__file__).with_name("获取抖音Cookie.py")
    runpy.run_path(str(target), run_name="__main__")
