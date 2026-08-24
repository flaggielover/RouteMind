# Round 2 Evidence Index

Status: frozen literature-audit evidence registry
Audit date: 2026-08-24
Scope: targeted adversarial search, not a systematic review

## Claim labels

- `KNOWN`: definition, direct repository fact, or result explicitly established by
  a cited source.
- `SUPPORTED`: multiple relevant sources support the statement, but the audit is
  not exhaustive.
- `INFERRED`: reasoned synthesis from cited sources.
- `SPECULATIVE`: candidate mechanism or theorem that has not been demonstrated.
- `UNKNOWN`: the audit could not establish the claim.

The absence of a source in this registry is not evidence of novelty. Every
candidate must be presumed reducible until a specialist audit establishes a
nontrivial mathematical residue.

## On-demand delivery and preparation

- **S01** - Ulmer et al., *The Restaurant Meal Delivery Problem: Dynamic Pickup
  and Delivery with Deadlines and Random Ready Times*. `KNOWN`: stochastic ready
  times are already integrated into anticipatory dispatch and bundling.
  <https://pubsonline.informs.org/doi/10.1287/trsc.2020.1000>
- **S02** - Zhao, Papier, and Teo, *Market Thickness in Online Food Delivery
  Platforms: The Impact of Food Processing Times*. `KNOWN`: uncertain processing
  time, delayed matching, threshold structure, and nonmonotone market thickness
  are directly studied.
  <https://pubsonline.informs.org/doi/10.1287/msom.2021.0354>
- **S03** - Chen and Hu, *Courier Dispatch in On-Demand Delivery*. `KNOWN`:
  spatial queueing, temporal pooling, customer patience, and endogenous demand
  already generate dispatch-regime comparisons.
  <https://pubsonline.informs.org/doi/10.1287/mnsc.2023.4858>
- **S04** - Reyes et al., *The Meal Delivery Routing Problem*. `KNOWN`: the
  stochastic, dynamic meal-delivery routing problem and public instances predate
  RouteMind.
  <https://optimization-online.org/wp-content/uploads/2018/04/6571.pdf>
- **S05** - Ulmer and Thomas, *The Restaurant Meal Delivery Problem with Ghost
  Kitchens*. `KNOWN`: synchronization of food preparation and delivery is an
  explicit operational objective.
  <https://pubsonline.informs.org/doi/10.1287/trsc.2024.0510>
- **S06** - *Order Now, Pickup in 30 Minutes: Managing Queues with Static
  Delivery Guarantees*. `KNOWN`: online food-order queues and promised pickup
  times have an established queueing formulation.
  <https://pubsonline.informs.org/doi/10.1287/opre.2021.2203>
- **S07** - Fotouhi et al., *Assessing the Effects of Limited Curbside Pickup
  Capacity in Meal Delivery Operations*. `KNOWN`: pickup congestion is modeled;
  pickup timestamps provide only an upper bound on preparation completion when
  couriers arrive late.
  <https://journals.sagepub.com/doi/10.1177/0361198121991840>
- **S08** - Xie et al., *A causal discovery and inference framework for on-demand
  food delivery delays*. `SUPPORTED`: pickup and preparation effects are causally
  entangled and delay propagation can be nonlinear.
  <https://doi.org/10.1038/s44333-026-00097-1>
- **S09** - Mao et al., *Meituan's Real-Time Intelligent Dispatching Algorithms*.
  `KNOWN`: large-scale minute-level food-delivery matching is established applied
  work, not a new mathematical object by itself.
  <https://pubsonline.informs.org/doi/10.1287/inte.2023.0084>

## Queueing, censoring, and state dependence

- **S10** - Wu, Bassamboo, and Perry, *When Service Times Depend on Customers'
  Delays*. `KNOWN`: endogenous service-time dependence, censored observations,
  and observational equivalence between dependence mechanisms are established.
  <https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3378648>
- **S11** - Gill, van der Laan, and Robins, *Coarsening at Random:
  Characterizations, Conjectures and Counter-examples*. `KNOWN`: informative
  observation is governed by a mature coarsened-data framework.
  <https://dbc.library.uu.nl/handle/1874/1642>
- **S12** - Sakaguchi, *Partial Identification and Inference in Duration
  Models with Endogenous Censoring*. `KNOWN`: partial identification under
  endogenous censoring is already a general econometric object.
  <https://arxiv.org/abs/2107.00928>
- **S13** - Bambos and Walrand, *On the Stability of State-Dependent Queues and
  Acyclic Queueing Networks*. `KNOWN`: state-dependent service and network
  stability have classical theory.
  <https://www.cambridge.org/core/services/aop-cambridge-core/content/view/9D9F994A2102BD3024EF1AA82AC61636/S0001867800018875a.pdf/on_stability_of_statedependent_queues_and_acyclic_queueing_networks.pdf>
- **S14** - D'Auria et al., *An M/M/c Queue with Queueing-Time Dependent Service
  Rates*.
  `KNOWN`: service rates that depend on experienced delay have direct queueing
  analysis.
  <https://doi.org/10.1016/j.ejor.2021.12.023>
- **S15** - Castro, Nazerzadeh, and Yan, *Matching Queues with Reneging*.
  `KNOWN`: matching, compatibility, abandonment, and steady-state structure are
  directly studied.
  <https://arxiv.org/abs/2005.10728>

## Policy evaluation, interference, and reusable resources

- **S16** - Luo et al., *Policy Evaluation for Temporal and/or Spatial Dependent
  Experiments*. `KNOWN`: policy evaluation under nonstationarity, carryover,
  spatial spillovers, and interference is directly developed for ride-sharing.
  <https://academic.oup.com/jrsssb/article/86/3/623/7511800>
- **S17** - Zhang and Bareinboim, *Causal Eligibility Traces for Confounding
  Robust Off-Policy Evaluation*. `KNOWN`: value bounds under latent confounding
  and lack of support are already available.
  <https://proceedings.mlr.press/v286/zhang25d.html>
- **S18** - Hayashi, Goda, and Saito, *Off-Policy Evaluation and Learning for
  Matching Markets*. `KNOWN`: OPE estimators specialized to matching markets are
  direct prior art.
  <https://arxiv.org/abs/2507.13608>
- **S19** - Swaminathan et al., *Off-Policy Evaluation for Slate
  Recommendation*. `KNOWN`: combinatorial/slate action spaces do not by
  themselves create a new OPE object.
  <https://arxiv.org/abs/1605.04812>
- **S20** - Mate et al., *Improved Policy Evaluation for Randomized Trials of
  Algorithmic Resource Allocation*. `KNOWN`: counterfactual reuse in resource
  allocation experiments is established.
  <https://proceedings.mlr.press/v202/mate23a.html>
- **S21** - Delong et al., *Online Bipartite Matching with Reusable Resources*.
  `KNOWN`: reusable resources and stochastic return times have competitive
  online-matching theory.
  <https://arxiv.org/abs/2110.07084>
- **S22** - Dickerson et al., *Allocation Problems in Ride-Sharing Platforms:
  Online Matching with Offline Reusable Resources*.
  `KNOWN`: ride-sharing-type reusable resources have direct online matching
  formulations.
  <https://arxiv.org/abs/1711.08345>

## Strategic behavior, fairness, and platform control

- **S23** - Afeche, Liu, and Maglaras, *Ride-Hailing Networks with Strategic
  Drivers: The Impact of Platform Control Capabilities on Performance*. `KNOWN`:
  strategic participation and repositioning, platform
  admission/reposition controls, and performance conditions are direct prior art.
  <https://pubsonline.informs.org/doi/10.1287/msom.2023.1221>
- **S24** - Yang, Umboh, and Ramezani, *Freelance Drivers with a Decline Choice:
  Dispatch Menus in On-Demand Mobility Services for Assortment Optimization*.
  `KNOWN`: driver rejection is incorporated into dispatch-menu design.
  <https://doi.org/10.1016/j.trb.2024.103082>
- **S25** - Ekbatani et al., *Non-Exclusive Notifications for Ride-Hailing at
  Lyft II: Simulations and Marketplace Analysis*. `KNOWN`: simultaneous offers
  and acceptance contention have been studied with proprietary platform traces.
  <https://papers.ssrn.com/sol3/Delivery.cfm/6273598.pdf?abstractid=6273598>
- **S26** - *Long-Term Fairness in Ride-Hailing*. `KNOWN`: dynamic fairness and
  long-run driver outcomes are established research topics.
  <https://arxiv.org/abs/2407.17839>
- **S27** - *Labor Rights and the Algorithmic Dispatch of Food Delivery*.
  `KNOWN`: labor-sensitive dispatch objectives already have an explicit
  algorithmic formulation.
  <https://arxiv.org/abs/2109.14156>

## Cascades, paradoxes, and learning feedback

- **S28** - Brummitt et al., *Cascading Failures in Interdependent Systems under
  Flow Redistribution*. `KNOWN`: interacting overloads and discontinuous
  transitions are not unique to dispatch.
  <https://journals.aps.org/pre/abstract/10.1103/PhysRevE.97.022307>
- **S29** - Moussawi et al., *Cascading Failures in a Spatially Embedded Network*.
  `KNOWN`: spatial cascade structure and overload propagation are established.
  <https://www.nature.com/articles/ncomms10094>
- **S30** - Hillas, Caldentey, and Gupta, *Heavy Traffic Analysis of Multi-Class
  Bipartite Queueing Systems under FCFS*. `KNOWN`: more compatibility can worsen
  delay, so a dispatch capacity paradox is not novel without a non-reducible
  mechanism.
  <https://link.springer.com/article/10.1007/s11134-024-09903-4>
- **S31** - Cohen and Kelly, *A Paradox of Congestion in a Queueing Network*.
  `KNOWN`: Braess-type degradation is classical in queueing networks.
  <https://www.ee.columbia.edu/~aurel/papers/networking_games/braess_jap99.pdf>
- **S32** - Perdomo et al., *Performative Prediction*. `KNOWN`: predictions and
  deployed decisions changing the data-generating distribution are established.
  <https://proceedings.mlr.press/v119/perdomo20a.html>
- **S33** - Tsiourvas et al., *The Optimizer's Curse in Decision-Focused
  Learning*. `KNOWN`: improved prediction metrics can fail to improve downstream
  decisions through optimization effects.
  <https://proceedings.mlr.press/v235/tsiourvas24a.html>
- **S34** - Acemoglu et al., *Informational Braess' Paradox*. `KNOWN`: more
  information can worsen equilibrium outcomes.
  <https://pubsonline.informs.org/doi/10.1287/opre.2017.1712>

## Audit limitations

`SUPPORTED`: the registry is broad enough to perform an early reduction attack.
`UNKNOWN`: it does not establish an exhaustive frontier in any specialist
literature. In particular, unpublished work, non-English work, and results after
the audit date may change the classification. A novelty claim would require a
separate systematic search and specialist review.
