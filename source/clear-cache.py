#!/usr/bin/python3
# encoding: utf-8
"""`tea clearcache`: delete the cached repository list."""
from workflow import Workflow


def main(wf):
    wf.clear_cache()


if __name__ == u"__main__":
    wf = Workflow()
    log = wf.logger
    wf.run(main)
