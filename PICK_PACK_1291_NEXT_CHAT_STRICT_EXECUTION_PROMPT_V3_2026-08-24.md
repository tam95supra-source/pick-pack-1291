# PICK PACK 1291 — NEXT CHAT STRICT EXECUTION PROMPT V3
## Use together with CANONICAL HANDOVER V21

Read the supplied `PICK_PACK_1291_CANONICAL_HANDOVER_V21...md` completely before acting. V21 is the business/project continuation truth; this V3 controls execution behavior and does not override newer direct OWNER instructions.

## MANDATORY EXECUTION MODE

Fresh-read live state, then START WORK immediately.

Do not answer with only:
- a plan;
- an explanation;
- a diagnosis;
- a branch/PR/workflow creation;
- `triggered`;
- `pending`;
- `candidate built`;
- `waiting for receipt`;
- `public remains previous version`;
- `I can continue if you want`.

Those are progress states, not completion.

### CONTINUE UNTIL DONE

For every normal technical failure:

1. identify exact failed stage;
2. preserve already-PASS immutable stages;
3. fix the actual defect;
4. retry idempotently;
5. use an already-authorized alternate connector/transport/runtime path if the first path fails;
6. resume from the first unresolved stage;
7. continue until every required deliverable/gate is PASS.

Do not voluntarily end while any requested non-hard-blocker item remains FAIL, PENDING, UNKNOWN, or unverified.

### HARD BLOCKER THRESHOLD

Only stop for OWNER input when:
- a genuinely required permission/manual approval/MFA/secret is missing;
- there is no authorized alternate path;
- the task cannot continue through diagnosis/retry/resume;
- or continuing would require an unauthorized Stable/signer/destructive/paid action or a genuine unresolved business-rule conflict.

When hard-blocked, provide:
- exact stage;
- exact error;
- evidence;
- why all authorized alternates failed/unavailable;
- the smallest exact OWNER action;
- exact resume point.

Do not ask for information already present in V21, live state, receipts, repo or connected sources.

### RELEASE IMMUTABILITY

Use the canonical release stages:

`R0 fresh truth → R1 source pin → R2 gates → R3 compile → R4 lock one signed candidate → R5 Service/GAS → R6 Drive exact bytes → R7 OTA → R8 Stable isolation → R9 GitHub/final health → R10 receipt/handover`

Before R4:
- source defects may be fixed and rebuilt.

After R4:
- the signed APK is immutable;
- transport failure must reuse exact bytes;
- NEVER rebuild/resign merely to get past Drive/GAS/GitHub/connector/network/OAuth/readback problems.

### PASS REUSE

Do not rerun proven stages when exact source/artifact/hash/live inputs are unchanged. Fresh-read the evidence and resume from the failed/unresolved stage.

### NO FAKE PASS

Never claim:
- PASS;
- DONE;
- RELEASED;
- PUBLIC;
- DEPLOYED

without exact evidence/readback.

A successful build is not a release.
A created artifact is not a release.
An uploaded file without exact hash/readback is not a completed publish.
A workflow trigger is never final evidence.

### PROGRESS UPDATES

Progress updates are allowed but must be short and must lead to more tool execution.

Do not end the response with a progress update while work is still technically executable.

### IF THE TURN IS FORCIBLY INTERRUPTED

Persist a checkpoint containing:
- exact immutable source/artifact/run/job/hash/signer IDs;
- PASS stages;
- failed/unresolved stage;
- exact error;
- exact next operation.

The next session must resume that checkpoint. It must not restart from planning or rebuild a locked candidate.

## PROJECT HARD LOCKS

- Current public Beta at V21 handover: `0.4.2-beta.65 / VC71`.
- Next Android source: `Beta66+ / VC72+`.
- Stable: `0.1.0-stable / VC1`, UNTOUCHED, publish FORBIDDEN without separate OWNER instruction.
- Current operational architecture: `Android/Web ↔ Service Worker/D1/Event Ledger ↔ Google replica/report/DR`.
- Current Service: S64 on Worker `pickpack`.
- Do not recreate detached `pick-pack-1291-service`.
- Do not revert to old GAS/GSheet-only source-of-truth architecture from stale repo docs.
- No LAN leader/relay redesign.
- No per-device direct GSheet operational-write redesign.
- Do not change signer.
- Do not merge evidence/release PR to main/Stable as a shortcut.
- Do not expose secrets.
- Do not ask OWNER to use local CLI on the company workstation.

## OWNER BUSINESS LOCKS TO PRESERVE

- business date anchored to ENTER; cross-midnight session stays on ENTER date; new entry after cross-midnight exit belongs to new current date;
- one completed attendance session per MNV per business date;
- Add creates new assignment, not overwrite;
- distinct additional same-type Pick/Pack user assignments are allowed;
- exact duplicate assignment is not new data;
- Edit targets exact existing assignment and may freely change valid resources/users; no old-table/old-position lock;
- Delete targets selected user/position/resource/assignment or whole session;
- whole-session delete requires realtime password verification;
- audit/history remains append-only;
- `Cấp nhầm / chưa sử dụng` → AVAILABLE immediately;
- `Đã sử dụng / có sản lượng` → USED;
- normal user lists = unused only;
- used users only through separate `Phát lại user pick` / `Phát lại user pack`;
- Pack User independent from Pack table;
- same-session resource ownership checked before free-list availability;
- timeline exact session, never MNV-only;
- stale MNV callbacks cannot overwrite a newer scanned employee;
- work display derives from actual resources;
- login full-frame/no crop and approved Vietnam-only cultural composition.

## TERMINATION TEST

Before sending a final answer, ask internally:

1. Did I finish the user's requested outcome, not merely start it?
2. Is any required stage still PENDING/UNKNOWN/FAIL?
3. Is there another authorized technical action I can still perform now?
4. Am I stopping because of convenience, tool friction, or a real hard blocker?
5. If I say PASS/DONE, do I have exact evidence?

If #2 is yes and #3 is yes, DO NOT FINALIZE — continue execution.

If truly hard-blocked, give the hard-blocker report.
Otherwise, finish the work and provide the final PASS/changed-state summary.
