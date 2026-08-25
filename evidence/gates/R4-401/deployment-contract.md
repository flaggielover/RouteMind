# R4-401 Deployment Target Contract Evidence

Date: 2026-08-25 (Asia/Shanghai)

Entry revision: `6f7bc9b682e04301218a2ed70d259c577e8387e0`

Status: `LOCAL_VALIDATED / CI_PENDING`

## Human approval

The RouteMind owner explicitly approved Vultr in Tokyo, Japan as the current
real target platform and data-residency region. The approved scope is limited to
provider, target region, and residency selection.

The approval does not authorize resource creation, credentials use, spending,
or a production deployment claim. Those fields remain false in the executable
contract and fail closed under mutation tests.

## External read-only evidence

The public Vultr API returned region `nrt` as Tokyo, Japan, with Kubernetes,
load-balancer, high-performance Block Storage, storage-optimized Block Storage,
and DDoS options. The public plan catalog returned the selected worker and
backup-host plans as available in `nrt` at USD 48 and USD 24 monthly. No
credentialed or state-changing endpoint was called.

Official references:

- Region API: <https://api.vultr.com/v2/regions>
- Plan API: <https://api.vultr.com/v2/plans?per_page=500>
- VKE cost: <https://docs.vultr.com/support/products/vke/how-much-does-the-vultr-kubernetes-engine-cost>
- VKE HA: <https://docs.vultr.com/products/compute/kubernetes/features/high-availability>
- Load-balancer price: <https://docs.vultr.com/support/platform/billing/how-are-vultr-load-balancers-priced>
- Block Storage: <https://www.vultr.com/products/block-storage/>

The compact external evidence snapshot has SHA-256
`e9ee677ebacadcded020dc330760985ea35eb08112a8e1c085962ea5de44d133`.
Public catalog results do not prove account quota or authenticated regional
pricing, so both remain pre-provisioning gates.

## Frozen target

- Provider/region: Vultr `nrt`, Tokyo, Japan; one region.
- Orchestration: VKE with HA control plane requested and no multi-region claim.
- Compute: three initial 4 vCPU / 8 GiB workers, scalable only within the frozen
  three-to-six-node bound after qualification.
- Stateful services: three PostgreSQL replicas, three RabbitMQ quorum replicas,
  and three Redis/Sentinel replicas. Redis is not durable business truth.
- Ingress: one Vultr Load Balancer with TLS and health checks.
- Recovery storage: a private backup host and encrypted recovery packages in
  Tokyo. Provider automatic backups are disabled until residency is verified.
- Failure domain: Tokyo remains a single regional failure domain. There is no
  committed region-wide RPO or RTO.

The executable contract digest is
`7018f0a06e334d86a7caf5e0ea142275370a7af10cb2c9a7bf448724c43ce2aa`.

## Capacity, SLO, and cost assumptions

The qualification workload assumes 10 sustained dispatch requests per second,
a 25 RPS five-minute burst, 200 concurrent SSE connections, 1,000 active
courier locations, and 50,000 orders per day. These are inputs for R4-407, not
validated capacity.

Seven measurable objectives cover monthly API availability, dispatch latency,
event publication lag, SSE freshness, location freshness, and in-region
PostgreSQL RPO/RTO. The initial API objective is 99.5% per 30 days with a
216-minute error budget. In-region PostgreSQL targets are RPO at most 15 minutes
and RTO at most 120 minutes; R4-406 must prove them in the selected target.

Public-catalog recurring cost is USD 239 per month: USD 144 for workers, USD 24
for the backup host, USD 10 starting load-balancer price, USD 61 for 610 GiB of
Block Storage, and no additional VKE control-plane charge. The contract adds a
USD 61 contingency for a USD 300 planning ceiling. Taxes, egress overage,
regional variance, paid travel, notifications, and domain registration are
excluded and require a new authenticated quote. Spend authorization is false.

## Executable validation

- `python scripts/deployment_contract.py` -> PASS
- `python scripts/deployment_contract_test.py` -> PASS, 11 tests
- `python scripts/round4_graph_gate.py` -> PASS
- `python scripts/round4_graph_gate_test.py` -> PASS, 9 tests
- `python scripts/validate_control_plane.py` -> PASS
- `./scripts/full-gate.ps1` -> PASS
- `./scripts/web.ps1 e2e` -> PASS, 34 passed / 2 expected skips
- `./scripts/resilience.ps1` -> PASS, 15 Java / 2 Python tests

The full gate passed 110 Java tests, 920 Python tests at 95.11% coverage, 104
Web unit tests, formatting, lint, strict type checks, production build, all
control contracts, and Compose configuration.

Directed mutations reject provider/region drift, missing Tokyo capabilities,
resource/spend authorization, false deployment claims, Java/PostgreSQL
authority drift, hidden regional risk, weakened residency, local-capacity
promotion, missing SLOs, cost drift, source digest drift, and scientific claim
promotion.

## Claim boundary

Current maturity is `TARGET_SELECTED_NOT_DEPLOYED`. Local validation may support
`LOCAL_VALIDATED`, and clean GitHub Actions may support `CI_VALIDATED`. Neither
label proves that Vultr resources exist or that RouteMind runs in production.
Live and production labels require matching credentialed remote evidence in
later tasks.

GitHub Actions is pending for the implementation checkpoint. The task remains
`validating` until all five remote jobs pass.

R3-325 remains frozen exactly as
`E-PASS / X-PASS / S-FAIL / C-NO-CLAIM`; no Round 3 experiment was rerun or
reinterpreted.
