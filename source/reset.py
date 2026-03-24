# encoding: utf-8
from workflow import Workflow, PasswordNotFound

# log = None

def main(wf):
    wf.reset()
    try:
        wf.delete_password('gitea_p12_passphrase')
    except PasswordNotFound:
        pass

if __name__ == u"__main__":
    wf = Workflow()
    log = wf.logger
    wf.run(main)
