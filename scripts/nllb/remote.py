#!/usr/bin/env python3
"""Train the second-draft model on another machine with a GPU (your own, or one rented by the hour), over ssh and rsync.
The machine is named only in your environment or in .env (git-ignored), never in the repo:

    NLLB_HOST=user@host            the machine (an ssh target; keys set up for it)
    NLLB_DIR=~/bsb-nllb            the folder there (default ~/bsb-nllb); one subfolder per project
    NLLB_PYTHON=python3            its Python with scripts/nllb/requirements.txt installed (a venv's python)

  push    python3 scripts/nllb/remote.py push <project>      the data (scripts/nllb/data.py), train.py and model_text.py to the machine
  train   python3 scripts/nllb/remote.py train <project> [train.py options]   starts training there, detached (nohup),
          and returns; the log is <dir>/train.log
  status  python3 scripts/nllb/remote.py status <project>    the log's last lines, and whether the model is ready
  fetch   python3 scripts/nllb/remote.py fetch <project>     the model and scores back into <project>/_eval/local/nllb/run/;
          drafting then runs here (scripts/nllb/draft.py run, on the processor too)

The data holds edition text: send it only to a machine you control or rent for yourself, and delete it there afterwards
(rented machines: when the model is fetched). Nothing here deletes remote files.
"""
import os, shlex, subprocess, sys

CODE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ROOT = os.path.abspath(os.environ.get("MAKE_TANAKH_ROOT") or CODE)   # the data root (books.py)
sys.path.insert(0, os.path.join(CODE, "scripts"))
import localenv  # noqa: E402
from project import project_dir  # noqa: E402


def conf():
    host = localenv.key("NLLB_HOST")
    if not host:
        raise SystemExit("set NLLB_HOST (user@host) in the environment or in .env (git-ignored); see the docstring")
    return host, localenv.key("NLLB_DIR") or "~/bsb-nllb", localenv.key("NLLB_PYTHON") or "python3"


def rdir(base, pname):
    return f"{base.rstrip('/')}/{pname.replace('/', '__')}"


def ssh(host, cmd, capture=False):
    return subprocess.run(["ssh", host, cmd], check=True, text=True, capture_output=capture).stdout


def main():
    a = sys.argv[1:]
    if len(a) < 2 or a[0] not in ("push", "train", "status", "fetch"):
        raise SystemExit(__doc__)
    cmd, pname, rest = a[0], a[1], a[2:]
    host, base, py = conf()
    d = rdir(base, pname)
    local = os.path.join(project_dir(pname), "_eval", "local", "nllb")
    if cmd == "push":
        data = os.path.join(local, "data")
        if not os.path.exists(os.path.join(data, "meta.json")):
            raise SystemExit(f"no training data: python3 scripts/nllb/data.py {pname}")
        ssh(host, f"mkdir -p {d}")
        subprocess.run(["rsync", "-a", os.path.join(CODE, "scripts", "nllb", "train.py"),
                        os.path.join(CODE, "scripts", "nllb", "model_text.py"),
                        os.path.join(CODE, "scripts", "nllb", "requirements.txt"), f"{host}:{d}/"], check=True)
        subprocess.run(["rsync", "-a", "--delete", data + "/", f"{host}:{d}/data/"], check=True)
        print(f"pushed to {host}:{d}")
    elif cmd == "train":
        args = " ".join(shlex.quote(x) for x in rest)
        ssh(host, f"cd {d} && nohup {py} train.py --data data --out run {args} > train.log 2>&1 < /dev/null &")
        print(f"training started on {host}:{d} (python3 scripts/nllb/remote.py status {pname})")
    elif cmd == "status":
        print(ssh(host, f"cd {d} && (tail -c 600 train.log | tr '\\r' '\\n' | tail -4); "
                        f"test -f run/model/meta.json && echo '# model ready: fetch it' || echo '# not ready'", capture=True))
    elif cmd == "fetch":
        os.makedirs(os.path.join(local, "run"), exist_ok=True)
        subprocess.run(["rsync", "-a", f"{host}:{d}/run/model", f"{host}:{d}/run/scores.json", os.path.join(local, "run") + "/"],
                       check=True)
        print(f"fetched into {os.path.relpath(os.path.join(local, 'run'), ROOT)}; the data is still on {host}:{d}/data")


if __name__ == "__main__":
    main()
