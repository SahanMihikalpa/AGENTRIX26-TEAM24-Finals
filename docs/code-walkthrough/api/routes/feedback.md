# `api/routes/feedback.py` — Experience-report route

**Layer:** api/routes · **Stage:** 6b · FR-6

## 🎯 කාර්යය
`POST /api/experience-reports` — පුරවැසි post-visit report එකක් file කරනවා → persist + best-effort B2→B3.

## 🔍 Code Walkthrough
`submit_experience_report(request, runtime)`:
1. `service_id`/district නැත්නම් **session එකෙන් resolve** (`session_values` — conversation එක ගැන වුණ
   service එකට report එක tie වෙනවා).
2. `ExperienceReport(status=PENDING, created_at=now UTC)` හදලා `runtime.experience_intake.submit(report)`.
3. `201` + `{id, status}`.

## 🔗 සම්බන්ධතා
[`ExperienceReportIntake`](../../application/feedback.md) use case, [session_state](../session_state.md),
[dto](../dto.md).

## 💡 Design decision
Route එක thin — persist + ingest **policy** use case එකේ. Session-resolution නිසා frontend එකට service_id
manually යවන්න වෙන්නේ නෑ.
