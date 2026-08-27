# Plan 09 — superseded by the single runner

The separate `aegis` CLI proposal is deferred. It would duplicate the product
entrypoint before the underlying Generate/Defend product is complete.

Use:

```bash
./run.sh          # live e2e, then FastAPI
./run.sh --check  # live e2e, then exit
./run.sh --down   # stop Postgres
```

Query reliability is covered by the reviewed Scout query plan. Durable logging
is specified in [`10-observability-debugging.md`](10-observability-debugging.md).

If a richer CLI is needed later, it should wrap these same product services; it
must not create another e2e implementation.
