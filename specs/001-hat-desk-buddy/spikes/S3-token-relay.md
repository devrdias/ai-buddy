# Spike S3: relaying the handshake access token

**Question**: does the proxy relay `hello.token` unchanged, or must it present the Hermes access token itself?

**Method**: source reading of `plugin/hub.py` and `plugin/adapter.py`, and `docs/connect-hermes.md`. Not yet run against a live
devserver with and without `GADGET_ACCESS_TOKEN`.

**Findings**
- `plugin/hub.py`: when `access_token` is set, the hub rejects any `hello` whose `token` does not match
  (`secrets.compare_digest`) with `bad_token`. `access_token` comes from `GADGET_ACCESS_TOKEN` (or `extra.access_token`),
  read by `plugin/adapter.py`.
- The device sends `token` in `hello` only if it was configured with one. Its value is set on the device, not by the proxy.
- The device identity check (HMAC over the nonce, using the device key) is separate. The hub's `challenge` nonce is relayed
  unchanged, so the HMAC still authenticates the device end to end.

**Answer**: a pure relay works only if the device was configured with the same `GADGET_ACCESS_TOKEN`. Otherwise
the proxy must present the Hermes token in `hello.token`.

**Design change**: the proxy holds the upstream token in its config (`upstream_token`). When it is set, the proxy writes it into
`hello.token` (replacing any device-supplied value). When it is unset, it relays `hello` unchanged. Device identity is still
proven by the relayed HMAC, so the proxy never needs the device key. Update `contracts/gadget-injection.md` relay rule 1 accordingly.

**Security note**: the access token gates network access to the hub. It is not a device credential. The proxy must never log it.

## Live result (2026-10-19): CONFIRMED

- Devserver with `--token s3-secret`:
  - Simulator with no token: rejected, `bad_token: access token missing or wrong`, close code 1008.
  - Simulator with `--token s3-secret`: accepted, `phase: online`, `paired: True`.
- So the hub checks `hello.token` exactly as read from source. A proxy that relays `hello` unchanged only works if the device
  holds the same token. The proxy should set `hello.token` from its own `upstream_token`.
