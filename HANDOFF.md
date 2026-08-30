# RouteMind Handoff

Last Known Commit: Current `HEAD`; resolve with `git rev-parse HEAD`

Current Branch: main

Current Phase: Round 4 Final Closure - ACTIVE

Current Task: R4-422 - GMAIL V2 SEND PREFLIGHT FAILED (CREDENTIAL REFRESH REQUIRED)

R4-422 Gmail refresh-if-required single-send preparation (2026-08-30): a new
independent contract
`contracts/provider/r4-422-google-gmail-refresh-if-required-single-send-v1.json`
is frozen at canonical SHA-256
`35702d6d6698b78f08757b2560deb2bfee50503d0b8cc90b8fd2fcdf9431535f`.
Preparation is offline-only and made zero Gmail API requests, zero
`users.messages.send` requests, zero token refresh requests, zero OAuth,
browser, SSH, email, retry, fallback, read, recipient, and mutation
operations. The Java executor uses one loaded credential object, refreshes at
most once only when readiness requires it, reassesses that same object, then
uses a fixed post-refresh token snapshot for at most one synthetic send. Any
refresh or send failure stops closed. Historical Gmail contracts and evidence
are explicitly preserved, immutable, and non-reusable. Contract, Java focused
tests, security, and leakage checks passed; no provider, delivery, or
production claim is made. Evidence:
`evidence/gates/R4-422/google-gmail-refresh-if-required-single-send-preparation-20260830.*`.
R4-422 remains `BLOCKED / HUMAN_GATE_PENDING`; no execution command was run.

R4-422 Gmail V2 approved execution (2026-08-30): contract
`contracts/provider/r4-422-google-gmail-single-send-validation-v2.json` at exact
SHA-256 `033bd4e5e3c92b65d94191a30fcae7d852dc92ae7441ef18c8bf8f959cba371f` was
validated before execution. The stored credential loaded from the external
Windows token store but currently requires refresh. The approved contract has
`FAIL_IF_REQUIRED` and zero refresh allowance, so execution stopped before any
Gmail request. Gmail API and `users.messages.send` requests, credential refreshes,
OAuth sessions, token exchanges, browser/SSH sessions, retries, fallback, email
sends, mutations, and cost are all zero. No provider, delivery, or production
claim is made. Evidence and leakage scan:
`evidence/gates/R4-422/google-gmail-single-send-v2-execution-preflight-20260830.*`.
The contract is consumed fail-closed and cannot be retried or reused; a new
independent refresh or send Human Gate is required. Historical evidence and the
R3-325 frozen result remain unchanged.

R4-422 Gmail V2 exactly-one send contract preparation (2026-08-30): a new
independent contract
`contracts/provider/r4-422-google-gmail-single-send-validation-v2.json` is
prepared with canonical SHA-256
`033bd4e5e3c92b65d94191a30fcae7d852dc92ae7441ef18c8bf8f959cba371f`.
It freezes exactly one synthetic Gmail API v1 `users.messages.send` request
to one recipient with `gmail.send` only, zero credential refreshes, OAuth
sessions, token exchanges, browser/SSH sessions, retries, fallback, reads,
attachments, CC/BCC, batch operations, or Google/account/resource mutations.
The repository-external Windows token store must load a current credential
without refresh; a refresh requirement is a fail-closed preflight result and
cannot produce a Gmail request under this contract. The adapter remains
disabled by default. Preparation made zero Gmail/API/OAuth operations and
cost `USD 0.00`; redacted evidence and leakage scan are under
`evidence/gates/R4-422/google-gmail-single-send-v2-preparation-*`.
Historical contracts, failures, and the successful refresh evidence remain
unchanged. R4-422 remains `BLOCKED / HUMAN_GATE_PENDING` with no provider,
delivery, or production claim. Exact Human Gate approval sentence: “I approve
R4-422 Google Gmail V2 exactly-one synthetic live send validation by exact
SHA-256 digest 033bd4e5e3c92b65d94191a30fcae7d852dc92ae7441ef18c8bf8f959cba371f,
authorize exactly one users.messages.send request to one synthetic recipient
with gmail.send only and the existing repository-external Windows token store
after the approved credential refresh, zero credential refreshes/OAuth
sessions/token exchanges/browser/SSH, zero retries/fallback, no
attachments/CC/BCC/batch/reads, no Google/account/resource mutation, within
15 minutes and USD 0.10, and accept sanitized evidence and fail-closed
semantics without a production claim.”
Preparation commit `b305df2` passed real GitHub Actions run `33266756073` with
all five required jobs green.

R4-422 Gmail credential refresh-only recovery execution (2026-08-30): the
approved contract
`contracts/provider/r4-422-google-gmail-token-refresh-recovery-v1.json` was
consumed at SHA-256
`6c2b454101787c72459b3a5a7f01c18b25cf09d19ffd8ed90aaf3044e8b4b39f`.
The existing external credential refresh completed successfully with exactly
one token refresh request and one token response. No Gmail API request, email,
OAuth session, authorization-code exchange, browser, SSH, retry, fallback, or
Google/account mutation occurred. Elapsed time was 1345 ms and observed cost
was `USD 0.00`. Evidence is append-only under
`evidence/gates/R4-422/google-gmail-token-refresh-recovery-execution-*` with a
passing leakage scan. Credential refresh is validated, but Gmail connectivity,
message operation, delivery, and production claims remain false. The consumed
contract cannot be reused; a new independent Gmail send contract and Human
Gate are required. R3-325 remains frozen as
`E-PASS / X-PASS / S-FAIL / C-NO-CLAIM`. Counts remain 167/197 overall and
10/38 in Round 4.
Execution checkpoint commit `c08f1e0` passed real GitHub Actions run
`33265482119` with all five required jobs green.

R4-422 Gmail credential refresh-only recovery preparation (2026-08-29): new
contract `contracts/provider/r4-422-google-gmail-token-refresh-recovery-v1.json`
has canonical SHA-256
`6c2b454101787c72459b3a5a7f01c18b25cf09d19ffd8ed90aaf3044e8b4b39f` and is
`PREPARED_OFFLINE / HUMAN_GATE_PENDING`. The existing repository-external
Windows token store is present and available; the stored credential loads
through the standard Google library, its metadata requires refresh, and the
refresh capability is available. The preparation command did not invoke
refresh, OAuth, authorization-code, browser, SSH, Gmail API, email, retry,
fallback, or mutation (`0` each; cost `USD 0.00`). No token, client secret,
authorization header, raw response, address, message body, or external path was
persisted. The Gmail adapter remains disabled by default, historical contracts
remain immutable, and R3-325 remains `E-PASS / X-PASS / S-FAIL / C-NO-CLAIM`.
Evidence: `evidence/gates/R4-422/google-gmail-token-refresh-recovery-preparation-*`.
Exact next human action: approve the new digest with one existing-credential
refresh only; on success or failure stop and require a separate new Gmail send
contract/Human Gate for any message operation. Counts remain 167/197 overall
and 10/38 for Round 4.
Preparation commit `3f11bd3` passed real GitHub Actions run `33262190380` with
all five required jobs green.

R4-422 Gmail single-send preflight closure (2026-08-29): exact contract digest
`16e6f9dd68fd261f28047b0e7ea8e2f19e186ba3c04dd68c7c8a7d3606dea663`
was approved and consumed fail-closed. The external Windows token-store path
and local credential load were available, but the stored access credential
requires an OAuth token refresh. Refresh/token exchange was not authorized, so
the executor stopped before any Gmail call. Gmail API and
`users.messages.send` requests, recipients attempted, email sends, OAuth,
token exchanges, browser, SSH, retries, fallback, mutations, and cost are all
zero. No secret, raw address, message content, provider response, or external
path was recorded. State is `PREFLIGHT_FAILED_NO_CALL / NO_PROVIDER_CLAIM`.
Exact next human action: authorize a new independent bounded OAuth refresh or
reauthorization contract; after credential readiness is restored, approve a
new independent exactly-one Gmail send contract. Do not reuse this digest.
Evidence: `evidence/gates/R4-422/google-gmail-single-send-preflight-failure-*`.
Evidence checkpoint `20641e4e707a57b57877fec465e80d1e73f5ab22` passed real
GitHub Actions run `33260439288` with all five required jobs green.

R4-422 active-provider replacement checkpoint (2026-08-29): the R4-422 domain
task is provider-neutral, so AWS SES remains a preserved historical
`BLOCKED / FAILED_PROVIDER_REJECTED / NO_PRODUCTION_CLAIM` outcome and is not
recast as a pass. AWS SES has been removed from active Java runtime wiring;
`GoogleGmailNotificationProvider` is the active email-provider candidate behind
the existing `NotificationProvider` port. The adapter is disabled by default,
uses only OAuth scope `https://www.googleapis.com/auth/gmail.send`, separates
bootstrap/token loading from invocation, creates UTF-8 RFC 2822 URL-safe
Base64 messages, normalizes sanitized status/reason outcomes, and performs no
automatic retry or fallback. The offline checkpoint made zero AWS calls, zero
Google calls, zero OAuth consent actions, zero credential-store mutations, and
zero email sends. Future Gmail validation is prepared in
`contracts/provider/r4-422-google-gmail-live-validation-v1.json` with canonical
SHA-256
`bc05c17490bcf1be3bd444ead6a68e941b29b0a09d71842283b228f8c5a811f1`; it remains
behind a new Human Gate and makes no Tokyo-processing claim. Evidence:
`evidence/gates/R4-422/gmail-provider-replacement-20260829.md`, its JSON index,
and the passing leakage scan. R3-325 remains frozen as
`E-PASS / X-PASS / S-FAIL / C-NO-CLAIM`. Java 17 full tests (126), control
plane gates, and `verify.ps1` pass locally; the Google HTTP JSON runtime is
aligned at `google-http-client-jackson2:1.46.3`.
Commit `c35306bc3fef51a0d624c55a36fa7a7fbc0b296a` passed real GitHub Actions
run `33244023747` with all five required jobs green.

Gmail OAuth bootstrap preparation (2026-08-29): an explicit
`scripts/gmail-oauth-bootstrap.ps1` command and Java bootstrap boundary are
prepared but not executed. The command requires the non-secret environment
variables `ROUTEMIND_GMAIL_OAUTH_CLIENT_FILE`, `ROUTEMIND_GMAIL_TOKEN_STORE`,
and `ROUTEMIND_GMAIL_OAUTH_USER_ID`; client JSON and token material remain in
existing repository-external locations. Canonical absolute path validation
rejects repository-contained files and redirecting links. The official OAuth
flow is limited to `https://www.googleapis.com/auth/gmail.send`, a loopback
`127.0.0.1` ephemeral redirect, one operator-controlled consent session, and
one token exchange. The command is explicit, never runs at startup/CI/resume,
and cannot send Gmail messages. No Google request, OAuth consent, token
exchange, Gmail send, Google Cloud mutation, AWS request, or credential-store
mutation occurred. New bootstrap contract:
`contracts/provider/r4-422-google-gmail-oauth-bootstrap-v1.json`, SHA-256
`ca3c1974b846f83846724091416f41bc431d51d9e26f1bfcdaac2b05c0ab9284`; it is
independent of the existing Gmail send contract and remains
`HUMAN_GATE_PENDING`. Evidence:
`evidence/gates/R4-422/gmail-oauth-bootstrap-preparation-20260829.md` and its
JSON/leakage companions. Counts remain 167/197 overall and 10/38 for Round 4.

Repair commit `8e0af27c0843ad6417d73ffb75bddd40dd5da3e0` passed real GitHub
Actions run `33245414841` with all five required jobs green.

Cross-device Gmail OAuth bootstrap preparation (2026-08-29): the existing
loopback-only bootstrap contract remains immutable and does not cover a Mac
browser or an SSH network boundary. A separate Windows-initiated `ssh -R`
path is prepared for exactly one strict connection to `suzhe@10.10.1.27`.
Windows listens only on `127.0.0.1:<windows-port>`; the Mac-side remote
listener is only `127.0.0.1:<mac-port>` and forwards to the Windows loopback.
The Mac performs login/consent, while Windows performs the sole token exchange
and persists tokens only in the external Windows token store. Strict
`known_hosts`, `StrictHostKeyChecking=yes`, `CheckHostIP=yes`,
`IdentitiesOnly=yes`, `BatchMode=yes`, `ExitOnForwardFailure=yes`, and a
`PermitRemoteOpen` loopback destination are required. Wildcards, `GatewayPorts`,
`-g`, remote commands, extra forwards, token transfer, Gmail message
operations, and email sends are forbidden. New contract:
`contracts/provider/r4-422-google-gmail-oauth-remote-forward-bootstrap-v1.json`,
SHA-256
`2ef914d10c541f800a61107bc521f3edbfcec05b608b8dc52c6c65bcd102c629`; it is
independent of the prior contract and remains `HUMAN_GATE_PENDING`. No SSH,
OAuth, Google, Gmail, or mutation operation occurred. Evidence:
`evidence/gates/R4-422/gmail-oauth-remote-forward-bootstrap-preparation-20260829.md`
with JSON and leakage companions. Counts remain 167/197 overall and 10/38 for
Round 4.

Cross-device Gmail OAuth execution (2026-08-29): the approved contract
`contracts/provider/r4-422-google-gmail-oauth-remote-forward-bootstrap-v1.json`
with SHA-256
`2ef914d10c541f800a61107bc521f3edbfcec05b608b8dc52c6c65bcd102c629` was
consumed for exactly one operator-controlled session. Mac consent completed,
but the callback to `127.0.0.1:52817` returned `ERR_CONNECTION_REFUSED`.
Read-only inspection found no listener on the Windows callback port and no
active Java/SSH process; remote-forward establishment and liveness at callback
time are therefore unconfirmed. No authorization code was captured or stored,
and no token exchange, Google API request, Gmail message request, or email send
occurred. Token-store metadata was unchanged during the attempt; contents were
not read. The result is `INCOMPLETE_CONSUMED / DIAGNOSTIC_INCOMPLETE` with
`NO_RETRY`; any future bootstrap needs a new contract and Human Gate. Evidence:
`evidence/gates/R4-422/gmail-oauth-remote-forward-execution-20260829T111824Z.json`
and `evidence/gates/R4-422/gmail-oauth-remote-forward-execution-closure-20260829T111824Z.md`.
The execution checkpoint commit `0c09da62f873713f076b7b010ba34e0982b5df51`
passed real GitHub Actions run `33250008179` with all five required jobs green.

Password-authenticated remote-forward preparation (2026-08-29): the consumed
key-based contract is preserved and not reused. A new independent contract is
prepared at
`contracts/provider/r4-422-google-gmail-oauth-password-remote-forward-v1.json`
with SHA-256
`3c8cb8104cad351b74620f68fa02129c516a46a458401ae78a909b3879aec215`.
It fixes `suzhe@10.10.1.27`, strict external `known_hosts`, one loopback-only
remote forward, and native Windows interactive password authentication with
public-key/key-file options disabled. The operator types the password directly
in the Windows terminal; Codex and Java never access or persist password bytes.
Only one synthetic localhost probe is authorized in this stage; OAuth,
authorization-code handling, token exchange, Gmail operations, and email sends
are explicitly forbidden and remain zero. No SSH or synthetic traffic has been
executed. Preparation evidence is under
`evidence/gates/R4-422/gmail-oauth-password-remote-forward-preparation-20260829.*`
with a passing leakage scan. State: `PREPARED_OFFLINE / HUMAN_GATE_PENDING /
SYNTHETIC_ONLY / NO_OAUTH`.

Password-authenticated remote-forward synthetic execution (2026-08-29): exact
Human Gate contract `3c8cb8104cad351b74620f68fa02129c516a46a458401ae78a909b3879aec215`
was consumed once. One Windows native `ssh.exe` process was launched for
`suzhe@10.10.1.27` with strict external `known_hosts` and loopback-only
forwarding, but it exited with code `1` before any synthetic request. SSH
connection and forward establishment are unconfirmed and no detailed SSH
diagnostics were retained. Password data was never read or captured by
Codex/Java. No synthetic request, OAuth session, token exchange, Google/Gmail
request, or email send occurred. Teardown stopped the listener and SSH process;
no resources or credential stores changed; cost was USD `0.00`. The result is
`INCOMPLETE_CONSUMED / DIAGNOSTIC_INCOMPLETE / NO_RETRY` with root cause
`UNKNOWN_SSH_EXIT_WITHOUT_RETAINED_DIAGNOSTICS`; no retry or OAuth stage is
authorized without a new contract and Human Gate. Evidence:
`evidence/gates/R4-422/gmail-oauth-password-remote-forward-execution-20260829T115910Z.json`,
its closure markdown, and its redacted leakage scan. Historical key-based
contract/evidence remain unchanged.

R4-422 SES IAM authorization semantics differential audit (2026-08-29):
read-only AWS Console and official-documentation audit completed with verdict
`AUTHORIZATION_MODEL_VALID_NO_STATIC_CAUSE_FOUND` (medium confidence). The
current inline IAM policy semantically allows `ses:SendEmail` and
`ses:SendRawEmail` on the exact verified identity ARN in `ap-northeast-1`, with
case-sensitive `ses:FromAddress`, multivalued `ForAllValues:StringEquals
ses:Recipients`, and `aws:SecureTransport=true`. SES's Service Authorization
Reference supports the required identity resource and condition keys. The
Console showed two Tokyo identities as verified, a healthy sandbox account,
and no permissions boundary. Same-account sending does not require delegated
`SourceArn`/`FromArn`/`ReturnPathArn` fields. AWS's IAM Policy Simulator only
evaluates the policies and context supplied to it, returns a binary IAM
decision, makes no service request, and returns no service response; AWS warns
that simulator and live results can differ. The stable real SES `AccessDenied` /
HTTP 403 therefore remains narrowed to an unobserved SES service-side or
request-context authorization difference; no exact documented static cause,
adapter defect, or policy defect was found. No IAM/SES/AWS mutation or SendEmail
request occurred, and all historical R4-422 evidence remains unchanged.
Offline analytical model tests pass 7/7. Evidence:
`evidence/gates/R4-422/aws-ses-iam-authorization-semantics-differential-audit-20260829.md`
and `evidence/gates/R4-422/aws-ses-iam-authorization-semantics-differential-audit-20260829.json`.
`FOURTH_SENDEMAIL_CURRENTLY_JUSTIFIED = NO`.

R4-422 third AWS SES single-send diagnostic execution (2026-08-29): exact
Human Gate approval consumed contract
`contracts/provider/r4-422-aws-ses-third-single-send-diagnostic-v1.json` at
SHA-256
`6c52a2457b4d136f17d11e66af15cf9a1a79a721bc8558cca68658f728ed4387`. The
hardened `AwsSesRequestFactory` -> `AwsSesNotificationProvider` -> AWS SDK v2
`SesClient.sendEmail` path passed all local preconditions and dispatched exactly
one request. AWS returned sanitized `AccessDenied` with HTTP 403 and a redacted
request-ID presence; this is classified `FAIL_PROVIDER_REJECTED` /
`AUTHORIZATION_REJECTED`. Credential-chain resolution and client construction
were available, retries and fallback were zero, no message ID or authenticated
delivery receipt was returned, and no email, IAM, account, provider, or resource
mutation occurred. Observed spend is USD 0.00 with a conservative USD 0.10
bound; billing readback was not performed. R4-422 remains
`BLOCKED / FAILED_PROVIDER_REJECTED / NO_PRODUCTION_CLAIM`; another live attempt
requires a new contract and Human Gate. Append-only redacted evidence:
`evidence/gates/R4-422/aws-ses-third-single-send-execution-20260829T071645Z.json`,
`evidence/gates/R4-422/aws-ses-third-single-send-usage-20260829T071645Z.json`,
`evidence/gates/R4-422/aws-ses-third-single-send-leakage-scan-20260829T071645Z.json`,
and `evidence/gates/R4-422/aws-ses-third-single-send-execution-closure-20260829T071645Z.md`.
Historical first/second contracts and evidence are unchanged. R3-325 remains
frozen as `E-PASS / X-PASS / S-FAIL / C-NO-CLAIM`.

R4-422 third AWS SES single-send diagnostic preparation (2026-08-29): new
independent contract
`contracts/provider/r4-422-aws-ses-third-single-send-diagnostic-v1.json` is
prepared with canonical SHA-256
`6c52a2457b4d136f17d11e66af15cf9a1a79a721bc8558cca68658f728ed4387`. It allows
exactly one synthetic `SendEmail` request in `ap-northeast-1`, exactly one
verified synthetic recipient, zero retries, zero fallback, 15 minutes, and
USD 0.10. Any future execution must use the hardened
`AwsSesRequestFactory` / `AwsSesNotificationProvider` path and sanitized error
observation; historical ad-hoc execution is forbidden. Preparation performed
zero AWS/external requests, zero mutations, and zero cost. The consumed first
and second contracts and all historical evidence are unchanged. R4-422 remains
`BLOCKED / FAILED_PROVIDER_REJECTED / NO_PRODUCTION_CLAIM` pending the exact new
Human Gate. Evidence is under
`evidence/gates/R4-422/aws-ses-third-single-send-diagnostic-preparation-20260829.md`
with linked JSON and leakage scan. Dedicated contract validation and five
regression tests pass locally; no credentials were resolved and no browser or
network endpoint was used.

R4-422 offline runtime-context and error-observability checkpoint (2026-08-29):
the real production request builder now enforces the bounded configured sender
and synthetic recipient, constructs exactly one To recipient with no CC/BCC or
unexpected optional/delegated fields, and uses an AWS SDK no-retry strategy.
The current process values have no whitespace, display-name, Unicode, or case
normalization anomaly, but no independent approved value or historical raw value
exists. Therefore the current comparison is `COMPARISON_INPUT_UNAVAILABLE`, the
historical context is `HISTORICAL_CONTEXT_NOT_RECONSTRUCTABLE`, and root cause
remains `INCONCLUSIVE`. Structured future error observations retain safe error
code, HTTP status, request-ID presence only, normalized semantics, counts,
timestamp, and request shape; raw messages and sensitive identifiers are excluded.
No external request, credential resolution, AWS mutation, contract creation, or
send occurred. Historical evidence is unchanged and R4-422 remains
`BLOCKED / FAILED_PROVIDER_REJECTED / NO_PRODUCTION_CLAIM`. See
`evidence/gates/R4-422/aws-ses-runtime-context-observability-offline-audit-20260829.md`.
Focused SES tests pass 16/16, the broader Java suite passes 136/136, and the
repository verify, control-plane, Round 4 graph, and security gates pass. The
standalone contract validator is independently unavailable because `jsonschema`
is absent from the current local Python environment; it is not treated as an SES
runtime failure.

R4-422 second single-send contract preparation (2026-08-29): new contract
`contracts/provider/r4-422-aws-ses-second-single-send-validation-v1.json` is
prepared with canonical SHA-256
`9c32cc9df3ac34e2a85f722ec2bcce6c64e9e5057a2f9e85e0e14656c082feaa`. It is
limited to one synthetic `SendEmail` request, one recipient, zero retries,
15 minutes, and USD 0.10 in `ap-northeast-1`. No AWS call, email, mutation, or
cost occurred during preparation. R4-422 remains `BLOCKED / HUMAN_GATE_PENDING`;
the prior consumed contract and failure evidence are unchanged.
Real GitHub Actions CI run `33233038421` passed all five required jobs.

R4-422 second single-send execution (2026-08-29): the exact approved contract
`9c32cc9df3ac34e2a85f722ec2bcce6c64e9e5057a2f9e85e0e14656c082feaa` was
consumed with exactly one AWS SES `SendEmail` request. The provider returned
normalized `AccessDenied` (`SesException`); no retry, fallback, second request,
email delivery, message ID, or delivery receipt occurred. Local credential
resolution and SES client construction were available before the request.
Observed cost is USD 0.00 with a conservative USD 0.10 bound; no AWS account,
IAM, provider configuration, or resource mutation occurred. Redacted,
append-only execution, usage, closure, and leakage evidence is under
`evidence/gates/R4-422/`, and the execution leakage scan passed. R4-422 remains
`BLOCKED / FAILED_PROVIDER_REJECTED / NO_PRODUCTION_CLAIM`; any subsequent
attempt requires a new contract and Human Gate. Preparation CI run
`33233157325` passed all five required jobs, and execution closure commit
`e5bed13` passed all five required jobs in real GitHub Actions run
`33234378913`. The local `verify.ps1` run reached the Compose configuration
check but Docker Desktop did not respond; that environmental failure is not
represented as a pass.

R4-422 local SES runtime repair (2026-08-29):
`BLOCKED / LOCAL_RUNTIME_REPAIRED_AWAITING_NEW_CONTRACT`. The consumed digest
`e942a04b080da7cf42645d757fec61a1fb67428b59da29f90c93227b06c7d660`
and its prior fail-closed evidence are unchanged. The root cause was the
diagnostic JShell launcher's manually assembled classpath omitting
`org.reactivestreams.Publisher`; the production Maven graph was already complete
and aligned at AWS SDK `2.31.77`, with `reactive-streams:1.0.4`, SLF4J `2.0.18`,
and runtime HTTP clients present. `scripts/business-api.ps1 -Action ses-offline`
now uses the repository Maven runtime and stops after local credential-chain
resolution and `SesClient` construction/close. The focused test passes, the
full 125-test Java suite passes, and AWS/SES/email/mutation/cost counters remain
zero. No production dependency changed and no live contract was prepared.
Evidence is under `evidence/gates/R4-422/aws-ses-runtime-repair-20260829.md` and
the linked JSON/dependency-tree artifacts. Any future send requires a new exact
contract and a new Human Gate. Real GitHub Actions CI run `33232296372` passed
all five required jobs.

RM-237 Research Observability checkpoint (2026-08-29): `PASSED /
FUTURE_DATA_READY / OBSERVABILITY_READY`. It is a single independent
research-enabling task with dependencies RM-003, RM-205, RM-233, and RM-234;
it is not attached to Round 4 external execution. Python owns versioned
tick-level policy/switch observations, replay digests, semantic classes,
redaction, and `ROUTEMIND_DATA_ROOT` JSONL export. Java owns optional metadata
on the dispatch command, idempotency fingerprint, transactional Outbox
provenance, and durable ledger columns. Schema/version is
`routemind-policy-observation-v1`; missing measurements remain unavailable and
no causal switch-cost claim is made. Compute 950 tests/95.10%, Java 125 tests,
contract/replay/control-plane/verify gates all pass locally. No empirical data,
historical backfill, external API call, production claim, Human Gate change, or
R3-325 mutation occurred. Evidence: `evidence/gates/RM-237/` and
`research/observability/`. The existing R4-422 Human Gate remains the current
external boundary and no safe next task is eligible. Checkpoint commit
`37bf50711057da9fa4f34f09af56838d951dc1ca` is pushed; GitHub Actions run
`33230961979` passed all five required jobs.

R4-422 single-send execution closure (2026-08-29): exact approved contract
`e942a04b080da7cf42645d757fec61a1fb67428b59da29f90c93227b06c7d660` was
consumed fail-closed. Local `DefaultCredentialsProvider` resolution was
available, but the isolated SES client runtime lacked
`org.reactivestreams.Publisher`, so no HTTP request was dispatched. Two local
construction attempts yielded zero AWS/SES requests, zero emails, zero cost,
and zero AWS/IAM mutations. Append-only artifacts, including the first
class-path correction, are under `evidence/gates/R4-422/`; provider acceptance,
delivery, connectivity, and production remain unclaimed. The contract permits
no retry; any future attempt requires a new bounded contract and Human Gate.

Science Readiness Audit (2026-08-28): verdict
`SCIENCE_READY_WITH_NONBLOCKING_GAPS`; `CLAUDE_SCIENCE_CAN_START = YES` for
bounded local exploratory discovery, hypothesis generation, experiment design,
deterministic replay, and falsifiable studies. S1-S8 are all
`PARTIAL_NONBLOCKING`; there is no blocking item for this scoped start. The
full metric/ablation campaign, observed Twin/RADS outcomes, and remote
high-scale Linux launcher/synchronization remain explicit follow-up work.
Readiness evidence and handoff scaffold are in
`evidence/gates/science-readiness/2026-08-28-science-readiness-audit.md` and
`research/SCIENCE_READINESS.md` plus the five linked scaffold files. No task
status or frozen scientific/external result changed.

Science readiness audit checkpoint commit `78b16c2` is pushed to
`origin/main`; real GitHub Actions CI run `33171244301` passed all five
required jobs, including the focused failure-injection and isolated backup /
restore drills. No external provider call or paid resource action occurred.

R4-422 AWS SES offline preparation (2026-08-28): the frozen provider-boundary
contract remains unchanged at SHA-256
`0cc9bcf99a11e3a4f948693e818c1c497ea7e0e3314ce15cd76f0a973eda4ffb`. The AWS
SDK v2 standard credential provider chain is wired through non-secret
`AWS_PROFILE`/profile configuration; no credential file is parsed and SES is
disabled by default. New contract
`contracts/provider/r4-422-aws-ses-live-validation-v1.json` is prepared with
SHA-256 `e6576212ff580f57231ceb83ca95363fb4fd8b42053e85461b6dcd0b1d41b3ca`;
no AWS request or send occurred.

Remote CI checkpoint: commit `50053f8` passed GitHub Actions run
`33178392686` with all five required jobs green. This validates repository and
Compose controls only and does not establish AWS connectivity or delivery.

R4-422 local implementation checkpoint (2026-08-28): the frozen contract
`contracts/product/r4-422-notification-human-gate-v1.json` remains unchanged at
SHA-256 `0cc9bcf99a11e3a4f948693e818c1c497ea7e0e3314ce15cd76f0a973eda4ffb`.
Provider-neutral Java notification models, strict template/privacy rendering,
redacted transactional Outbox payloads, consent rechecks, bounded retries,
duplicate suppression, DLQ, authenticated-receipt semantics, and an offline
failure-injection provider are implemented and covered by seven focused tests.
No AWS SDK/client, credential reader, account/resource change, callback, or
real notification send exists or was invoked. R4-422 remains
`BLOCKED / PREPARED_NOTIFICATION_PROVIDER_HUMAN_GATE`; AWS SES in
`ap-northeast-1` remains an unapproved candidate only.

Implementation checkpoint commit `015a5cf` is pushed to `origin/main`; real
GitHub Actions CI run `33169515189` passed all five required jobs. No AWS,
Google, HERE, or notification-provider call was made.

Authoritative R4-411B execution closure (2026-08-28): approved contract SHA-256
`a2d37bd79cc433e48fc76b5a1b4ba6518592bd5a1a8ac72bc38d1c000e3285d1` completed
with `ComputeRoutes=PASS` and `ComputeRouteMatrix=PARTIAL`; one of four matrix
cells returned a provider error. Final run usage was 1 point request and 1
matrix request with 4 elements; append-only contract usage is 3 point requests,
1 matrix request, and 4 elements after two prior bounded attempts. Final elapsed
time was 2.433 seconds, no fallback was used, and billing readback was
unavailable; conservative cost ceiling remains USD 1.00. Redacted evidence,
prior attempts, usage ledger, and the classification correction are retained
under `evidence/gates/R4-411B/`. No provider-live validation, production,
Tokyo-pinned processing, or Japan Matrix entitlement claim is made.

Offline matrix root-cause audit (2026-08-28): the retained normalized result
pinpoints cell `[1][0]` to synthetic `SHINJUKU -> SHINJUKU`, with HTTP 200,
`ERROR / ROUTE_EXISTS`, and absent distance/duration. Three other cells are
successful. The point result `TOKYO_STATION -> SHINJUKU` matches matrix cell
`[0][0]`; the failing self-pair has no point-route counterpart. Point and
matrix payloads share `DRIVE` and `TRAFFIC_AWARE_OPTIMAL` but have distinct
schemas. The raw provider body was not retained, so the origin field and exact
provider semantics cannot be recovered. The conservative classification is
`INCONCLUSIVE_FIXTURE_REACHABILITY_OR_PROVIDER_CELL_SEMANTICS` with
`MEDIUM_LOW` confidence; no adapter, connectivity, or capability defect is
demonstrated. No retry or new contract is justified. Evidence:
`evidence/gates/R4-411B/2026-08-28-google-matrix-partial-root-cause-audit.md`.

Audit synchronization commit `e0c819b` is pushed to `origin/main`; real GitHub
Actions run `33167661721` passed all five required jobs. No external call was
made during the audit.

HERE retirement checkpoint (2026-08-28): contract
`contracts/provider/r4-411-here-provider-retirement-v1.json` is validated at
SHA-256 `0991151bdce71f5be2e725a21708efecf0184ba830903632e3584bfad74f3e3c`.
R4-411 is terminal `deferred_external` with
`CLOSED_NOT_SELECTED / SUPERSEDED_BY_GOOGLE / NO_LIVE_CLAIM`. Historical HERE
contracts, support ticket `CS0184597`, diagnostics, costs, teardown records, and
frozen validators remain retained. Active runtime/configuration has no HERE code,
dependency, or secret requirement; GoogleRoutesProvider is primary and
deterministic-local is the explicit fallback. No provider live call occurred.

Implementation commit `fcf0c2f8b850e93d74edf8795bee95246e0f57b0` is pushed to
`origin/main`; real GitHub Actions CI run `33161825379` passed all five required
jobs. `scripts/resume.ps1` after that push reports `166/196`, Round 4 `10/38`,
and `Next eligible: NONE`.

R4-411B final synchronization (2026-08-28): commit `74488e1` is pushed to
`origin/main` and real GitHub Actions run `33158830218` passed all five required
jobs. The frozen R4-411 HERE-only evidence record is unchanged; R4-411B is
represented only by the graph-root `replacement_provider_gates` entry, with
contract SHA-256 `a2d37bd79cc433e48fc76b5a1b4ba6518592bd5a1a8ac72bc38d1c000e3285d1`,
live calls unauthorized, and no production or Matrix-entitlement claim.

Task Status: R4-410 is passed and HERE is retired/not selected with historical evidence preserved. R4-411 is terminal deferred with no live claim. R4-411B is `FAILED / PARTIAL_NO_PRODUCTION_CLAIM` at exact contract SHA-256 `a2d37bd79cc433e48fc76b5a1b4ba6518592bd5a1a8ac72bc38d1c000e3285d1`; ComputeRoutes passed and ComputeRouteMatrix was partial with one provider error cell. No fallback, production claim, or Matrix Japan entitlement claim is made. External VKE/VM evidence remains frozen inconclusive and R4-405/R4-406 remain target-pending/no-claim.

Next: no safe task is currently executable. R4-411B bounded execution is closed and no additional Google call is authorized by its consumed contract. R4-422's exact single-send contract `e942a04b...c7d660` was approved but failed before SendEmail during local SES client construction; zero provider traffic and zero emails were recorded. A new contract and Human Gate are required after fixing the local runtime dependency. VKE checks remain deferred, R4-437 inactive, and `.codex-tmp/` must remain untouched.

R4-411 prerequisite revalidation checkpoint: commit `6da7c15` passed real GitHub
Actions CI run `33151723573` (all five required jobs). The checkpoint records
HERE account/application confirmation, presence-only User-scope API-key status,
documented Routing Japan support, and the still-restricted Matrix Japan access;
no HERE live call was made and the frozen contract digest is unchanged.

R4-411 support-ticket evidence checkpoint: ticket `CS0184597` is recorded in
`evidence/gates/R4-411/2026-08-28-here-support-ticket-cs0184597.md` with status
`NEW`, type `Product Catalog`, and category `Account Support`. Submission is
not entitlement approval; Matrix Japan remains restricted and R4-411 remains
blocked. No HERE live call or API-key inspection occurred.

R4-422 provider-neutral preparation checkpoint: the frozen contract
`contracts/product/r4-422-notification-human-gate-v1.json` remains at SHA-256
`0cc9bcf99a11e3a4f948693e818c1c497ea7e0e3314ce15cd76f0a973eda4ffb`. Java-owned
PostgreSQL Outbox/Inbox, bounded retry and dead-letter handling, consent and
quiet-hours rechecks, duplicate suppression, provider-neutral sender/template
boundaries, privacy/leakage rules, and zero-send budget guards are locally
validated in `evidence/gates/R4-422/notifications.md`. AWS SES email in
`ap-northeast-1` remains only the unapproved candidate; real sends, credentials,
account/resource changes, and provider claims remain forbidden.

Latest synchronization before this checkpoint: commit `aab4aa4` passed real
GitHub Actions CI run `33153739404` (all five required jobs). This confirms the
ticket evidence, graph mirror, and R4-422 zero-send preparation are CI-backed;
it does not authorize a provider call or notification send.

R4-411B Google Routes replacement-provider checkpoint (2026-08-28): the
provider-neutral adapter and zero-live-call contract are recorded in
`contracts/provider/r4-411b-google-routes-live-validation-v1.json` and
`evidence/gates/R4-411B/provider-contract.md`. Canonical SHA-256 is
`a2d37bd79cc433e48fc76b5a1b4ba6518592bd5a1a8ac72bc38d1c000e3285d1`. Google
Cloud prerequisites are owner-reported as created/enabled/configured; the key is
presence-only (`SET`/`MISSING`) and the previously exposed key must be rotated.
Point Japan support is documented, Matrix entitlement is not asserted, and
Google-managed processing is not claimed Tokyo-pinned. The fixed Round 4 graph
represents R4-411B under R4-411 per ADR-0036; no HERE/Google live call occurred.

Latest observed pre-synchronization control-plane checkpoint: commit `e2a1b32f215594c471a917b53809e49286c9868f`
passed real GitHub Actions CI run `33086123655` (all five required jobs). The
following documentation synchronization also passed real GitHub Actions CI run
`33092163129`, and its follow-up wording correction at commit `ba09280` passed
run `33092466943` (all five required jobs). The overnight reconciliation found
no stale graph blockers or safe eligible tasks;
R4-411 now lists only the three genuine blockers: HERE account/application and
Matrix Japan entitlement/overall partial Japan eligibility, external secret
injection, and its separate Human Gate; account/application identity is now
confirmed.

## Tokyo VM SSH-readiness diagnostic v1 execution - 2026-08-27

Approved canonical digest `2ba069c9...fbb7` was consumed once under execution
`r4-vm-ssh-v1-20260827t072548z-b0006d8c04` at source revision `b0006d8`.
Authenticated preflight, exact three-create saved plan, provider identity, Ubuntu
24.04 image, matching client/provider ED25519 public key, and one operator `/32`
TCP 22 firewall rule all passed.

The VM reached `active / ok / running` on the first provider observation. Six
bounded probes from `07:27:38Z` to `07:29:53Z` each connected TCP 22 but received
no SSH banner. KEX, host-key verification, authentication, cloud-init, and
bootstrap were not reached. There was no independently retained console host key
or guest artifact, so the result is `DIAGNOSTIC_INCOMPLETE /
SSH_BANNER_NOT_RECEIVED / UNKNOWN`, not a root-cause or target-readiness claim.

Exact teardown and a second GET-only finalizer proved the VM and firewall return
404 and execution-label resource count is zero. The conservative incremental
bound is USD 0.01, cumulative conservative external cost USD 11.256, retained
resources zero, and leakage findings zero. Sanitized external evidence has 11
manifest entries; manifest SHA-256 is
`aa4dabc54cfae06f93747477aef0af113cb2324a6e80ccca446c61f547e0e078`.
Execution finalizer fix `5b5d42b` passed all five jobs in real Actions run
`33050160883`. Repository evidence is
`evidence/gates/R4-405/2026-08-27-tokyo-vm-ssh-readiness-diagnostic-v1-execution.md`.

## Tokyo VM SSH-readiness diagnostic v1 preparation - 2026-08-27

The v2 startup audit found no explicit sshd/network restart, reboot, user
creation, or authorized-key mutation. Its package update/install work is a
possible timing or contention factor, not a root-cause claim. TCP success never
proved SSH banner, KEX, host identity, authentication, cloud-init, or bootstrap
readiness, so the root cause stays `UNKNOWN`.

Contract
`contracts/external-validation/r4-vultr-tokyo-vm-ssh-readiness-diagnostic-v1.json`
has canonical SHA-256
`2ba069c9886c69f1b38a22740c6c2367bd21a2bd129e8ff6c8148f336a46fbb7`.
It freezes one `vc2-1c-1gb`, Ubuntu 24.04 LTS x64 OS ID 2284, user `root`,
the configured ED25519 public fingerprint, one exact operator `/32` TCP 22
rule, 60 minutes, and USD 1. It creates no VPC, storage, load balancer, public
HTTP endpoint, RouteMind, SigNoz, or OTLP stack.

The operator raw probe and guest local/console readiness artifact are atomic and
independent; malformed/missing/execution/aggregation failures cannot delete the
other evidence. Strict host-key checking is mandatory and `accept-new` is
forbidden. The A-P matrix remains conservative. Local gates passed 21 artifact/protocol
and fault tests, seven contract mutations, five plan mutations, PowerShell JSON
and external-key checks, and a real Terraform `3 create / 0 change / 0 destroy`
no-apply plan. Preparation evidence is
`evidence/gates/R4-405/2026-08-27-tokyo-vm-ssh-readiness-diagnostic-preparation.md`.
Preparation commit `e4f9686` passed all five jobs in real GitHub Actions run
`33047908200`.

## Independent provider Human Gate preparation - 2026-08-27

R4-410 closed on 2026-08-27 through the machine-validated receipt
`evidence/gates/R4-410/r4-410-human-approval-v1.json`. The receipt binds the
owner's exact approval statement to canonical v2 digest `6d71059d...3ac5c` and
ratifies HERE Technologies as the candidate provider without changing the
immutable pre-approval contract bytes. It explicitly preserves unconfirmed Japan
eligibility, non-region-pinned processing, zero account/credential creation, zero
live calls, zero spend, and no live or production claim.

Approval-closure commit `a59a0b4` passed all five jobs in real GitHub Actions run
`33079533974`; detailed local and remote evidence is retained at
`evidence/gates/R4-410/2026-08-27-approval-closure.md`.

R4-410 v2 is the current executable fail-closed preparation contract at
`contracts/provider/r4-410-travel-provider-human-gate-v2.json`, canonical
SHA-256 `6d71059d2db366ce0ab3e54b7959f532346b0875101ebc1ab8da9189e8b3ac5c`.
The unapproved v1 digest `7f71f018...75d7` remains historical and is superseded,
not rewritten. v2 recommends HERE Technologies with separate HERE Routing API
v8 point and HERE Matrix Routing API v8 matrix products. It records Japan service
eligibility as `UNCONFIRMED_REQUIRES_HERE`, processing as `NOT_REGION_PINNED`,
and Tokyo residency as unclaimed. It freezes the synthetic-coordinate allowlist,
one external future secret name, zero current calls/spend, no fail-open behavior,
and explicit deterministic-local fallback provenance. Human ratification of the
provider/products, Japan access path, HERE contract/DPA, processing locations,
privacy boundary, and billing ownership is required. R4-411's exact v1
live-validation contract is now prepared at SHA-256
`4eacaad0c0d8a71a73715b750b370d58a4439d70b1f9dd1cc97d119599da6d1c`; it remains
unauthorized until HERE account/Japan eligibility, external secret readiness,
and a separate Human Gate are complete. The contract caps execution at 20 point
calls, 5 matrix requests/100 elements, 30 minutes, and USD 1 with fail-closed
fallback and teardown.
Preparation commit `5d4cee5` passed all five jobs in real GitHub Actions run
`33066336359`.

R4-411 preparation evidence is
`evidence/gates/R4-411/2026-08-27-live-validation-preparation.md`, with the
prior blocked checkpoint retained at
`evidence/gates/R4-411/2026-08-27-blocked-after-r4-410.md`. The independent
contract gate passes 19 tests, and this checkpoint must observe its own real CI
before being considered synchronized.

R4-422 now has a zero-send preparation contract at
`contracts/product/r4-422-notification-human-gate-v1.json`, SHA-256
`0cc9bcf99a11e3a4f948693e818c1c497ea7e0e3314ce15cd76f0a973eda4ffb`.
It recommends email-only AWS SES in `ap-northeast-1`, preserves the frozen
R4-420 delivery truth, and requires external sender/recipient/credential
injection. No provider/channel/recipient is selected, no AWS resource or adapter
is activated, and no message is sent. A later exact execution contract is
required for any resource creation or real send.

## Tokyo VM v2 external execution attempt 1 - 2026-08-27

Contract `b1cf89b...a05b` was consumed once under execution
`r4-vm-v2-20260827t051846z-7c7bd60337` at source revision `7c7bd60`. Authenticated
preflight and saved-plan validation passed at USD 1.476/six hours. Terraform
created exactly two `nrt` VMs, one firewall group, two exact IPv4 `/32` TCP 22
rules, and zero VPCs. Provider identity, region, plans, rules, and zero-VPC
readback passed.

Both instances reached `active / ok / running`; direct operator egress matched
the approved rule and TCP 22 connected, but both connections closed before an
SSH server banner. One bounded recovery reboot did not change the result. No
firewall was widened. RouteMind, SigNoz, OTLP, failure injection, backup/restore,
and DR did not execute, so R4-405/R4-406 remain `TARGET_PENDING` without a root-
cause claim.

The exact five-delete teardown passed. Both VM identities and the firewall are
404, execution-label resources are zero, and no VPC was modified. Conservative
incremental cost is USD 0.246; leakage findings are zero. Only sanitized
evidence remains under `ROUTEMIND_DATA_ROOT/external-validation/r4-vm-v2-
20260827t051846z-7c7bd60337/`, with artifact-manifest SHA-256
`a67384b4b6fdaeee6a1738a7abaf47a1e6f9eafc70e03af206bedada26f1dcf6`.
Repository evidence is `evidence/gates/R4-405/2026-08-27-tokyo-vm-v2-
execution-attempt-1.md`.

## Tokyo VM v2 no-new-VPC preparation - 2026-08-27

The authenticated GET-only audit returned five `nrt` VPCs, all named
`VKE-Network-*`, and zero listed instances, Kubernetes clusters, load balancers,
bare-metal servers, or managed databases. Absence from those lists is not proof
of ownership or non-use. Every VPC remains `UNKNOWN / NOT_SAFE_TO_REUSE`; no
provider resource was created, modified, attached, detached, or deleted.

The new contract is
`contracts/external-validation/r4-vultr-tokyo-vm-external-validation-v2.json`.
Its canonical SHA-256 is
`b1cf89b905b6bb42a98eba17de31fb21883ed94139301986a06247acc660a05b`
and byte SHA-256 is
`a572e7fa0bd1eaa7a4ddeb8a60d3a9fcb5ba7cdd74ea411069e04591ec20ea65`.
It creates exactly two VMs, one firewall group, two SSH `/32` rules, and zero
VPCs. Recovery pulls only an encrypted, digest-bound package directly from the
primary with public-key SSH and pinned host identity. No internal service is
public and no raw package transits the operator.

Local validation passed 16 contract mutations, seven exact-plan mutations, four
GET-only audit tests, Terraform 1.9.8/provider 2.32.0 `fmt/init/validate`, shared
Compose/Foundry gates, and an authenticated `-refresh=false` plan with five
creates, zero changes/deletes, and zero VPCs. The plan was not applied and its
isolated directory was deleted. Evidence is
`evidence/gates/R4-405/2026-08-27-tokyo-vpc-quota-resolution.md`.
Preparation commit `760e1ca` passed all five jobs in real GitHub Actions run
`33039469513`, including the Linux v2 Terraform/Compose/Foundry gate. This is
preparation evidence only and does not authorize a paid execution.

Tokyo VM preparation: contract
`contracts/external-validation/r4-vultr-tokyo-vm-external-validation-v1.json`
has canonical SHA-256
`2c6bd381ea8bdbf6a2c91864ec4bbf7589d434b19f043375322138ad7bfc608a`.
Its offline gate validates an exact two-VM Terraform inventory, no VKE/block/LB,
only operator `/32` and private-VPC SSH ingress, real RouteMind Compose services,
two mTLS Collector boundaries, and pinned SigNoz Foundry rendering. Foundry runs
with `--no-ledger --no-updater`; SigNoz analytics, stats reporting, and identity
collection are disabled. Execution-scoped backend credentials and an egress
block are mandatory target preconditions. No paid resource was created.

Preparation implementation `0a900ce` passed all five jobs in real GitHub Actions
run `32993990760`. The control-plane job independently rendered and validated the
platform-neutral Terraform/Compose/Foundry assets on Linux without provider
mutation. This is preparation evidence only and does not qualify R4-405/R4-406.

The v2 execution's sanitized evidence is under
`ROUTEMIND_DATA_ROOT/external-validation/r4-diag-20260826t134703z-03f22ab836/`.
It records the Operator result, firewall readback, exact resource inventory,
failure phase, authenticated quote, and cleanup inventory; Tokyo observer
evidence is explicitly absent because the parser failed before that probe. The
probe parser now emits unique case-insensitive proxy keys with a directed
regression test. This local correction does not reinterpret the failed run or
authorize another paid execution. R3-325 remains exactly
`E-PASS / X-PASS / S-FAIL / C-NO-CLAIM`.

Post-push CI for commit `179773c` completed green in run `32978351148`, and the
follow-up graph/status checkpoint `0ac8645` completed green in run
`32978781956` (five jobs each).

The v3 independent-artifact preparation commit `80fd171` completed green in
real GitHub Actions run `32982077821` (five jobs). This validates the local
preparation and control-plane gates only; no Vultr resource or paid experiment
was executed.

The v3 execution/evidence closure commit `19e0988` completed green in real
GitHub Actions run `32987266627` (five jobs) against that exact pushed HEAD.
This validates the recorded incomplete result and repository controls; it does
not promote R4-405/R4-406 or authorize another external execution.

External preparation evidence: `docs/adr/0035-vultr-tokyo-external-validation-backend.md`, `docs/runbooks/R4_VULTR_TOKYO_EXTERNAL_VALIDATION.md`, and `evidence/gates/R4-405/telemetry-export.md`. Terraform `1.9.8` validated provider `2.32.0`; a read-only plan for the new contract passed the exact five-create resource validator and its temporary artifacts were deleted. Helm `3.18.6` linted/rendered pinned SigNoz chart `0.138.0` (SHA-256 `b180a601...d7418`) to 32 objects with zero load balancers. The remediated local gates passed 6 TLS identity cases including real OpenSSL CN/SAN generation, 5 fake-DNS/VKE endpoint cases, 5 controller cleanup guards, 8 preparation mutations, 3 evidence-assembly tests, 9 telemetry mutations, 5 DR contract tests, Java 113/113, Python 925/925 at 95.09%, Web 104/104 plus build, Playwright 34/2, focused resilience 16 Java / 2 Python, security, graph/mirror, and controls. The isolated local DR runtime stopped at an unresponsive Docker Desktop `docker version` before creating resources, so the independent Actions recovery job remains mandatory. Evidence checkpoint `fd94ce2` passed all five jobs in real GitHub Actions run `32945284919`; controller/evidence closure `5d7b8a2` passed all five jobs in run `32975132108`. R3-325 was not rerun and remains exactly `E-PASS / X-PASS / S-FAIL / C-NO-CLAIM`.
External preparation evidence: `docs/adr/0035-vultr-tokyo-external-validation-backend.md`, `docs/runbooks/R4_VULTR_TOKYO_EXTERNAL_VALIDATION.md`, and `evidence/gates/R4-405/telemetry-export.md`. Terraform `1.9.8` validated provider `2.32.0`; a read-only plan for the new contract passed the exact five-create resource validator and its temporary artifacts were deleted. Helm `3.18.6` linted/rendered pinned SigNoz chart `0.138.0` (SHA-256 `b180a601...d7418`) to 32 objects with zero load balancers. The remediated local gates passed 6 TLS identity cases including real OpenSSL CN/SAN generation, 5 fake-DNS/VKE endpoint cases, 5 controller cleanup guards, 8 preparation mutations, 3 evidence-assembly tests, 9 telemetry mutations, 5 DR contract tests, Java 113/113, Python 925/925 at 95.09%, Web 104/104 plus build, Playwright 34/2, focused resilience 16 Java / 2 Python, security, graph/mirror, and controls. The isolated local DR runtime stopped at an unresponsive Docker Desktop `docker version` before creating resources, so the independent Actions recovery job remains mandatory. Evidence checkpoint `fd94ce2` passed all five jobs in real GitHub Actions run `32945284919`. The new read-only VKE diagnostic tool and contract validate locally and passed all five jobs in real GitHub Actions run `32948600781`; their proposed digest is `30c9580eb2fe43de1306b299a73c4a1c5d0f286ac7bef4be0c3d0f4b7994a426` and remains unauthorized. R3-325 was not rerun and remains exactly `E-PASS / X-PASS / S-FAIL / C-NO-CLAIM`.

R4-405 evidence: implementation `49680bd` passed run `32852309878`; preparation `10ec537` passed run `32920903229`; cross-volume remediation `2efb0f6` passed run `32928947867`; execution activation `eb70db7` passed run `32930028175`; first-attempt remediation `fb6adcd` passed run `32934187355`; VKE firewall remediation `160f670` passed run `32937109761`. Attempt 2 `r4-ext-20260826t054111z-ea80181368` used approved digest `4956d29a...77393`, stopped at the zero-rule VKE firewall, and completed exact zero-inventory cleanup. Attempt 3 `r4-ext-20260826t063255z-18f9f4f51b` used approved digest `c2a16951...f4e2df`, applied five resources, still observed VKE API TLS EOF, and completed exact zero-inventory cleanup; details are in `evidence/gates/R4-405/2026-08-26-external-attempt-3.md`. No target pass, production claim, experiment, or R3-325 rerun occurred.

R3-365 closure report remains `docs/research/r3/ROUND_3_SCIENTIFIC_CLOSURE_REPORT.md`, byte SHA-256 `f5e12a289ccd7cd01c37edad739b4e4ace8496c80fd1dc82cc055d172a769632`. The active `docs/research/ROUND_4_TASK_GRAPH.yaml`, byte SHA-256 `7ce10a36c0d66200e9535e471922831b03f58d6601e2a48d18873320c49baba6`, has 38 tasks across six workstreams, 15 external gates, 12 human approvals, three conditional tasks, 11 closure classifications, and 11 preserved Round 3 reclassification lanes. `scripts/round4_graph_gate.py` plus nine directed tests validate the live `TASK_GRAPH.yaml` mirror, reject gate/dependency/classification drift or claim promotion, and bind R3-325 plus the zero-`C-PASS` Claim Matrix. R3-313 maps to optional R4-437; R3-355 maps to R4-438/R4-439 and conditional R4-440. R4-401 read only the public Vultr catalog; no credentialed call, resource creation, production action, experiment, or R3-325 rerun occurred.

R3-360 evidence is `evidence/gates/R3-360/final-figures.md`. Final plan digest is `10e12aa0f586ad94e963396feb0a045fc1b21fe4ff0cd7537d0d769f145bb30d`; bundle digest is `2b230697ea367ace51afcd52c7544efd6cd024abca0104f10a35b50ebce34684`. Actions run `32789597203` passed all five jobs. The final 16/12/7 rows retain six non-estimable cells, unexecuted confirmatory inference, zero Twin observations, unsupported RADS location noise, zero exclusions, and zero `C-PASS`. R3-325 was not rerun.

R3-360 final plan is `docs/research/r3/manifests/final-figures/r3-360-final-figures-v2.json` with digest `10e12aa0f586ad94e963396feb0a045fc1b21fe4ff0cd7537d0d769f145bb30d`. Its committed index has bundle digest `2b230697ea367ace51afcd52c7544efd6cd024abca0104f10a35b50ebce34684` across three SVG and three CSV artifacts. Exact row counts are 16/12/7; negative outcomes are six non-estimable assignment cells, confirmatory inference not executed, zero Twin observations, unsupported RADS `location_noise`, zero exclusions, and zero `C-PASS`. Browser-rendered QA passed after v2 corrected a column overlap found in the immutable v1 draft. Automated validator plus six tests and all non-Docker control gates pass. Large v2 artifacts, sidecars, and QA screenshots are under `ROUTEMIND_DATA_ROOT/research/r3/R3-360/r3-360-final-figures-v2/`. No experiment or R3-325 rerun occurred.

R3-359 evidence is `evidence/gates/R3-359/claim-review.md`; Claim Matrix byte SHA-256 is `c6656ac6a1f4634c001cace78867c924b950eebef944380f8a26c556fac9d4cc`. Actions run `32787968109` passed all five jobs. The executable gate enforces seven identities, final dispositions, R3-357/R3-356 mappings, supported-claim equality, and frozen R3-325 status. No experiment or external artifact was rerun.

R3-357 evidence is `docs/research/r3/PRIOR_ART_AUDIT.md`; byte SHA-256 is `5978c859247230566e77d9573c2b4d62cb3b960555e3d4e035d85c6660052f4c`. The Claim Matrix maps every proposed claim to a prior-art audit identity and completed reproduction status. No `C-PASS` or novelty claim was created. Actions run `32787178651` passed all five jobs. R3-325 remains frozen exactly as `E-PASS / X-PASS / S-FAIL / C-NO-CLAIM` and was not rerun.

R3-347 evidence is `evidence/gates/R3-347/counterfactual-xray.md`. Plan digest is `4c76ce8200f00adeeb2690051d7615fa47d710523b78d631e849385b135047ce`, byte SHA is `d7306891950446216d4188a672a0ebfd6d5154b76555d65208b4d12f2a261f90`, and audit digest is `9c4be0fd4c7d2f7b54e1ccc92fd34ef84e7bb37e6f4a2e1ccc488673996107d8`. Two summaries, zero replays, and eight missing fields prohibit perturbation/delta/minimality claims. R3-325 remains frozen and was not rerun.

R3-346 evidence is `evidence/gates/R3-346/policy-boundaries.md`. Plan digest is `02304c1910463a30a481070382d76bb55c01c76be1bd6b7bcbeba972b14da5dd`, byte SHA is `daa5e1a3ca7bf423eb1c1fa99ed50d1a25a35683a84751f926c056de234a7e8d`, and formal audit digest is `dd5787f22a328cc6afb532624def46eea7866326b595903fc16884287ef35ed6`. One `shadow` class has two records, eligible stability cells are zero, six support fields are absent, and no boundary/uncertainty/sensitivity output was estimated. R3-325 remains frozen and was not rerun.

R3-358 evidence is `evidence/gates/R3-358/negative-results.md`. Audit manifest digest is `e36e3be33cb61138472cf94966ea31a2fb7432af142a5d50c011e6359fd6dcf5`, byte SHA is `396a3a921a28bdeb30f4429b97ce75a509b9193c47897a8ec7bf36c782d33e91`, and the immutable 31-entry prefix digest is `89fe0c2eb1cab8da5162c4769f4bcef41bc8b904dcc0f933a1bf069192032706`. Validation covers 24 tasks, six categories, seven exact source artifacts, and append/mutation/deletion behavior. R3-325 and R3-327 remain `S-FAIL/C-NO-CLAIM`; R3-355 remains deferred, not failed engineering.

R3-356 evidence is `evidence/gates/R3-356/independent-reproduction.md`. Plan digest is `aaab4e70a7daa04d6850c886edb80ac652d47f0fad89e89e75b550530f874d93`; formal result digest is `9eea07d71c037199eca311e242308da1f517904f082099098dea409fd985c36e` and byte SHA is `feb374e75420ec6c9e100dde634c80f936c8bf10d19da182562c879154dc61e7`. Attempt 1 remains byte-for-byte with SHA-256 `09897e3db418cb5a41aa8343f009c50fd7bf7ee7b187cc58981b313b0427d307`. The order-only recovery changed no expectation, and R3-325 remains frozen at `E-PASS / X-PASS / S-FAIL / C-NO-CLAIM`.

R3-349 evidence is `evidence/gates/R3-349/rads-robustness.md`; plan digest is `379f5087f3114f50cd9bb8cefff62af0d9a35e0ea3e1ba12544b9fafc52527a2` and byte SHA is `e58abf5ac7498a3564c3a9dc7d001ae34da2d79ccde6a54d41a2c4fc091d7f5b`. Seven axes preserve source regimes without RADS outcomes, location noise is unsupported, and broad robustness claims are prohibited. R3-325 remains frozen and was not rerun.

R3-336 evidence is `evidence/gates/R3-336/twin-non-fidelity.md`; plan digest is `ed63c2a2c7a8020076411f285ff3c7fccd3b12e7800de70c4ad5b4a9a674dd94` and byte SHA is `87359292944b701cedfa11546cbca2553c259645d83d6bb2b4e6857b9d58e571`.

R3-340 evidence is `evidence/gates/R3-340/rads-baseline-freeze.md`; baseline digest is `a907a0a722e8782aa76277637fa92205cc10046e5aca85b2de81e555623016c3` and byte SHA is `c477a1ae2b00fcd53251be26db4229c56b7e2e91d79b49f9303aba29b6014a02`.

R3-341 evidence is `evidence/gates/R3-341/rads-h-formalization.md`; plan digest is `4b846bc8b971df269c1c6439b325ab61b7803a83812ced39b352f519acb929c5` and byte SHA is `091a196bfbcaae57077cd862b87a30d7793300bae219f0b6c32e95cff6060e94`.

R3-342 evidence is `evidence/gates/R3-342/hysteresis-experiments.md`; plan digest is `725bce8111db8652c6b52ef1c71e63429594aa4a329e0372e524471ea41ac967` and byte SHA is `62eab0fca0a28a758ae6299a83c900752044f3c155f84245e09dadc6e7ac921d`. The read-only support audit returned `INSUFFICIENT_DATA` because all six required tick-level fields are absent from frozen R3-325 pair artifacts; all metrics are `NOT_REPORTED_NO_SWITCH_LOGS`.

R3-343 evidence is `evidence/gates/R3-343/stability-map.md`; plan digest is `c6d7d4a5ac088570731e80a189c12cd79792256ac3669bdeed5f9049d6b4ee14` and byte SHA is `8153eeef5f5397ae411371eedb9c369995ba1cdc33057814a9923613213e49c6`. The audit returned `INSUFFICIENT_DATA`, `NO_ELIGIBLE_CELLS`, and `NOT_ESTIMATED_NO_CELL_SUPPORT`; no map or theoretical-stability claim exists.

R3-344 evidence is `evidence/gates/R3-344/safe-rads-formalization.md`; plan digest is `82fed4dc95bec7ccbfa10ead770d63e2de6f47bb081d0b5d05672382462f6644` and byte SHA is `a3570615177b19fa59688b23a0e85f76957c6090b75f1fd6d165f3506b171163`. This is a formal preregistration boundary only; no safety, calibration, efficiency, or superiority claim is authorized.

R3-345 evidence is `evidence/gates/R3-345/safe-rads-experiments.md`; plan digest is `182a3e6217f2c8e918049a4d55b78e340c8882a58e5dad106a7f738c3433783c` and byte SHA is `74d83b8fc695e623d6b1a89466f3836bcf6dec618745080920df8080dbb68288`. The support audit returned `INSUFFICIENT_DATA`; all seven metrics are `NOT_REPORTED_NO_SAFE_OUTCOMES`.

R3-348 evidence is `evidence/gates/R3-348/rads-ablation.md`; plan digest is `c5644b75580db5d95f33a28ea6cd367906a235aac777f46890f862cdf952d2e7` and byte SHA is `388598f7c0265ecfad9f99247b6efc8124b8bc53383d49d102f4be269879d2b4`. The audit returned `INSUFFICIENT_DATA`; five applicable dimensions are `NOT_EVALUATED_NO_ABLATION_LOGS`, counterfactual feature is `NOT_APPLICABLE_FEATURE_ABSENT`, and no R3-325 rerun or component-effect claim occurred.

R3-351 evidence is `evidence/gates/R3-351/shadow-disagreements.md`; plan digest is `f2dfc31a57db3dcd7c3ad2c4f432b41efcbdd7c252274904550a818508734022` and byte SHA is `00a79ee8571465197f43f6c47c43b7a328f11724cca2cf482253cfdfbdb847dc`. The two-record corpus lacks alternate outcomes and disagreement strata; result is `INSUFFICIENT_DATA`, not superiority evidence.

R3-353 evidence is `evidence/gates/R3-353/interference.md`; plan digest is `4a1b3477a7da89e42ded5d58e38b086bf459863cd2e320bf038f383b2438de8c` and byte SHA is `7500c777993eee907e2642e30a70eefc938778bb9bee8de12dc3496e102db8e5`. The frozen design has no simulation outcomes; result is `INSUFFICIENT_DATA`, simulation-scoped only.

R3-354 evidence is `evidence/gates/R3-354/ope-identifiability.md`; plan digest is `bbce6870d64222128ab06015a5a8a0642cbc30b0f6677b5da2c9e4422b3e3609` and byte SHA is `a7f254babad7382d4d6f1db66d2a82606a4f9e3fdc53109f69445c0b3fabda5d`. Result is `OPE_NOT_IDENTIFIABLE_FROM_CURRENT_LOGS`; no propensity or OPE effect claim is permitted.

R3-335 evidence is `evidence/gates/R3-335/what-if-validity.md`; plan digest is `81c52721886c646d2ff468f500c334566e3ed7f4f66bf0f63a9c4478f4b42023` and byte SHA is `20640a2cd366fd992dec681c3dc4139b4b352cb9609bf71ba0542a9bceb9a57d`.

R3-333 evidence is `evidence/gates/R3-333/fidelity-protocol.md`; protocol digest is `de453fdf1181b2e5a52839eb9f1b7536db3f5f5fb1177f4b5351269cfa3c1825` and byte SHA is `a3007f1ca9892fd0b7746797e53dec9ab5aecc5e243d188b16f12564df2ea8ff`.

R3-324 resume capsule: the exact frozen 16-test Holm step-down family retains
protocol/regime/metric/hypothesis identity, raw p-values, stable family ranks,
multipliers, sequential thresholds, monotonic adjusted p-values, rejection
decisions, family disposition, claim boundary, and content digest. The reference
vector adjusts first to 0.016/0.030/0.042/0.052, rejects 3/16, and has digest
`53580e4f...e18c`; ties at the boundary adjust deterministically to 0.05.
Invalid values, identity drift, incomplete/duplicate families, and frozen
protocol drift fail closed. Twenty-two directed tests pass at 100% module branch
coverage; statistical integration is 143/143. The full local gate passes Java
81/81, Python 657/657 at 95.88%, Web 92/92 plus build, contracts, controls, and
determinism gates. During validation, a real Java same-instant transition flake
was diagnosed and repaired with monotonic aggregate/outbox event time; the fixed
clock regression and originally failing lease test pass. Implementation revision
`c3e394b` passed all five jobs in Actions run `32720233681`; R3-324 is closed.
Next: define R3-333's variable-appropriate Twin fidelity metrics, absolute
thresholds, improvement tests, and fail-closed INSUFFICIENT_DATA behavior;
R3-331 remains dependent on this protocol. R3-330 evidence is
`evidence/gates/R3-330/twin-dataset-contract.md`; its contract digest is
`fb3f3162ac073815cba838f3fde5a3b8ac94604e21dc4f9049bdf3785d108eaa`.
The R3-327 report implementation `ed01044` passed all five jobs in Actions run
`32737520239`; its report digest remains
`0c7e29af8c89ed9ca7cb094525745f488c4b4d69e73ab6a4a7f47dd4e5ae9eac`.
The report digest is
`0c7e29af8c89ed9ca7cb094525745f488c4b4d69e73ab6a4a7f47dd4e5ae9eac`; it
retains the six `NON_ESTIMABLE` assignment cells and makes no strategy claim.

R3-323 resume capsule: exact SciPy 1.18.0 one-sided noncentral paired-t planning
records the content-addressed variance source, frozen MDE/noninferiority distance,
family/local alpha, target, raw/rounded/planned counts, achieved power at required
and capped counts, runtime identity, disposition, and stable digest. The frozen
16-test Holm family uses conservative local alpha 0.003125; counts round to four
and retain the 20-200 cap without weakening design inputs. Synthetic variance
0.0016 yields raw 55, planned 56, power 0.8104064287044574. Variance 0.01 requires
324 and remains UNDERPOWERED_AT_CAP at 200 with power 0.5269065070498476. An
observed R3-325 pilot must contain exactly eight pairs. Forty-one directed tests pass
at 100% module coverage; integration is 120/120; the full local gate passes Java
80/80, Python 635/635 at 95.83%, and Web 92/92 plus build. Ruff, strict mypy,
contracts, lock/security, determinism, analytics, semantic metrics, and controls
pass. Implementation revision `b18d171` passed all five jobs in Actions run
`32718029279`; R3-323 is closed. R3-324 is active. Next: implement the exact
16-test Holm step-down family with stable identities, ties, monotonic adjusted
p-values, reject decisions, and fail-closed family validation; then run local and
remote gates. No pilot or confirmatory campaign ran.

R3-322 resume capsule: validated CRN plans feed candidate-minus-comparator paired
mean, median, sample SD, standard error, two-sided 95% Student-t interval,
paired Cohen's dz, 10% Winsorized mean, and complete leave-one-pair-out
sensitivity. Reports retain every four-stream seed/digest and have stable content
digests; forged, mixed, duplicate, incomplete, non-finite, out-of-range, and
zero-variance samples fail explicitly. Five Student-t references pass within
`5e-10`; 29 directed tests pass at 95.71% module coverage, integration is
101/101, and the full local gate passes Java 80/80, Python 594/594 at 95.76%, Web
92/92 plus build, contracts, determinism, analytics, semantic metrics, and
controls. Standard vector report digest: `8cc4f549...e585c`. No campaign ran.
Implementation revision `349a27e` passed all five jobs in Actions run
`32715625853`; R3-322 is closed. R3-323 is active. Next: freeze the power method,
record supplied variance/MDE/alpha/power/count/cap/disposition, validate against
independent vectors and underpowered cases, then run local and remote gates. Any
fixture variance must remain labeled synthetic until R3-325 runs the real pilot.

R3-321 closure capsule: demand, merchant, courier, and traffic have distinct
logical owners; preregistered SHA-256 derivation produces arm-independent 63-bit
seeds; each stream is realized once and both arms bind identical realization
digests; order alternates by replicate parity. The implementation explicitly
records `VARIANCE_CONTROL_NOT_OBSERVATION_INDEPENDENCE`. Directed tests passed
21/21 at 96.12% module coverage. The full local gate passed Java 80/80, Python
565/565 at 95.76%, Web 92/92 plus production build, 6 schemas / 18 fixtures,
determinism, analytics, semantic metrics, and repository controls. Implementation
revision `00475b8` passed all five jobs in Actions run `32714350193`. No pilot was
executed. R3-322 is active; implement Student-t paired intervals, paired Cohen's
dz, median, 10% Winsorized mean, leave-one-pair-out sensitivity, and fail-closed
sample validation, then run full local and remote gates.

Completed: Repository reconnaissance found an empty greenfield root and an existing
external data boundary. RM-000 established the authoritative control plane, task
graph validation, quality gates, recovery scripts, architecture contract, and ADR.
RM-001 added pinned PostgreSQL/RabbitMQ/Redis Compose infrastructure, isolated host
ports, health automation, stable RabbitMQ identity, and persistent volumes.
RM-002 added the Java 17/Spring Boot 4.1.1 business runtime, Maven Wrapper,
layered module boundaries, health and system endpoints, Flyway, and PostgreSQL
schema ownership.
RM-003 added the Python 3.12-3.14/FastAPI compute runtime, an isolated pinned uv
bootstrap, a hash-bearing lock file, framework-free dispatch strategy contracts,
strict boundary/type/lint gates, and loopback-only health/system endpoints.
RM-004 added independently versioned JSON Schema 2020-12 API/event contracts,
a conservative compatibility policy, positive/negative fixtures, permanent v1
compatibility baselines, and an executable validator in the frozen Python gate.
RM-005 has a least-privilege GitHub Actions workflow with independent control,
Java, and Python/contract jobs. The Python bootstrap is now portable across
Windows and Linux PowerShell.
RM-010 implements sealed customer, merchant, and courier identities, audited
party aggregates, Flyway V2 persistence, and a JPA repository adapter. H2
repository tests and a real PostgreSQL 18.6 migration/constraint probe passed.
RM-011 implements the order lifecycle state machine, immutable transition audit,
JPA persistence, Flyway V3, and optimistic database versioning. Domain and
repository tests plus a real PostgreSQL migration/persistence probe passed.
RM-020 implements the versioned event envelope, transactional order command and
Outbox write, pessimistic claim, stable event IDs, bounded retry, and RabbitMQ
publisher confirms. Flyway V4 and real PostgreSQL/RabbitMQ health/persistence
validation passed.
RM-021 implements durable event-ID deduplication, processing-before-ack
semantics, bounded retries, and observable dead-letter state. Flyway V5 and real
PostgreSQL validation passed.
RM-022 implements durable courier locations, a rebuildable Redis GEO projection,
nearby queries, and explicit `PROJECTED`/`DEGRADED` write outcomes. Flyway V6,
real PostgreSQL/Redis validation, and Redis-outage durability tests passed.
RM-030 implements the versioned Python dispatch result, a replaceable strategy
registry, and a deterministic Haversine nearest baseline with tie-breaking,
latency, and decision metadata.
RM-031 implements weighted-greedy and Hungarian baselines through the same
registry, including rectangular matrix assignment and benchmark provenance.
RM-040 implements point and matrix travel-time provider contracts, a
deterministic local Haversine estimator, and timeout/error fallback with
explicit provider and fallback metadata.
RM-050 implements an immutable seeded scenario manifest, deterministic event
kernel, dispatch/travel integration, replayable state transitions, and a
canonical SHA-256 replay digest.

RM-060 implements the shared React/TypeScript role-aware web surface under
`apps/web`, with Operations, Strategy, Customer, Merchant, and Courier routes,
typed deterministic demo data, independent Java/Python health probes, accessible
responsive controls, a schematic dispatch map, lifecycle timeline, and Playwright
desktop/mobile/axe smoke gates. The surface explicitly labels demo state and does
not own durable business state. Evidence is in
`evidence/gates/RM-060/2026-08-22-role-aware-web.md`.
The RM-060 checkpoint commit `9eaada1` passed all four GitHub Actions jobs in run
`32548856880`.

RM-080 adds bounded request/trace context, structured completion logs, request
count/latency metrics, health/SLI documentation, a Java Micrometer registry-backed
`/metrics` endpoint, Python Prometheus metrics, and deterministic failure injection
for travel-provider and Redis projection degradation. A fixed 100-request local
bounded-burst smoke is included. Local full gate passed with Java 34 tests and
Python 36 tests at 98.07% coverage. Evidence is in
`evidence/gates/RM-080/2026-08-22-observability-resilience.md`.
The RM-080 checkpoint commit `c1913f3` passed all five GitHub Actions jobs in
run `32552399489`, including the focused resilience job.

RM-090 defines and implements the Python research boundary for RouteBench and
lineage. `BenchmarkManifest` records code/scenario/seed/load/city/failure,
configuration, runtime, hardware, and dataset provenance. `RouteBenchRunner`
compares registered strategies through fresh Digital Twin kernels and emits
deterministic replay/output digests plus observed runtime. `ResearchLineage`
stores typed hypothesis, observation, result, and conclusion nodes with parent
links, canonical payloads, and manifest/hypothesis queries. Local full gate
passed with 40 Python tests at 97.75% coverage and Java/Web/control regression.
Evidence is in `evidence/gates/RM-090/2026-08-22-routebench-lineage.md`.
The RM-090 checkpoint commit `a32802d` passed all five GitHub Actions jobs in
run `32553160352`.

RM-070 defines and implements a bounded Python Agent Runtime and Orchestrator.
Read/research tool permissions, role grants, argument keys, metadata, and
per-session call counts are bounded and validated. Immutable audit records
capture accepted, rejected, and failed calls. Orchestration emits deterministic
fallbacks for missing plans, denied tools, handler failures, and call-budget
exhaustion, while the existing dispatch registry remains independent of agent
availability. Local full gate passed with 45 Python tests at 96.47% coverage,
Java 34 tests, and Web/control regression. Evidence is in
`evidence/gates/RM-070/2026-08-22-agent-runtime.md`.
The RM-070 checkpoint commit `3b1c5b2` passed all five GitHub Actions jobs in
run `32553873639`.

RM-091 implements the deterministic RADS research baseline. Immutable risk
signals and encoded states feed a decomposed distance/risk objective with stable
tie-breaking and explicit explanations. `RadsExperimentRunner` compares RADS
with registered baselines and records full, distance-only, and risk-only
ablations across explicit risk multipliers with stable manifest and output
digests. The reduced experiment shows the registered distance baselines choosing
the near/high-risk courier while full/risk-only RADS chooses the farther/low-risk
courier. Local full gate passed with 50 Python tests at 95.47% coverage, Java 34
tests, and Web/control regression. Evidence is in
`evidence/gates/RM-091/2026-08-22-rads-baseline.md`.
The RM-091 checkpoint commit `50e666d` passed all five GitHub Actions jobs in
run `32554498417`.

RM-081 implements isolated strategy Shadow Mode and a deterministic regression
gate. The active strategy is evaluated first and remains authoritative; candidate
exceptions become bounded failures and never mutate business state. Immutable
observations record both outcomes, metrics, and digests while excluding wall
clock latency from reproducibility hashes. Explicit sample, candidate failure,
assignment-rate drop, and disagreement thresholds produce `promote` or `hold`
with stable reason codes. Local full gate passed with 56 Python tests at 96.05%
coverage, Java 34 tests, and Web/control regression. Evidence is in
`evidence/gates/RM-081/2026-08-22-shadow-regression.md`.
The RM-081 checkpoint commit `8b92bf0` passed all five GitHub Actions jobs in
run `32555440040`.

RM-082 adds a local static security and supply-chain hygiene gate. It scans only
Git-tracked files for private keys, high-confidence provider tokens,
non-placeholder secret assignments, and sensitive artifacts; checks Python/npm
lock metadata, workflow least-privilege permissions, and Compose image/loopback
hygiene; and runs three standard-library self-tests from `verify.ps1`. Local
full gate passed with Java 34 tests, Python 56 tests at 96.05% coverage, Web
regression, and security checks. Evidence is in
`evidence/gates/RM-082/2026-08-22-security-supply-chain.md`.
The RM-082 checkpoint commit `5498fee` passed all five GitHub Actions jobs in
run `32556047734`.

RM-083 defines immutable PostgreSQL/RabbitMQ/Redis recovery artifacts with
relative paths, SHA-256, byte size, source revision, and contiguous restore order.
The local rehearsal validator verifies fixture package integrity and reports
bounded ready/blocked reasons; rollback metadata is reproducible and requires
explicit acknowledgement without executing a state change. Local full gate
passed with Java 34 tests, Python 56 tests at 96.05% coverage, Web regression,
security checks, and four recovery-contract self-tests. Live service restore is
explicitly not claimed and remains deferred_external. Evidence is in
`evidence/gates/RM-083/2026-08-22-recovery-contract.md`.
The RM-083 checkpoint commit `4b47d4e` passed all five GitHub Actions jobs in
run `32556590018`.
The RM-083 CI evidence commit `ac4723c` passed all five GitHub Actions jobs in
run `32556661332`.

RM-084 defines immutable release artifact provenance and a canonical release
manifest covering source revision, contracts, migrations, health checks, and a
content-addressed rollback package. Its read-only preflight reports stable
blocker codes for mutable or incomplete inputs and unsafe/missing repository
files. Local full gate passed with Java 34 tests, Python 56 tests at 96.05%
coverage, Web checks/build, security/recovery/release self-tests, and schema
fixtures. Evidence is in
`evidence/gates/RM-084/2026-08-22-release-preflight.md`.
The implementation checkpoint is `ada92bc`; the CI evidence checkpoint is
`5459b50`, and GitHub Actions run `32557262937` passed all five jobs.

RM-085 design defines immutable ordered cohorts, integer basis-point thresholds,
and deterministic `promote`/`hold`/`rollback` precedence. Rollback wins on
unhealthy required checks, breached safety limits, or unavailable rollback
readiness; promotion cannot skip the next declared stage. The contract is
read-only and leaves traffic shifting, live monitoring, and production restore
external. Design is in
`docs/design/p8-staged-release-decision-contract.md`; the task graph now marks
RM-085 `in_progress`.
The implementation checkpoint `4367caf` adds deterministic evaluation and five
self-tests; local full gate passed. Evidence is in
`evidence/gates/RM-085/2026-08-22-staged-release.md`. The task remains
`passed` after Actions run `32558073285` passed all five jobs.

Tests Run: Stage 0 gates passed. RM-001 passed Compose validation, real health,
PostgreSQL SQL, RabbitMQ diagnostics, Redis authenticated ping, loopback binding,
cross-`down/up` persistence for all three services, and the unified infrastructure
gate. RM-002 passed seven unit, architecture, HTTP, and migration tests; a live
PostgreSQL 18.6 run returned health `UP`, system identity `business-api/java/v1`,
and Flyway history `1:true`. RouteMind processes and containers were stopped.
RM-003 passed Ruff, format, strict mypy, 16 tests with 100% statement/branch
coverage, locked synchronization, and a live Uvicorn HTTP probe. The Python
process was stopped cleanly.
RM-004 validated four schemas and twelve fixtures, including UUID/date-time
formats, dispatch invariants, and stable event/correlation/causation/trace fields.
RM-005 passed all three jobs in GitHub Actions run 32496271644. The first run
caught Windows-specific Java wrapper paths; commit `de5e608` made JDK and wrapper
discovery portable, after which control, Java, and Python/contract jobs passed.
RM-010 passed 18 Java tests, architecture checks, Flyway V2/Hibernate validation
on PostgreSQL 18.6, health `UP`, role-scoped uniqueness, and audit-order checks.
RM-011 passed 22 Java tests, explicit happy/forbidden/repeated/stale command
coverage, Flyway V3/Hibernate validation on PostgreSQL 18.6, and persisted
transition audit rows.
The RM-011 commit `9872d76` passed all three GitHub Actions jobs in run
`32498473119`.
RM-020 passed 27 Java tests, full available gates, Flyway V4/Hibernate
validation on PostgreSQL 18.6, RabbitMQ health via the Compose-mapped port, and
transactional order-to-Outbox persistence.
RM-021 passed 30 Java tests, full available gates, Flyway V5/Hibernate
validation on PostgreSQL 18.6, duplicate suppression, and persisted
`DEAD_LETTER` attempt/error evidence.
RM-022 passed 33 Java tests, full available gates, Flyway V6/Hibernate
validation on PostgreSQL 18.6, authenticated Redis GEOSEARCH, durable courier
location persistence, and degradation behavior when the projection is unavailable.
RM-030 passed the full compute gate: 23 Python tests, strict mypy, Ruff, all
contract fixtures, and 100% statement/branch coverage. The nearest baseline
selects by `(distance_km, courier_id)` and the registry records solve latency,
strategy version, candidate count, and assignment status.
RM-031 passed the full available gate with 26 Python tests and 96.43% total
statement/branch coverage. Weighted-greedy and Hungarian results share the
versioned registry contract; a smoke benchmark records strategy, version,
latency, selected courier, and provenance.
The RM-031 commit `bf44e12` passed all three GitHub Actions jobs in run
`32503389125`.
The RM-030 commit `2a9b3de` passed all three GitHub Actions jobs in run
`32502960806`.
RM-040 passed the full available gate with 29 Python tests and 97.24% total
statement/branch coverage. Point/matrix estimates are deterministic and
primary provider failures or timeouts are marked as fallback results.
RM-050 passed the full available gate with 32 Python tests and 97.92% total
statement/branch coverage. Repeated runs with the same manifest and seed are
byte-identical; changed seed or inputs produce a different replay digest.
The RM-050 commit `595a221` and follow-up baseline coverage commits `ccce5fa`
and `53ab288` passed all three GitHub Actions jobs in run `32505121861`.
The RM-040 commit `cf71191` passed all three GitHub Actions jobs in run
`32504045099`.

Known Failures: Global `JAVA_HOME` points to JDK 8 while the active `PATH` JDK is
17. Repository Java commands deliberately resolve and validate the active JDK.
Maven is not installed globally; use the repository wrapper script.
The first Python dependency sync took several minutes because uv's cache and the
workspace are on filesystems that do not support hardlinks. The script now fixes
copy mode; subsequent frozen syncs are incremental.

Known Blockers: NONE

Important Context: Keep Java business correctness separate from Python compute and
research. Do not store large datasets or runtime databases in Git. The configured
data boundary is `F:\Projects\RouteMind-Data` on this workstation.

RM-086 implementation checkpoint `45850cd` adds the framework-independent Java
policy, five unit tests, and local full-gate evidence. The task remains
`passed` after Actions run `32558622055` passed all five jobs.

Next Recommended Action: Commit and push the Round 2 gap audit and expanded
task graph, observe planning CI, then implement RM-100's explicit LIVE/DEMO/
REPLAY adapter and minimal Java/Python read contracts.
The RM-088 design now binds release/staged/auth/rate digests, requires
fail-closed immutable edge references for apply/rollback, and keeps local
preflight/plan read-only. Design is in
`docs/design/p8-deployment-edge-security-adapter.md`. The implementation adds
the pure Java `DeploymentEdgeAdapter`, immutable request/capability/decision
records, stable operation digests, and five focused tests. Local Java (49 tests)
and repository gates pass; implementation evidence is in
`evidence/gates/RM-088/2026-08-22-deployment-edge-security.md`.
GitHub Actions run `32559680696` passed all five jobs.

The RM-087 design now defines immutable limits, normalized descriptors, reject
versus throttle precedence, deterministic retry-after, and the explicit
non-claim that distributed counters and WAF remain external. Design is in
`docs/design/p8-rate-limit-input-protection.md`.

The implementation checkpoint `24831c0` adds the Java evaluator and five unit
tests; local full gate passed. Evidence is in
`evidence/gates/RM-087/2026-08-22-rate-limit-input.md`. The task is now
`passed` after Actions run `32559165335` passed all five jobs.

Round 2 gap audit: `docs/reviews/ROUND_2_GAP_AUDIT.md`.
Round 2 foundation design:
`docs/superpowers/specs/2026-08-22-round2-live-product-foundation-design.md`.
The graph now contains 48 Round 2 tasks (RM-100 through RM-190); Round 1 tasks
remain passed, RM-106 is CI-validated, and RM-107 is the current active task.

Next Candidate Task: implement RM-110 operations command-center data projection.

Relevant Files: `TASK_GRAPH.yaml`, `MASTER_ARCHITECTURE.md`, `compose.yaml`,
`scripts/full-gate.ps1`, `scripts/business-api.ps1`,
`scripts/compute-api.ps1`, `services/business-api/README.md`,
`services/compute-api/README.md`, `contracts/README.md`,
`docs/runbooks/local-development.md`

Do Not Do: Do not collapse the dual runtime, treat Redis as durable truth, bypass
Outbox/Inbox reliability, put large data in Git, or mark tasks passed without gates.

RM-100 implementation checkpoint `8b70f9e` passed local gates and all five jobs
in Actions run `32561918020`; evidence is in
`evidence/gates/RM-100/2026-08-22-live-product-foundation.md`. RM-101 checkpoint
`3237144` added the Java v1 operations read response with explicit
merchant/courier projections and bounded health summary. Local gates and all
five Actions jobs in run `32562416957` passed; evidence is in
`evidence/gates/RM-101/operations-read-api.md`. RM-102 is implemented and
CI-validated with durable command idempotency, role-aware lifecycle validation,
expected-version conflicts, and transactional Outbox commands. Checkpoint
`ad988bc` and Actions run `32563322826` passed all five jobs; evidence is in
`evidence/gates/RM-102/order-command-api.md`. Continue with RM-103.
RM-103 adds bounded candidate validation, versioned strategy decisions, travel
provider metadata, and explicit 503 strategy/travel failure responses. Local
full gate passed; evidence is in `evidence/gates/RM-103/dispatch-api.md`.
Checkpoint `7506a5d` and Actions run `32563779670` passed all five jobs.
Continue with RM-104. The web source boundary has local evidence in
`evidence/gates/RM-104/web-live-data-source.md`; push and observe CI, then
continue with RM-105.
RM-105 defines the v1 event-stream item schema, monotonic decimal cursor,
exclusive `Last-Event-ID` reconnect, replay provenance, stale-state semantics,
and supported event types. Local contract evidence is in
`evidence/gates/RM-105/realtime-contract.md`; checkpoint `3c218e5` and Actions
run `32564387503` passed all five jobs. Continue with RM-106.
RM-106 adds a bounded read-only Java SSE projection over durable Outbox events,
exclusive decimal reconnect cursors, explicit stale conflicts, and bounded
subscriber-loss logging. Local full gate passed with 57 Java tests, 59 Python
tests at 96.13% coverage, 5 schemas/15 fixtures, and 9 Web unit tests plus build.
Evidence is in `evidence/gates/RM-106/java-sse.md`; checkpoint `21beadc` and
Actions run `32565242420` passed all five jobs. RM-107 evidence is in
`evidence/gates/RM-107/web-realtime.md`; checkpoint `48ef6fa` and Actions run
`32565914443` passed all five jobs. Continue with RM-108.
RM-108 adds the verified live activity projection with cursor, trace, freshness,
and explicit Demo/Replay labels. Local full gate passed with 15 Web unit tests,
16 Playwright tests, Java 57 tests, Python 59 tests at 96.13% coverage, and
5 schemas/15 fixtures. Checkpoint `4181f3c` and Actions run `32566340978` passed
all five jobs. Continue with RM-110.
RM-110 adds explicit operations projection loading/degraded/unavailable states,
source and freshness metadata, projection health, exception visibility, and
route-geometry fallback handling. Local full gate passed with 17 Web unit tests,
16 Playwright tests, Java 57 tests, Python 59 tests at 96.13% coverage, and
5 schemas/15 fixtures. Checkpoint `4b4ab79` and Actions run `32567110886` passed
all five jobs. RM-110 is now passed; continue with RM-111.
RM-111 defines the provider-neutral geospatial map contract and deterministic
local schematic fallback. It validates WGS84 coordinates and bounds, carries
markers/routes/zones/selection and freshness, and makes tile/routing capability
explicit without paid credentials. Local full gate passed with 21 Web unit
tests, 16 Playwright tests, Java 57 tests, Python 59 tests at 96.13% coverage,
and 5 schemas/15 fixtures. Checkpoint `d73be4f` and Actions run `32567620315`
passed all five jobs. RM-111 is now passed; continue with RM-112.
RM-112 connects the provider-neutral adapter to the operations map. Explicit tile
templates render a provider layer and attribution; no template keeps the local
schematic fallback visibly labeled and routing remains not configured. Local full
gate passed with 22 Web unit tests, 16 Playwright tests, Java 57 tests, Python 59
tests at 96.13% coverage, and 5 schemas/15 fixtures. Checkpoint is awaiting
Actions validation. Checkpoint `e199a9a` and Actions run `32568087013` passed all
five jobs. RM-112 is now passed; continue with RM-113.
RM-113 adds functional zone/lifecycle/exception/freshness filters and order/courier
detail panels. Local full gate passed with 23 Web unit tests, 16 Playwright tests,
Java 57 tests, Python 59 tests at 96.13% coverage, and 5 schemas/15 fixtures.
Checkpoint is awaiting Actions validation. Checkpoint `549fb87` and Actions run
`32568470723` passed all five jobs. RM-113 is now passed; continue with RM-114.
RM-114 adds a recorded exception queue with order-linked inspection, snapshot-derived
supply/demand imbalance, and an explicit unavailable overtime-risk state. Local full
gate passed with 24 Web unit tests, 16 Playwright tests, Java 57 tests, Python 59
tests at 96.13% coverage, and 5 schemas/15 fixtures. Checkpoint is awaiting Actions
validation.
Checkpoint `550f2a2` and Actions run `32568845070` passed all five jobs. RM-114 is
now passed; continue with RM-120.
RM-120 connects the customer role to the Java-owned durable order command path,
including idempotency, validation/conflict/timeout states, trace metadata, and
explicit demo/replay write protection. Realtime `order.created` events now add
orders to an empty live projection and forward lifecycle events retain versions.
Local full gate passed with Java 57 tests, Python 59 tests at 96.13% coverage,
Web 29 unit tests and build, 16 Playwright tests, and 5 schemas/15 fixtures.
Checkpoint `fbecdd0` and Actions run `32569640180` passed all five jobs. RM-120 is
now passed; RM-121 checkpoint `b4e1694` and Actions run `32572069719` also passed
all five jobs. RM-121 full gate evidence is recorded at
`evidence/gates/RM-121/merchant-workflow.md`.
RM-121 adds Java-owned merchant preparation states, validated actor permissions,
durable Flyway status expansion, transition persistence repair, and a merchant UI
that drives accept, start preparation, and mark ready commands with idempotency,
expected versions, traces, and explicit degradation. Local full gate passed with
Java 59 tests, Python 59 tests at 96.13% coverage, Web 31 unit tests/build, 16
Playwright tests, and 5 schemas/15 fixtures. RM-122 courier shift and delivery
workflow passed local and remote validation in Actions run `32573723273` (all five
jobs green).
RM-122 adds durable courier shift state, courier location commands with idempotent
outbox events, optional `ACCEPTED` and `ARRIVED` order audit states, courier order
commands through delivery completion, and explicit live/degraded projection state.
Local full gate passed with Java 60 tests, Python 59 tests at 96.13% coverage, Web
34 unit tests/build, 16 Playwright tests, and 5 schemas/15 fixtures. Evidence is
recorded at `evidence/gates/RM-122/courier-workflow.md`; remote Actions run
`32573723273` passed all five jobs. RM-123 role command error/degradation handling
passed local and remote validation in Actions run `32574390001` (all five jobs
green).
RM-123 role command adapters classify failures as conflict, validation, timeout, or
unavailable while preserving the original idempotency key and trace context; live
degraded snapshots disable writes with an explicit reason. Local full gate passed
with Java 60 tests, Python 59 tests at 96.13% coverage, Web 36 unit tests/build, 16
Playwright tests, and 5 schemas/15 fixtures. Evidence is recorded at
`evidence/gates/RM-123/role-degraded-states.md`; remote Actions run `32574390001`
passed all five jobs.
RM-124 adds a keyboard-dismissible mobile navigation drawer, 44px role links,
responsive courier/customer/merchant action layouts, and mobile browser/axe
coverage. Local full gate passed with Java 60 tests, Python 59 tests at 96.13%
coverage, Web 38 unit tests/build, 17 Playwright passes plus one desktop-only skip,
and 5 schemas/15 fixtures. Evidence is recorded at
`evidence/gates/RM-124/mobile-workflows.md`; remote Actions run `32575052384`
passed all five jobs. RM-130 constraint-aware dispatch model is now locally complete.
RM-130 adds optional capacity, current load, courier state, availability bounds,
service risk, estimated travel, pickup readiness, service duration, delivery time
windows, and a maximum risk threshold to the compute-owned DispatchProblem. All
registered baseline strategies use the shared eligibility boundary and return
stable infeasibility reasons; the API exposes eligible counts and reason metadata.
Local full gate passed with Java 60 tests, Python 65 tests at 96.47% coverage, Web
38 unit tests/build, and 5 schemas/15 fixtures. Evidence is recorded at
`evidence/gates/RM-130/constraint-dispatch-model.md`; Actions run `32575824899`
passed all five jobs. RM-131 capacity, preparation, and risk-aware scoring is now
the active task.
RM-131 registers the versioned `risk-aware` strategy with deterministic weights for
distance, pickup readiness, overtime risk, service risk, and courier load balance.
The same constrained fixtures remain available to nearest, weighted-greedy,
Hungarian, and risk-aware strategies; rationale and weight metadata are recorded
in each decision. Local full gate passed with Java 60 tests, Python 69 tests at
96.57% coverage, Web 38 unit tests/build, and 5 schemas/15 fixtures. Evidence is
recorded at `evidence/gates/RM-131/risk-aware-scoring.md`; remote Actions run
`32576213676` passed all five jobs. RM-132 minimum-cost flow and partitioned
assignment is now locally complete.
RM-132 adds a bounded successive-shortest-augmenting-path solver for rectangular
request/courier matrices, courier capacity, deterministic residual rematching, and
explicit unassigned reasons. `partitioned-assignment` reuses the solver per zone
without crossing courier partitions; single-order calls remain registry-compatible
and record assignment mode/count metadata. Local full gate passed with Java 60
tests, Python 74 tests at 96.03% coverage, Web 38 unit tests/build, and 5
schemas/15 fixtures. Evidence is recorded at
`evidence/gates/RM-132/flow-assignment.md`; remote Actions run `32576849657`
passed all five jobs. RM-132 is fully validated. RM-140 dynamic travel model
contract passed local/full validation and remote Actions run `32577433788` (all
five jobs green). Evidence is recorded at
`evidence/gates/RM-140/dynamic-travel.md`. RM-141 network and zone travel
provider is now the active task.
RM-141 network and zone travel provider is locally complete. The bounded
network fixture provides deterministic shortest paths, route geometry, edge and
zone metadata, matrix reuse, and explicit unavailable-route fallback. Local
full gate passed with Java 60 tests, Python 80 tests at 95.32% coverage, Web 38
unit tests/build, and 5 schemas/15 fixtures. Evidence is recorded at
`evidence/gates/RM-141/network-travel.md`; checkpoint is awaiting remote Actions
validation.
RM-141 remote Actions run `32577972174` passed all five jobs; the task is fully
validated. RM-142 data-root matrix and artifact adapter is now the active task.
RM-142 is locally complete: manifests carry canonical artifact metadata and
digests, the adapter resolves only inside `ROUTEMIND_DATA_ROOT`, and checksum or
path failures are explicit. Local full gate passed with Java 60 tests, Python
85 tests at 95.22% coverage, Web 38 unit tests/build, and 5 schemas/15
fixtures. Evidence is recorded at
`evidence/gates/RM-142/data-root-adapter.md`; checkpoint is awaiting remote
Actions validation.
RM-142 remote Actions run `32578382074` passed all five jobs; the task is fully
validated. RM-143 traffic and incident travel updates is now the active task.
RM-143 is locally complete: versioned simulated updates apply by effective time,
zone, edge, and incident, while context replay digests and provider metadata
remain deterministic. Local full gate passed with Java 60 tests, Python 89 tests
at 96.40% coverage, Web 38 unit tests/build, and 5 schemas/15 fixtures.
Evidence is recorded at `evidence/gates/RM-143/traffic-updates.md`; remote
Actions run `32579007370` passed all five jobs and the task is fully validated.
RM-150 continuous Digital Twin state kernel is now the active critical-path
task.
RM-150 is locally complete: `TwinClock` separates forward-only simulated time
from wall-clock observation, and the seeded scenario kernel records simulated
end tick without polluting replay digest. Local full gate passed with Java 60
tests, Python 90 tests at 96.37% coverage, Web 38 unit tests/build, and 5
schemas/15 fixtures. Evidence is recorded at
`evidence/gates/RM-150/continuous-twin.md`; remote Actions run `32579369219`
passed all five jobs and the task is fully validated. RM-151 continuous demand
arrival generator is now the active task.
RM-151 is locally complete: `DemandArrivalGenerator` uses explicit seeded
Bernoulli decisions per active tick, deterministic burst expansion and ordering,
profile metadata propagation, and a canonical replay digest. Local compute and
full gates pass with Java 60 tests, Python 92 tests at 96.34% coverage, Web 38
unit tests/build, and 5 schemas/15 fixtures. Evidence is recorded at
`evidence/gates/RM-151/demand-arrivals.md`; remote Actions run `32581545061`
passed all five jobs; RM-151 is fully validated. RM-153 dynamic merchant
preparation model is now the active task.
RM-153 is locally complete: `MerchantPreparationModel` schedules expected and
actual preparation on deterministic capacity slots, exposes queue load,
readiness and evolving late risk, and applies actual-ready state to dispatch.
Compute check passes 96 tests at 96.16% coverage; evidence is recorded at
`evidence/gates/RM-153/merchant-preparation.md`; full repository gate and
remote Actions run `32582291443` passed all five jobs. RM-153 is fully
validated. RM-154 traffic, supply, and failure perturbation modeling is now
the active task.
RM-154 is locally complete: `PerturbationScenario` emits bounded, windowed
traffic, supply, merchant-delay, and dependency-failure events, feeds traffic
into `DynamicTravelContext`, and separates simulated from live failure metrics.
Full local gate passes Java 60, Python 100 at 95.96%, Web 38 unit tests/build,
and 5 schemas/15 fixtures. Evidence is recorded at
`evidence/gates/RM-154/twin-perturbations.md`; remote Actions run
`32582936237` passed all five jobs. RM-154 is fully validated.

RM-155 remains blocked because RM-152 depends on RM-133. The next unblocked
critical task is RM-160, which exposes the compute-owned strategy registry and
bounded execution API while preserving versioned provenance and explicit
failure metadata.

RM-160 is fully validated. The compute catalog and bounded execution API are
covered by 104 Python tests at 95.78%, full local gates, browser smoke (17
passed plus one desktop-only skip), and GitHub Actions run `32600128160` with
all five jobs green. The task graph now activates RM-161, which depends on
RM-160 and RM-090 and adds versioned strategy parameter schemas and experiment
provenance.

RM-161 is fully validated after remote Actions run `32600780985` passed all
five jobs. It adds bounded
versioned parameter schemas for weighted-greedy and risk-aware, preserves
generic RouteBench manifest metadata separately from strategy parameters, and
adds `POST /api/v1/experiments/routebench` backed by the existing seeded
RouteBench/ScenarioKernel. Compute check passes 109 tests at 95.39%; full
available gates pass Java 60, Web 38 unit/build, and 5 schemas/15 fixtures.
The task graph now activates RM-163; RM-162 remains blocked by RM-156.

RM-163 is fully validated after remote Actions run `32601227912` passed all
five jobs. The new shadow
evaluation endpoint exposes active/candidate comparisons, ordered observations,
assignment/disagreement/failure metrics, promote/hold reasons, manifest/run
digests, and `candidate_authority: none`, while preserving active-strategy
authority and bounded candidate failures. Compute check passes 111 tests at
95.41%; full available gates pass Java 60, Web 38 unit/build, and 5
schemas/15 fixtures. The task graph now activates RM-133, the VRP/VRPTW
strategy baseline; RM-155 remains dependency-blocked until RM-133 and RM-152
pass.

RM-133 is fully validated after remote Actions run `32602269612` passed all five
jobs. It adds the bounded deterministic
`VrptwRoutePlanner`, the `vrptw` registry strategy, explicit capacity/service/
time-window/availability checks, stable unassigned reason codes, and a
two-stop reproducible reference baseline. Compute check passes 119 tests at
95.57%; full available gates pass Java 60, Web 38 unit/build, and 5 schemas/15
fixtures. The task graph now activates RM-134 dynamic insertion; RM-152 is also
unblocked while RM-162 remains blocked by RM-156.

RM-134 is fully validated after remote Actions run `32602785200` passed all five
jobs. `VrptwRoutePlanner.insert` evaluates
all positions against the active route snapshot, returns an immutable proposed
route with incremental travel cost, and emits stable identity, capacity,
time-window, availability, and bounded-limit rejection codes. Compute check
passes 122 tests at 95.56%; full available gates pass Java 60, Web 38
unit/build, and 5 schemas/15 fixtures. Evidence is recorded at
`evidence/gates/RM-134/dynamic-insertion.md`. The task graph now activates
RM-135 dynamic replanning; RM-152 is also unblocked while RM-162 remains
blocked by RM-156.


RM-135 is fully validated after remote Actions run `32603303249` passed all
five jobs. `DynamicReplanningPolicy` covers arrival, lateness, incident,
courier-loss, and material-change triggers with deterministic improvement
gating, debounce/cooldown state, trace, and before/after metrics. Compute check
passes 131 tests at 95.66%; full available gates pass Java 60, Web 38
unit/build, and 5 schemas/15 fixtures. The task graph now activates RM-152
courier motion; RM-162 remains blocked by RM-156.


RM-152 local implementation is complete. `CourierMotionEngine` advances an
immutable route with the existing travel-provider abstraction, interpolates
locations in simulated time, emits stable route/arrival/pickup/delivery/
completion events, and returns idle/en-route/servicing/available state. The
snapshot includes a canonical replay digest and a Redis GEO-compatible
`(longitude, latitude, member)` projection; Redis remains rebuildable hot state.
Compute check passes 135 tests at 95.46%; full available gates pass Java 60,
Web 38 unit/build, and 5 schemas/15 fixtures. Evidence is recorded at
`evidence/gates/RM-152/courier-motion.md`. GitHub Actions run `32603896737`
passed all five jobs, including browser smoke;
RM-152 is fully validated and RM-155 is now active.

RM-155 local implementation is complete. `TwinControlService` wraps the
existing `ScenarioKernel` in a bounded process-local control boundary and the
FastAPI adapters expose `/api/v1/twin/control` plus `/api/v1/twin/state`.
Commands cover start/pause/resume/step/reset/speed/scenario/seed/strategy,
advance only simulated time, and use recent `command_id` deduplication with
explicit 409 conflicts. State/events carry strategy version, simulated time,
generation, deterministic event IDs, and canonical replay digest. Compute check
passes 139 tests at 95.71%; full available gates pass Java 60, Web 38
unit/build, and 5 schemas/15 fixtures. Evidence is recorded at
`evidence/gates/RM-155/twin-control-api.md`. GitHub Actions run `32604701074`
passed all five jobs, including browser smoke; RM-155 is fully validated and
RM-156 is now active.

RM-156 local implementation is complete. The Operations surface now has a
distinct simulation data source backed by the Python Twin API, with scenario,
seed, speed, strategy, step, pause/resume, and reset controls. Existing map,
routes, lifecycle, metrics, exceptions, and health regions remain visible while
simulated time, seeded traffic/supply/demand metrics, replay digest, and recent
events are explicit. Web check passes 42 unit tests/build; browser smoke passes
19 tests with one existing desktop-only skip, including the new desktop/mobile
simulation control flow. Evidence is recorded at
`evidence/gates/RM-156/twin-ui.md`. GitHub Actions run `32605590683` passed all
five jobs, including browser smoke; RM-156 is fully validated and RM-157 is now
active.

RM-157 local implementation is complete. The replay source verifies a
canonical SHA-256 artifact before enabling playback, exposes scenario/seed/
provenance and explicit replay-vs-live labeling, and supports play, pause,
reset, seek, step, speed, and event detail inspection. Web check passes 43
unit tests/build; browser smoke passes 21 desktop/mobile tests with one
existing desktop-only skip; the full available gate passes Java 60, Python 139
at 95.71%, and 5 schemas/15 fixtures. Evidence is recorded at
`evidence/gates/RM-157/replay.md`. The implementation checkpoint is `c8d2ac2`.

RM-157 is fully validated after GitHub Actions run `32606493460` passed all five
jobs, including the Web static, unit, and browser smoke gates. The task graph
now records RM-157 passed (40/48 Round 2, 68/76 repository) and activates
RM-158 What-if scenario comparison.

RM-158 local implementation is complete. The compute-owned What-if runner and
`POST /api/v1/experiments/what-if` derive bounded demand, supply, preparation,
traffic, strategy, and risk variants from a recorded manifest and return
reproducible replay/manifest/output/comparison digests. The Strategy surface
exposes controls, baseline/variant metrics, loading/error/clear states, and
explicitly labels results as scenario comparisons rather than causal production
claims. Compute check passes 142 Python tests at 95.88%; Web check passes 47
unit tests/build; browser smoke passes 23 desktop/mobile tests with one
existing desktop-only skip; full available gates pass Java 60 and 5 schemas/15
fixtures. Evidence is recorded at `evidence/gates/RM-158/what-if.md`; the
implementation checkpoint is `90f85ea`.

RM-158 is fully validated after GitHub Actions run `32607641909` passed all five
jobs, including the Python compute and Web browser smoke gates. The task graph
now records RM-158 passed (41/48 Round 2, 69/76 repository) and activates
RM-162 strategy comparison visualizations; RM-160 and RM-161 are already passed.

RM-162 local implementation is complete. The Strategy Comparison panel uses a
bounded multi-variant What-if request and renders actual assignment rate,
simulated duration, observed compute runtime, and scenario-risk bars. It keeps
recorded-run, comparison, replay, manifest, and output digests visible, while
completion, overtime, distance, utilization, fairness, and cost are explicitly
shown as unavailable from the recorded run. Web check passes 49 tests/build;
browser smoke passes 23 desktop/mobile tests with one existing desktop-only
skip; full available gates pass Java 60, Python 142 at 95.88%, and 5 schemas/15
fixtures. Evidence is recorded at `evidence/gates/RM-162/strategy-comparison.md`;
the implementation checkpoint is `95901cd`.

RM-162 is fully validated after GitHub Actions run `32608343277` passed all five
jobs, including Python compute and Web browser smoke. The task graph now records
RM-162 passed (42/48 Round 2, 70/76 repository) and activates RM-136 advanced
dispatch integration and audit; RM-170 remains blocked by RM-136.

## Current Resume Capsule
- Resume at RM-230 Reliability Center surface. Preserve Java lifecycle
  authority, durable location sequence ordering, Redis-as-projection, and the
  explicit non-disciplinary anomaly boundary and honest ETA lineage boundary.
- RM-215 evidence is `evidence/gates/RM-215/reconciliation.md`; checkpoint
  `d26a121` and GitHub Actions run `32647766636` passed all five jobs.
- Round 2 remains 48/48, Hardening remains 10/10, and Enhancement is 19/27 with
  RM-230 active. Repository total is 105/113. RM-228 remains independently
  eligible, while RM-230 is the active reliability sequence.
- Human action required: NONE. Keep `.codex-tmp/` untouched and untracked.

### R4-422 V2 closure and credential lifecycle audit - 2026-08-30

The consumed V2 fail-closed execution was closed in checkpoint `1b7c41021f914bd2f1eb367fd3d417345729304d`, whose first remote CI run was `33290111559`. That run passed Python, Web, Resilience, and Java, but the control-plane security gate rejected a local token variable name lexically; no provider or credential operation occurred. The smallest source-only naming repair was committed separately as `3752f205d5d5e5cb5670ed03d86801dca0eb21e8` and passed all five jobs in remote CI run `33290659144`.

The strictly offline lifecycle audit is recorded in `evidence/gates/R4-422/google-gmail-credential-lifecycle-offline-audit-20260830.*`. Source and cached Google OAuth bytecode show the refresh and V2 processes use the same external-store path policy, user-key loading algorithm, and automatic DataStore refresh listener. The historical evidence does not retain path identity or post-refresh store metadata, so the historical cause is classified as `EXTERNAL_CREDENTIAL_BEHAVIOR_REQUIRES_FURTHER_EVIDENCE` with low root-cause confidence. No local credential defect was confirmed and no Phase 3 credential repair was performed. All new external-operation counters remain zero. Do not reuse the consumed V2 contract; any future credential or send operation requires a new independent contract and Human Gate.

Gmail exactly-one synthetic send Human Gate preparation (2026-08-29): the new
independent contract
`contracts/provider/r4-422-google-gmail-single-send-validation-v1.json` has
canonical SHA-256
`16e6f9dd68fd261f28047b0e7ea8e2f19e186ba3c04dd68c7c8a7d3606dea663`.
It is `PREPARED_OFFLINE / HUMAN_GATE_PENDING / NO_GMAIL_API_CALL / NO_EMAIL_SENT`.
The future bounded operation is exactly one Gmail API v1
`users.messages.send` request to one synthetic recipient with `gmail.send`
only, the existing external Windows token store, a 15-minute window, and a
USD 0.10 ceiling. OAuth/browser/SSH, retries, fallback, reads, batch, drafts,
attachments, CC/BCC, account/resource mutation, and production claims are
forbidden. Google-managed processing is not claimed Tokyo-pinned.

The known repository-external token store is present, while the current Codex
Process/User scopes do not expose `ROUTEMIND_GMAIL_TOKEN_STORE`; execution must
set that non-secret path reference and re-run preflight before any Gmail call.

Preparation made no Gmail, OAuth, browser, SSH, or mutation call. Existing
Gmail OAuth V2 and all historical SES evidence remain unchanged. Redacted
preparation and leakage evidence are under
`evidence/gates/R4-422/google-gmail-single-send-*`. Exact next human action:
approve the new contract digest before any Gmail API request.

Gmail OAuth bootstrap V2 preparation (2026-08-29): independent contract
`contracts/provider/r4-422-google-gmail-oauth-bootstrap-v2.json` is prepared
with SHA-256
`e6fc0dec19ea96c2eaee337694e7a0a19716e5491ea4b50d9be09892391ca22e`.
It starts the Windows OAuth listener on loopback before emitting any URL and
requires one operator-managed strict loopback SSH forward to
`suzhe@10.10.1.27`. The operator runs SSH separately and enters the Mac
password manually; RouteMind never starts SSH or reads password bytes. One Mac
`/routemind-oauth-preflight` request must return
`ROUTEMIND_GMAIL_OAUTH_TUNNEL_READY` before the single `gmail.send` OAuth URL
is generated. The future stage permits one session, one callback, and one token
exchange, with no Gmail message operation, email send, retry, fallback, or
mutation. No SSH, preflight, OAuth, Google, Gmail, or mutation call occurred
in preparation. State:
`BLOCKED / OAUTH_BOOTSTRAP_V2_HUMAN_GATE_PENDING / NO_PRODUCTION_CLAIM`.
Evidence is under
`evidence/gates/R4-422/gmail-oauth-bootstrap-v2-preparation-20260829.*`.
Historical contracts/evidence and R3-325 remain unchanged.

V2 implementation checkpoint is commit
`371312058b64786b92a5c65db88d2dda0e446a75`; real GitHub Actions run
`33254290292` is green across all five jobs. The prior run's Linux-only test
fixture failure was repaired with a portable absolute temporary path; no
production dependency or OAuth behavior changed.

V2 execution evidence checkpoint is commit
`e63df42706bd60298e83d6234b83acd32a394d03`; real GitHub Actions run
`33255445994` is green across all five jobs.

Gmail OAuth bootstrap V2 execution closure: contract
`e6fc0dec19ea96c2eaee337694e7a0a19716e5491ea4b50d9be09892391ca22e` was
consumed once. The strict operator-managed loopback SSH forward passed one
preflight; one `gmail.send` OAuth session consumed one callback and completed
one Windows token exchange. Credentials remain only in the external Windows
token store. Listener and SSH tunnel teardown are complete. No Gmail message,
email send, retry, fallback, mutation, or production claim occurred. Evidence:
`evidence/gates/R4-422/gmail-oauth-bootstrap-v2-execution-20260829.json`,
`.md`, and `-leakage-scan-20260829.json`. Observed cost is USD 0.00. Any
future Gmail message/send operation requires a new contract and Human Gate.

## Tokyo VM execution attempt 1 - 2026-08-27

The exact approved VM contract `2c6bd381ea8bdbf6a2c91864ec4bbf7589d434b19f043375322138ad7bfc608a` was applied once under execution
`r4-vm-20260826t182938z-d3255b7d6c`. Read-only provider preflight proved `nrt`
Tokyo, both approved VM plans, Ubuntu 24.04 x64, the configured SSH key, exact
operator `/32`, and an authenticated six-hour quote of USD 1.476.

The exact six-create plan passed: two instances, one VPC, one firewall group,
and two firewall rules. Vultr then rejected the VPC create with HTTP 400 because
the account had reached the five-VPC-per-location quota. No VM or VPC was
created. The execution firewall group and its two exact rules were the only
created identities; Terraform destroyed all three with an exact partial destroy
plan. Provider readback returned firewall identity `404` and zero resources
matching the execution label. No workload, telemetry backend, recovery package,
or customer data ran; conservative execution cost is USD 0.00.

Immutable details are in
`evidence/gates/R4-405/2026-08-27-tokyo-vm-execution-attempt-1.md`.
R4-405/R4-406 remain `TARGET_PENDING`; this is not target evidence and does not
establish a provider or root-cause claim. The consumed contract digest may not
be reused. A future retry needs a new safe quota/topology decision and a new
exact Human Gate. R3-325 remains exactly
`E-PASS / X-PASS / S-FAIL / C-NO-CLAIM`.

The evidence checkpoint `e6e009f` passed all five required jobs in real GitHub
Actions run `33000804025`; final closure checkpoint `1ac8320` passed all five
required jobs in run `33001205407`. CI validates repository controls only and
does not qualify the target. The exact execution state was removed after
cleanup verification.

RM-216 closure, RM-217 implementation, RM-218 notes, and RM-219 status: checkpoint `c98ea76` is
remote-green in Actions run `32649193769`, and RM-217 checkpoint `7234ff6` is
remote-green in Actions run `32650330974`. V15 adds bounded courier location
history; event sequence and ingestion metadata are propagated to operations
snapshots and Web realtime handling. RM-218 adds read-oriented integrity states
and privacy-bounded hotspots; checkpoint `a61b559` is remote-green in Actions
run `32651238530`. RM-219 checkpoint `8fab1a6` is remote-green in Actions run
`32651955908`; it implements a deterministic five-component ETA baseline with
explicit unavailable inputs and outcome lineage. RM-220 local evidence is 201
Python tests at 95.23%, full available gate green, and explicit calibration-
confidence gating. RM-220 is fully validated in Actions run `32652719384`.
RM-221 is fully validated in Actions run `32653393681`; keep the waterfall
descriptive and reconcile observed duration without causal claims. RM-222 is
fully validated in Actions run `32654207318`. RM-223 is fully validated in
Actions run `32655392123`; evidence is recorded in
`evidence/gates/RM-223/city-zone-drilldown.md`. Continue autonomously with
RM-224. Its local evidence is recorded in
`evidence/gates/RM-224/arc-flow.md`; preserve order-route lineage and explicit
empty/stale/unavailable states. RM-225 is fully validated in Actions run
`32657006258`; evidence is recorded in `evidence/gates/RM-225/geo-layers.md`.
RM-226 is closed in checkpoint `470d67f` with evidence in
`evidence/gates/RM-226/decision-xray.md` and Actions run `32658324255`.
RM-227 is closed in checkpoint `c63d336` with evidence in
`evidence/gates/RM-227/strategy-analytics.md` and Actions run `32659202824`.
RM-233 is closed in checkpoint `b5174d8` with evidence in
`evidence/gates/RM-233/reference-data-versioning.md` and Actions run
`32659704665`.
Continue autonomously with RM-230.

## Current Research Resume Capsule
- Workstream: B - Statistical RouteBench.
- Current task: R3-321 common-random-number stream ownership.
- Engineering Gate: E-IN-PROGRESS.
- Experiment Gate: X-NOT-REQUIRED.
- Statistical Gate: S-NOT-APPLICABLE.
- Claim Gate: C-NOT-APPLICABLE.
- R3-311 evidence: `evidence/gates/R3-311/solomon-vrptw.md`; compact result
  `docs/research/r3/results/solomon/solomon-stratified-six-results-v1.json`.
- R3-311 CI: preregistration run `32697011223`, implementation run
  `32699067563`, and closure run `32699784206` passed all five jobs.
- R3-311 result: campaign `r3-311-20260824T065444Z-8a0a4ea5c098` retained all
  six; 4 verified complete incumbents, 2 no-incumbent timeouts, Wilson 95%
  `[0.299993, 0.903229]`, final `E-PASS/X-PASS/S-FAIL/C-NO-CLAIM`.
- R3-315 evidence: `evidence/gates/R3-315/exact-cross-check.md`; compact result
  `docs/research/r3/results/exact-cross-check/solomon-prefix-eight-exact-results-v1.json`.
- R3-315 CI/results: preregistration run `32700423191` and implementation run
  `32701927556` passed all five jobs. Campaign
  `r3-315-20260824T073439Z-1bae0447b562` retained 6/6; complete enumeration,
  CP-SAT `OPTIMAL`, independent verification, and 0% transformed candidate gaps
  held for all six. Proof scope is the derived conservative model only.
- R3-312 protocol: replicate `_1` for all six structural families at each of
  200/400/600/800/1000 customers, 30 total; five seconds, one thread, one
  isolated process each. Archive/member hashes are frozen under the external
  data root, and questioned/marked SINTEF references cannot receive scalar gaps.
  Manifest SHA-256 is
  `6c35a47e03d53a71f32240953fe1a088412637b893cb6d5a25a924a7bef9a2d2`.
- R3-312 implementation revision `eac087e` passed all five jobs in Actions run
  `32706450863`. Campaign `r3-312-20260824T083216Z-eac087e32790` then retained
  all 30 results: 29 verified complete incumbents and one no-incumbent timeout.
  The 200 scale was 5/6 and larger scales were each 6/6 under the frozen policy.
- Every R3-312 incumbent used more vehicles than its retained reference; there
  were no same-vehicle scalar distance gaps. External audit verified 31 JSON
  files plus 31 sidecars with zero errors. Compact result is
  `docs/research/r3/results/gehring-homberger/scale-first-replicates-results-v1.json`
  with SHA-256 `45ad7967cac4985d869663b6f5208e03c26e18995d33b6903535d8b627460daf`.
- R3-312 is `E-PASS/X-PASS/S-NOT-APPLICABLE/C-NO-CLAIM`. R3-316 now owns the
  frozen all-outcome protocol for median, p90, best, worst, timeout, infeasible,
  and reference-comparability results across R3-311, R3-312, and the scoped
  transformed-model R3-315 evidence.
- R3-312 closure revision `4f678fd` passed all five jobs in Actions run
  `32707794770`.
- R3-316 manifest `r3-316-bks-gap-analysis-v1` is frozen with SHA-256
  `6c6332896dff30e878f77a161e576b88b42422cc2e2a617c1fa4f43f9ca6f77b`.
  It binds all 42 upstream records and keeps 36 source-BKS results separate from
  six derived exact results. Vehicle gap, conditional same-vehicle distance gap,
  and transformed exact gap use separate Type-7 distributions; all outcome rates
  retain failures and no-incumbent results.
- The R3-316 freeze is explicitly post-inspection, not blinded preregistration.
  Direct run `32708520338` was concurrency-cancelled; descendant `d86c41e`
  contains the unchanged freeze and passed all five jobs in run `32708578105`.
- R3-316 implementation revision `9f68e99` passed all five jobs in Actions run
  `32710816931`. Campaign `r3-316-20260824T092121Z-9f68e9902a9b` then retained
  all 42 records with zero exclusions/errors: 32 timeout-with-feasible, three
  timeout-no-feasible, and one feasible incumbent among 36 source results.
- Approved source vehicle gaps had `n=27`, median `31.6667%`, p90 `349.4545%`,
  and max `484.2105%`; conditional same-vehicle distance gaps had `n=4`, median
  `2.6745%`, p90 `8.8185%`, and max `10.3053%`. Six scoped transformed exact
  gaps were all `0%`; the domains were never pooled.
- Independent audit verified the immutable result SHA-256
  `6e5571fcba1fd7069e4eb6604fff3f70533495fe1970fb2b5c0df257514eefb1`,
  all inputs, exact artifacts, identities, formulas, and Type-7 summaries.
  Compact result is
  `docs/research/r3/results/gap-analysis/bks-gap-analysis-results-v1.json`.
- R3-316 is `E-PASS/X-PASS/S-PASS/C-NO-CLAIM`; no source optimality,
  superiority, or population claim is authorized.
- R3-316 closure revision `c0967c1` passed all five jobs in Actions run
  `32711507127`.
- R3-320 protocol `r3-320-statistical-routebench-v1` is locally frozen against
  that closure before any R3-B campaign data. It binds `risk-aware@1.0.0` versus
  `weighted-greedy@1.0.0`, an independent per-request risk formula, assignment
  margin `-0.02`, eight numeric stress regimes, four CRN streams, disjoint pilot
  and confirmatory seeds, prospective power bounds, a 16-test Holm family,
  mandatory safety diagnostics, exclusions/stopping, lineage, and zero cost.
- Strict loader and directed mutation tests must pass locally and remotely.
  Material R3-325 data remain prohibited until R3-321/322/323/324 and the R3-325
  implementation checkpoint pass. After remote R3-320 validation, close it and
  activate R3-321 immediately.
- R3-320 manifest is 9,737 bytes with SHA-256
  `a6dae9d55641ff7966ef4a50cc00a63da3e936620c3c48f23cd2c2ce039375b5`.
  Local full gates pass: Java 80/80, Python 544/544 at 95.76% (protocol loader
  97.46% across 51 directed tests), Web 92/92 plus build, 6 schemas / 18
  fixtures, determinism, analytics, semantic metrics, Ruff, and mypy.
- R3-320 freeze revision `8c592d4` passed all five jobs in Actions run
  `32713127743` and closes `E-PASS/X-NOT-REQUIRED/S-NOT-APPLICABLE/
  C-NOT-APPLICABLE`. R3-321 is active; implement the exact frozen SHA-256 seed
  derivation and prove stable demand/merchant/courier/traffic digests without
  claiming independent observations.
- Concurrent state: `465488f` implements the separate spatial-lock-in
  negative-control diagnostic. Preserve subsequent `research/level4/spatial_lockin/`
  changes and do not claim them as Round 3 task work.
- Human action required: NONE. Keep `.codex-tmp/` untouched and untracked.
