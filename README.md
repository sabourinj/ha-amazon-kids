# Amazon Kids Parent Controls for Home Assistant

An **unofficial** Home Assistant integration that lets you pause and resume
Amazon Kids (child) profiles — e.g. a "disable all screens" button that also
turns off your other devices via your own automations.

It creates one `switch` per child plus a master **All Kids** switch:

- **ON** = child is allowed (normal schedule)
- **OFF** = child is paused (off-screen)

Turning a switch **off** pauses for a default duration; a `pause` service lets
you set a custom duration per call.

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
so **state is optimistic**: Home Assistant shows the state of the last command
it sent. If you change something in the Amazon app directly, HA won't know
until the next command. Entities are marked `assumed_state`.

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

Enter children as a JSON list:

```json
[
  {"name": "Alex", "directed_id": "amzn1.account.AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"},
  {"name": "Sam",  "directed_id": "amzn1.account.BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB"}
]
```

### When it stops working

If pauses start failing, your session expired. Re-harvest the `Cookie` and
`x-amzn-csrf` values and reconfigure the integration. This is the most common
maintenance task.

## Usage

- Toggle any child switch, or the **All Kids** switch, from the UI or automations.
- Custom duration:

```yaml
service: amazon_kids.pause
target:
  entity_id: switch.all_kids
data:
  minutes: 120
```

- Resume: `service: amazon_kids.resume` with the same target.

### Example "disable everything" script

```yaml
alias: Disable all screens
sequence:
  - service: amazon_kids.pause
    target:
      entity_id: switch.all_kids
    data:
      minutes: 180
  - service: media_player.turn_off
    target:
      entity_id: media_player.living_room_tv
  # + your router/firewall action for the Switch, etc.
```

## Limitations / roadmap

- **Optimistic state only.** No known "is paused" read endpoint. PRs welcome if
  you find one.
- **No auto-discovery of children.** IDs are entered manually. A household/roster
  endpoint may exist; contributions welcome.
- **Amazon may cap very long durations.** Long pauses are clamped to 24h; to
  "pause until resumed" you'd re-issue periodically (not yet automated).

## Contributing

Issues and PRs welcome — especially traffic captures (with **all** cookies,
tokens, names and child IDs redacted) that reveal a state-read or roster
endpoint.

## Security & privacy

- Credentials are stored in your Home Assistant config entry and sent only to
  `parents.amazon.com`. They are never transmitted anywhere else.
- Never commit a HAR file or your cookie/CSRF token to a public repo.

## License

MIT. See [LICENSE](LICENSE).
