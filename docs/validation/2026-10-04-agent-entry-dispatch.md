# Fresh contributor entry: dispatch status and remaining gates

This check follows the existing contributor route, building on PR #112's item
brief export. It changes a discovery projection, not task authority, ownership,
capability, review, or membership rules.

## Observed outsider failures

1. `open_work.py --capability ai_tokens_only --json` offered five entries on
   `d15b66f2dc60c6535c631b30ac84154d86e1747a`: WI-010 and four deferred lessons.
   The [lesson definitions](../standards/lessons/README.md) say `deferred` means
   the rule cannot apply yet and its follow-up names a future trigger. Presenting
   those conditions as work a newcomer can take encourages unrelated feature
   creation. The full board should retain them for planning; the capability work
   lane should not turn their trigger into an assignment.
2. A fixture with an `in_progress` item and satisfied prerequisites was still
   offered by the capability board. The complete `--item` brief already requires
   `open` status for readiness. The two entry points disagreed about what a new
   worker can start. This is not a lease claim: contributors may still coordinate
   under the [existing protocol](../contributing/work-items.md).
3. The work-item guide implied a routine verdict alone determined merging.
   [AGENTS.md](../../AGENTS.md) and [start-here.md](../contributing/start-here.md)
   require the actual mandate/review route. The guide now describes those existing
   boundaries consistently; no merge requirement is removed or added.

## Fix and verification

The board preserves `source_status` for work items and lesson dispositions. Its
capability view excludes non-open work items and deferred lessons, after checking
capability and dependencies. `items_not_actionable_by_status` explains those
omissions without double-counting dependency or capability waits. Canonical source records are unchanged; the full board retains unfinished work
and deferred lessons with their statuses visible.

Two regression cases failed before the change and passed afterward. A third case
checks mixed capability, dependency, and status waits; each omitted item counts
once, and filtering leaves the original board unchanged. Markdown exposes source
status rather than implying every row is immediately available.

Reproduce:

```bash
python -m unittest discover -s tests -p test_open_work.py -v
python scripts/open_work.py --json
python scripts/open_work.py --capability ai_tokens_only --json
python scripts/open_work.py --item WI-010 --capability ai_tokens_only --markdown
python scripts/validate_repository.py --json
```

On the checked registry, the narrowed result is one item, WI-010, with four
entries omitted by source status. That is a truthful lack of ready curated
implementation work, not a completed onboarding funnel. WI-010 requires a merged
outside contribution; it does not supply the initial contribution itself.

## Existing work and remaining acceptance

The relevant existing work is [CC-01 #65](https://github.com/Lingkyn/xr-foundry/issues/65)
(exact-next-action discovery), [CC-02 #66](https://github.com/Lingkyn/xr-foundry/issues/66)
(fresh-agent continuation), and the completed entry-route baseline
[WB-03 #41](https://github.com/Lingkyn/xr-foundry/issues/41). This follow-on does not
reopen completed checkpoints, claim their leases, or create another tracker.

A complete outside-contributor exercise still needs:

- a genuine bounded routine Issue or curated open item with complete prerequisites,
  permitted paths, and executable acceptance, selected from actual remaining work;
- an outside identity following the fork route, exporting the item brief and
  contributing revision-bound evidence without private context;
- the required independent human review or applicable mandate route, then a real
  merged result before the WI-010 cold-start receipt can truthfully be completed.

Agent participation remains assistance under an accountable human identity.
[RFC 0006](../rfcs/0006-agent-native-xr-dao.md) is Proposed and inactive at G0 x A0;
[recognition policy](../contributing/recognition-policy.md) requires its future
validated credit checkpoint. A patch, declaration, receipt, or successful test
cannot create membership, voting, permission, credit acceptance, or merge authority.
No external agent was contacted, and no access or governance setting was changed.
