#!/usr/bin/python3
# encoding: utf-8
"""`tea reset`: delete cache, settings and all stored secrets."""
from workflow import Workflow

import gitea_common as gc


def main(wf):
    wf.reset()
    # wf.reset() does not touch the Keychain; remove the token and the
    # client key passphrase too, as documented.
    for account in gc.ALL_ACCOUNTS:
        gc.delete_secret(wf, account)


if __name__ == u"__main__":
    wf = Workflow()
    log = wf.logger
    wf.run(main)
