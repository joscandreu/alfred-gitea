#!/usr/bin/python3
# encoding: utf-8
"""`tea home`: print the configured Gitea URL (opened by Alfred)."""
from workflow import Workflow3

import gitea_common as gc

wf = Workflow3()
# Only ever print a validated https URL, so Alfred cannot be made to open
# something else (e.g. a file:// URL) via a tampered settings file.
print(gc.get_base_url(wf) or '')
