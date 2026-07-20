# Amazon Kids Parent Controls for Home Assistant

An **unofficial** Home Assistant integration that lets you pause and resume
Amazon Kids (child) profiles — e.g. a "disable all screens" button that also
turns off your other devices via your own automations.

It creates one HA **device per child** (named after the child, e.g. "Alex"),
plus an **All Kids** device, each with:

- A **Pause** and a **Resume** button — these just fire the command; Amazon
  gives no way to read back whether a child is actually paused right now, so a
  button is the honest representation (a `switch` would imply state this
  integration can't verify). Shown in HA as e.g. `Alex Pause`, `All Kids Resume`.
- A **Status** sensor showing `allowed` / `paused` (or, for All Kids,
  `all_allowed` / `all_paused` / `mixed`) reflecting the *last command this
  integration issued* — not verified truth. See "How it works" below.
- A **Pause Duration** number (minutes) — buttons can't prompt for input when
  pressed, so this is what pressing **Pause** actually uses: set it once, or
  dial it up/down right before pressing Pause. Persists across restarts.

Pressing **Pause** uses that entity's current value; the `pause` service lets
you override it with a one-off custom duration per call instead, without
changing the number entity's saved value.

> ⚠️ **This uses Amazon's private, undocumented endpoints.** There is no public
> API. It can break at any time if Amazon changes their dashboard, and it may
> violate Amazon's Terms of Service. Use at your own risk. This project is not
> affiliated with or endorsed by Amazon.

---

## How it works

Amazon's Parent Dashboard (`parents.amazon.com`) pauses a child by calling:

```
POST /ajax/set-offscreen-time
{ "directedIds": ["<child id>"], "expirationTimeInSeconds": 3600 }
```

`expirationTimeInSeconds` > 0 pauses for that many seconds; `-1` resumes. The
endpoint accepts multiple IDs, so pausing all children is a single request.

No endpoint has been found that reports whether a child is *currently* paused,
so pause/resume are exposed as **button** entities (press = fire the command,
no state implied) rather than switches. The **Status** sensor(s) show the last
command this integration issued — if you change something in the Amazon app
directly, HA won't know until the next button press.

## Installation (HACS)

1. HACS → Integrations → three-dot menu → **Custom repositories**.
2. Add this repo URL, category **Integration**.
3. Install **Amazon Kids Parent Controls**, then restart Home Assistant.
4. Settings → Devices & Services → **Add Integration** → *Amazon Kids*.

## Getting your credentials

You supply two secrets and your children's IDs. **Treat the cookie and CSRF
token like a password** — they grant access to your family dashboard until the
session expires.

1. Log in at <https://parents.amazon.com> in a desktop browser.
2. Open DevTools (F12) → **Network** tab → filter **Fetch/XHR**.
3. Click any control (e.g. adjust a time limit) so a request to
   `/ajax/...` appears. Click it.
4. From **Request Headers**, copy:
   - the full **`Cookie`** value → *Cookie header value* field
   - the **`x-amzn-csrf`** value → *x-amzn-csrf token* field
5. Find each child's `directedId`: it appears as the `childDirectedId` query
   param on calls like `get-adjusted-time-limits?childDirectedId=amzn1.account.XXXX`.

The setup wizard collects these in two steps: credentials once, then each
child one at a time (name + directedId, with a checkbox to add another) —
no JSON to hand-write. Each child's name becomes that child's device/entity
name in HA.

### When it stops working

If pauses start failing, your session expired. Re-harvest the `Cookie` and
`x-amzn-csrf` values and reconfigure the integration. This is the most common
maintenance task.

## Usage

- Adjust `number.alex_pause_duration` (or `number.all_kids_pause_duration`) to
  set how long the next press pauses for, then press **Pause**. Both live
  under the same device, so they show up together in the UI.
- Press any child's **Pause**/**Resume** button, or the **All Kids** versions,
  from the UI or automations.
- One-off custom duration without touching the number entity's saved value —
  target the Pause button entity directly:

```yaml
service: amazon_kids.pause
target:
  entity_id: button.all_kids_pause
data:
  minutes: 120
```

- Resume: `service: amazon_kids.resume` targeting `button.all_kids_resume` (or
  a child's own Resume button).

### Example "disable everything" script

```yaml
alias: Disable all screens
sequence:
  - service: amazon_kids.pause
    target:
      entity_id: button.all_kids_pause
    data:
      minutes: 180
  - service: media_player.turn_off
    target:
      entity_id: media_player.living_room_tv
  # + your router/firewall action for the Switch, etc.
```

## Limitations / roadmap

- **No verified state, only last-commanded state.** The Status sensors reflect
  what this integration last told Amazon, not a read-back. No known "is
  paused" read endpoint exists; PRs welcome if you find one.
- **Upgrading from a version with switch entities?** The `switch.*` entities
  are gone (replaced by `button.*` + `sensor.*`); remove the old ones from
  Settings → Devices & Services → Entities, they'll show as unavailable.
- **No auto-discovery of children.** IDs are entered manually. A household/roster
  endpoint may exist; contributions welcome.
- **Amazon may cap very long durations.** Long pauses are clamped to 24h; to
  "pause until resumed" you'd re-issue periodically (not yet automated).

## Contributing

Issues and PRs welcome — especially traffic captures (with **all** cookies,
tokens, names and child IDs redacted) that reveal a state-read or roster
endpoint.

### Releasing a new version

HACS shows users a real version number (rather than a commit hash) only when
a GitHub Release exists for it. To cut one:

1. Bump the version **in lockstep** in all four places (nothing reads this
   automatically, so a mismatch here is easy to miss):
   - `custom_components/amazon_kids/manifest.json` (`version`)
   - `pyproject.toml` (`[project] version`)
   - `amazonkids/__init__.py` (`__version__`)
   - `custom_components/amazon_kids/amazonkids/__init__.py` (`__version__`,
     the vendored copy)
2. Commit that as its own change (e.g. `Bump version to 0.3.0`) and merge it
   to `main`.
3. Tag the merge commit and push the tag: `git tag v0.3.0 && git push origin v0.3.0`.
4. Create a GitHub Release from that tag (Releases → Draft a new release →
   pick the tag) summarizing what changed since the last release.

Follow [semver](https://semver.org/): this project is pre-1.0, so breaking
changes (e.g. renaming/removing entities) are fine as a minor bump.

## Security & privacy

- Credentials are stored in your Home Assistant config entry and sent only to
  `parents.amazon.com`. They are never transmitted anywhere else.
- Never commit a HAR file or your cookie/CSRF token to a public repo.

## License

MIT. See [LICENSE](LICENSE).
