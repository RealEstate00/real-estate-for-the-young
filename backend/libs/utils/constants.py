#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Global constants and configuration
"""

from datetime import timezone, timedelta

# Timezone
KST = timezone(timedelta(hours=9))

# Allowed file extensions for downloads
ALLOWED_EXTS = {".pdf", ".hwp", ".hwpx", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".zip"}