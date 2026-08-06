# Deployment — DLSU ALTDSI GPU VM

Target: `ALTDSI-GPU-R05` (A100-PCIE-40GB)

| | |
|---|---|
| SSH | `ssh root@altdsidccf.dlsu.edu.ph -p 32051` |
| HTTP | `http://altdsidccf.dlsu.edu.ph:32050` → VM port 80 |

## Verdict: doable — the blocking risk was checked and cleared

The deployment is one process on port 80 serving both the API and the built
frontend. Nothing about the app resists it.

The one thing that could have killed it was outbound network access from the VM to
Bedrock, since every analysis is 3–4 calls to
`bedrock-runtime.ap-southeast-1.amazonaws.com`. **That has been checked and it
works.**

Verified on 2026-08-06:

| Check | Result |
|---|---|
| SSH 32051 reachable off-campus | yes |
| VM → Bedrock egress | **yes** — HTTP 404 from the endpoint over validated TLS |
| VM port 80 | free |
| `systemctl` / `tmux` / `git` / `rsync` on VM | all present |
| Single-origin serving (`/` + `/api/*` one process) | verified locally |
| Backend suite with the static mount | 75 passed |

On the egress check: a 404 is proof of success, not failure. It means a real HTTPS
response came back from AWS with a certificate curl validated — a blocked or
filtered path returns `000` and no TLS handshake. The endpoint 404s on a bare GET
to `/` because there is no resource there, which is exactly right.

What remains unverified is the token and model ID working *from that machine*, which
step 5 tests directly, and end-to-end latency through the port forward.

## The shape: one origin, one process, one port

The VM exposes exactly one HTTP port. That constraint decides the architecture,
and it happens to land on the simplest option:

**FastAPI serves the built frontend as static files, alongside `/api/*`, on port 80.**

This works because `frontend/src/api.ts` calls **relative** paths (`/api/analyze`,
`/api/meta`). Same origin means no CORS configuration, no API-base-URL environment
variable, and nothing to get wrong between the two halves.

### Why not put the frontend on Vercel

It was considered and rejected. Three reasons, in order of how fatal they are:

1. **Mixed content.** Vercel serves HTTPS. The VM serves plain HTTP on a
   non-standard port. A browser on an HTTPS page will block every `fetch` to an
   HTTP backend, silently, with no way for the user to override it. This alone
   ends it.
2. **No TLS path.** Fixing (1) needs a certificate for `altdsidccf.dlsu.edu.ph`,
   which we do not control, on port 32050. Not happening in a week.
3. **It would add work.** Splitting the origins means adding a CORS origin list,
   an API base URL config, and a second deploy target — all to make the app
   strictly worse.

Single-origin on the VM is both the easiest and the only one that works.

## The code change (already applied)

`backend/app/main.py` now mounts the built frontend, **at the end of the file** —
after the route definitions, because FastAPI matches routes in registration order
and a mount at `/` would otherwise swallow `/api/*`:

```python
FRONTEND_DIST = Path(__file__).resolve().parents[1] / "static"

if FRONTEND_DIST.is_dir():
    app.mount("/", StaticFiles(directory=FRONTEND_DIST, html=True), name="frontend")
```

The `is_dir()` guard is load-bearing: `StaticFiles` raises at construction time if
the directory is missing, which would break `uv run pytest` and local dev on any
machine that has not built the frontend. `backend/static/` is gitignored, so it
never exists in a fresh clone and the mount stays inert everywhere except a
deployed box.

This is why **no separate deploy branch is needed**. The change is inert without a
build directory, and every genuinely deploy-specific artifact — `backend/static/`,
`backend/.env`, `knowledge-base/out/kb.sqlite` — is gitignored and travels by
rsync, not git. A deploy branch would carry no content that `main` does not, while
costing a second merge on every feature.

Verified locally against a real build: `/` returns `index.html`, `/assets/*.js`
returns JavaScript, `/api/health` and `/api/meta` still route to the API, and the
backend suite passes 75/75.

## Deploy

### 1. Check Bedrock egress — DONE

Recorded for anyone redeploying to a different box. Skip it on this VM; it passed
on 2026-08-06.

```bash
ssh root@altdsidccf.dlsu.edu.ph -p 32051
# password: ALTDSI1234!

curl -s -o /dev/null -w '%{http_code}\n' \
  https://bedrock-runtime.ap-southeast-1.amazonaws.com   # -> 404 = reachable
ss -lntp | grep ':80 ' || echo 'port 80 free'            # -> free
command -v systemctl tmux git rsync                      # -> all four present
```

Any HTTP status proves egress. `000` means blocked — stop and read
[If Bedrock is unreachable](#if-bedrock-is-unreachable).

### 2. Build the frontend and stage it — DONE

Build on the Mac, not the VM. It avoids installing Node and a `node_modules` tree
on the VM for a one-time build. Rerun both lines whenever frontend code changes:

```bash
cd frontend && npm run build                    # -> frontend/dist/
cd .. && rm -rf backend/static && cp -R frontend/dist backend/static
```

`backend/static/` is the directory the mount looks for. Staging it inside
`backend/` means a single rsync of the repo carries the app and its frontend
together, with no second copy step to forget.

### 3. Upload to the VM

Git is not the transport. Three files the app cannot run without are gitignored and
would never survive a clone: `knowledge-base/out/kb.sqlite`, `backend/.env`, and
the `backend/static/` build from step 2.

**Build one archive and upload that one file.** Do not drag the project folder into
VS Code's remote explorer — two reasons, both of which bite silently:

- `backend/.venv` is 903 MB of **macOS** binaries and `frontend/node_modules` is
  another 138 MB. Neither is usable on Linux, and together they turn a one-second
  transfer into a very long one.
- Finder hides dotfiles. Select-all inside a folder does not pick up `backend/.env`
  unless you have pressed Cmd-Shift-. first, so the single most important file is
  the one most likely to be left behind.

A tarball sidesteps both: everything needed, nothing else, and it either arrives or
it does not. Build it on the Mac:

```bash
cd /Users/achibukz/Code/GitHub/Elderly-Scam-Shield

COPYFILE_DISABLE=1 tar czf ~/Desktop/kalasag-deploy.tgz \
  --exclude='__pycache__' --exclude='.pytest_cache' --exclude='.venv' \
  --exclude='backend/eval/results' \
  backend/app backend/tests backend/eval backend/pyproject.toml backend/uv.lock \
  backend/.env backend/.env.example backend/static backend/check_bedrock_connection.py \
  knowledge-base/out/kb.sqlite docs/DEPLOYMENT.md
```

That is **about 1 MB**. `COPYFILE_DISABLE=1` suppresses the `._` AppleDouble files
macOS otherwise scatters through the archive.

The paths are relative to the repo root and must stay that way. `config.py` resolves
the KB as `<backend>/../knowledge-base/out/kb.sqlite`, so flattening the structure
sends it back to the fixture.

Then in VS Code Remote-SSH: open the remote window, navigate the Explorer to
`/root`, and drag `kalasag-deploy.tgz` in. Extract it in the remote terminal:

```bash
mkdir -p /root/kalasag && tar xzf /root/kalasag-deploy.tgz -C /root/kalasag
rm /root/kalasag-deploy.tgz
```

Now confirm all three landed. **This is the most common way this deployment fails
silently** — a missing KB falls back to the fixture and still returns plausible
answers, so nothing in the UI looks wrong:

```bash
ls -l /root/kalasag/knowledge-base/out/kb.sqlite   # ~1.7 MB
ls /root/kalasag/backend/static/index.html
grep -c AWS_BEARER_TOKEN_BEDROCK /root/kalasag/backend/.env
```

Delete the local `~/Desktop/kalasag-deploy.tgz` when you are done — it contains the
Bedrock bearer token in cleartext.

If you would rather not use the VS Code explorer, one `scp` does the same thing:

```bash
scp -P 32051 ~/Desktop/kalasag-deploy.tgz root@altdsidccf.dlsu.edu.ph:/root/
```

### 4. Install dependencies — everything inside `/root/kalasag`

A default install scatters across four locations outside the project: the `uv`
binary in `~/.local/bin`, uv's wheel cache in `~/.cache/uv`, uv's managed Python
in `~/.local/share/uv/python`, and the HuggingFace model cache in
`~/.cache/huggingface`. Together that is multiple gigabytes that `rm -rf
/root/kalasag` would not reclaim.

Redirect all four into `/root/kalasag/.local/` so the deployment is one deletable
folder. Write this env file first:

```bash
mkdir -p /root/kalasag/.local
cat > /root/kalasag/.local/env.sh <<'EOF'
export UV_CACHE_DIR=/root/kalasag/.local/uv-cache
export UV_PYTHON_INSTALL_DIR=/root/kalasag/.local/uv-python
export HF_HOME=/root/kalasag/.local/hf
export PATH=/root/kalasag/.local/bin:$PATH
EOF
```

Then install and sync. **Source that file in every new shell** — including when you
reattach to tmux later, or uv will silently rebuild its cache in `~`:

```bash
source /root/kalasag/.local/env.sh

curl -LsSf https://astral.sh/uv/install.sh \
  | env UV_INSTALL_DIR=/root/kalasag/.local/bin INSTALLER_NO_MODIFY_PATH=1 sh

command -v uv          # must print /root/kalasag/.local/bin/uv

cd /root/kalasag/backend
UV_TORCH_BACKEND=cpu uv sync
```

`uv sync` installs Python 3.13/3.14 itself if the VM lacks it, so no system Python
setup is needed.

**`UV_TORCH_BACKEND=cpu` is deliberate on a GPU box.** `sentence-transformers`
pulls `torch`, and the default Linux wheel drags in the bundled CUDA runtime —
roughly 4–5 GB installed against 1.5 GB for the CPU build. The A100 buys nothing
here: the only local model is a 118M-parameter embedder scoring one short string
per request, and the actual LLM is remote on Bedrock. Paying 3 GB and a long
download for an idle GPU is pure cost.

If your `uv` is too old to know that flag it will error rather than silently
install CUDA. Fall back to:

```bash
uv sync && uv pip install torch --index-url https://download.pytorch.org/whl/cpu
```

### 5. Verify the provider, then pre-warm the embedder

```bash
source /root/kalasag/.local/env.sh
cd /root/kalasag/backend
uv run python check_bedrock_connection.py
```

This is the real gate. It exercises the actual model ID and bearer token, not just
network reachability. It must pass before you go further.

Then pull the embedding model down ahead of time. `intfloat/multilingual-e5-small`
(~120 MB) downloads from HuggingFace on first use, and you do not want that
happening during the first demo request:

```bash
uv run python -c "from app.retrieval.embedder import embed_queries; embed_queries(['warm'])"
```

### 6. Run it

Use `tmux`. It survives disconnection and lets you watch the log live during the
presentation, which matters more than you would think when a demo misbehaves.

```bash
tmux new -s kalasag
source /root/kalasag/.local/env.sh
cd /root/kalasag/backend
uv run uvicorn app.main:app --host 0.0.0.0 --port 80
# detach with Ctrl-b then d; reattach with: tmux attach -t kalasag
```

The `source` line is not optional. tmux starts a fresh shell that has never seen
those exports, and without them `uv` is not on `PATH` at all.

`--host 0.0.0.0` is required — uvicorn binds `127.0.0.1` by default, which the port
forward cannot reach. **Do not pass `--reload`**: it watches the filesystem, doubles
memory, and reloads the sentence-transformer on every stray write.

`systemctl` is present on the VM, but the 32050→80 and 32051→22 port forwards
suggest a container allocation, where the binary often exists while systemd is not
PID 1 and every command fails with "system has not been booted with systemd".
Check before relying on it:

```bash
ps -p 1 -o comm=          # 'systemd' means usable; anything else means not
```

If it is real systemd and you want restart-on-crash, this unit is equivalent to the
tmux command. Worth it only if the demo box will be left unattended:

```ini
# /etc/systemd/system/kalasag.service
[Unit]
Description=Kalasag
After=network-online.target

[Service]
WorkingDirectory=/root/kalasag/backend
ExecStart=/root/.local/bin/uv run uvicorn app.main:app --host 0.0.0.0 --port 80
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
systemctl daemon-reload && systemctl enable --now kalasag
journalctl -u kalasag -f
```

## Verify from the Mac

```bash
curl http://altdsidccf.dlsu.edu.ph:32050/api/health
# {"status":"ok"}

curl http://altdsidccf.dlsu.edu.ph:32050/api/meta
# kb_freshness, model_id, chunk_count — confirms it opened the real KB
```

**`chunk_count` must be 732.** That is the real KB. A much smaller number means
`KB_PATH` fell back to `backend/tests/fixtures/kb_fixture.sqlite` and step 3 did not
land the database. The app will still answer plausibly on the fixture, which is why
this check exists — the failure is invisible from the UI.

Then open `http://altdsidccf.dlsu.edu.ph:32050` in a browser and run **one real
analysis end to end**, timing it. Nothing short of a full request proves the
deployment: health and meta never touch the LLM, and the request timeout below is
the risk that a curl cannot see.

## Redeploying after a code change

Rebuild the frontend, rebuild the archive, upload, extract over the top.

```bash
cd /Users/achibukz/Code/GitHub/Elderly-Scam-Shield
cd frontend && npm run build && cd ..
rm -rf backend/static && cp -R frontend/dist backend/static

COPYFILE_DISABLE=1 tar czf ~/Desktop/kalasag-deploy.tgz \
  --exclude='__pycache__' --exclude='.pytest_cache' --exclude='.venv' \
  --exclude='backend/eval/results' \
  backend/app backend/tests backend/eval backend/pyproject.toml backend/uv.lock \
  backend/.env backend/.env.example backend/static backend/check_bedrock_connection.py \
  knowledge-base/out/kb.sqlite docs/DEPLOYMENT.md
```

Upload as in step 3, then on the VM:

```bash
tar xzf /root/kalasag-deploy.tgz -C /root/kalasag    # overwrites in place
```

Extracting over the top never touches `/root/kalasag/.local/` or
`/root/kalasag/backend/.venv/`, since neither is in the archive — so a redeploy
costs one megabyte, not a re-download of torch. Rerun `uv sync` only if a
dependency changed.

Then restart: `tmux attach -t kalasag`, Ctrl-C, rerun the uvicorn line.

**The frontend build is not optional.** The archive ships `backend/static/`, so
skipping `npm run build` silently deploys the previous UI with the new backend.

One caveat of extract-over-the-top: it overwrites and adds but never deletes. If
you *rename or remove* a source file, that stale file lingers on the VM. For a
one-week demo that is harmless; if it ever matters, `rm -rf /root/kalasag/backend/app`
before extracting.

## Storage

Everything lives under `/root/kalasag`. Nothing is installed system-wide, so
`rm -rf /root/kalasag` reclaims all of it.

Measured on this VM: **251 GB total, 131 GB free** (2026-08-06). The deploy needs
roughly 2 GB, so capacity is not a constraint here. Check anyway on any other box:

```bash
df -h /root
du -sh /root/kalasag/*  /root/kalasag/.local/*   # after install, to see the split
```

Estimated footprint with `UV_TORCH_BACKEND=cpu`:

| Path | Size | What |
|---|---|---|
| `backend/.venv` | ~1.2–1.5 GB | torch CPU, transformers, scipy, langchain, fastapi |
| `.local/uv-cache` | ~0.5–1 GB | downloaded wheels — safe to delete after install |
| `.local/uv-python` | ~130 MB | uv's managed CPython |
| `.local/hf` | ~120 MB | `intfloat/multilingual-e5-small` |
| `backend/` + `knowledge-base/` | ~5 MB | app, KB, built frontend |
| **Total** | **~2–2.7 GB** | ~1.7 GB after pruning the wheel cache |

The default CUDA torch build would put this at **5–6 GB** instead. With 131 GB free
that is affordable, so the reason to avoid it is not capacity — it is the extra
~3 GB of download on a campus link, in exchange for a GPU that never runs anything.
See step 4.

To reclaim the wheel cache once everything runs:

```bash
source /root/kalasag/.local/env.sh && uv cache clean
```

Keep it if you expect to redeploy with changed dependencies; a cold cache means
re-downloading torch.

## Risks and gotchas

**Request timeout is the most likely surprise.** An analysis is 3–4 LLM calls at
~20s, so 60–80s end to end in the worst case. If whatever proxies 32050→80 has a
60-second gateway timeout, slow analyses will fail while fast ones succeed — an
intermittent failure that is miserable to debug under presentation pressure. Test a
long message early. If it does time out, the lever is `CONFIDENCE_THRESHOLD` in
`backend/.env`: lowering it makes the reflection pass fire less often, cutting a
whole LLM call off the slow path. Set it from the T18 eval sweep rather than by
guessing.

**The bearer token now sits in plaintext on a shared university machine**, readable
by anyone with root on that box. Rotate `AWS_BEARER_TOKEN_BEDROCK` in the Accenture
sandbox after the presentation.

**The app will be publicly reachable with no authentication.** Anyone who finds the
URL can spend sandbox quota. Bring it down after the demo — `tmux kill-session -t
kalasag`.

**`uv sync` failing on torch** almost always means the Python version is outside
3.13–3.14. Check `uv run python --version`.

**Pipeline invariant 1 survives deployment.** uvicorn's access log records the
request line only, never the body, so raw user input still does not reach the logs.
Do not add `--log-level trace` to debug something; it changes that.

## If Bedrock is unreachable

Not the case on this VM — egress was verified working. Kept for a redeploy onto a
different box, where a blocked egress means the machine cannot run this app at all:
the pipeline is LLM calls end to end and there is no offline mode. Options, best
first:

1. **Ask ALTDSI to allow egress** to `bedrock-runtime.ap-southeast-1.amazonaws.com`
   on 443. Worth an email immediately, since it costs nothing to ask and the answer
   may take days.
2. **Demo from a laptop.** The local setup already works and is what has been
   tested. The VM buys a shareable URL, not a working demo.
3. **Tunnel from a laptop** (`cloudflared tunnel --url http://localhost:8000`) if a
   public URL specifically matters. This gives HTTPS, so the frontend can be
   anywhere.

Do not spend presentation week fighting a firewall. Have the screen recording from
T21 ready regardless.

## Teardown

Do this after the presentation. The app has no authentication and anyone with the
URL can spend sandbox quota.

```bash
tmux kill-session -t kalasag
rm -rf /root/kalasag
```

That is the whole removal — the env-var redirection in step 4 is what makes it
true, since uv and HuggingFace would otherwise have left gigabytes in `~/.cache`
and `~/.local/share`. To confirm nothing leaked:

```bash
du -sh ~/.cache ~/.local 2>/dev/null    # should be near-empty
```

If you installed the systemd unit, `systemctl disable --now kalasag` and delete
`/etc/systemd/system/kalasag.service` too — that is the one file that lives outside
the folder by necessity.

Then rotate `AWS_BEARER_TOKEN_BEDROCK` in the Accenture sandbox — a copy of it sat
in `/root/kalasag/backend/.env` on a shared university machine.

## Docs this touches

Per the doc map in `CLAUDE.md`, applying the static-file change means updating:

- `docs/ARCHITECTURE.md` — `main.py` gains a responsibility (serving the frontend),
  and the single-origin decision belongs in the record.
- `README.md` — a pointer to this file.
- `docs/TASKS.md` — T21 is the runbook task this feeds.
