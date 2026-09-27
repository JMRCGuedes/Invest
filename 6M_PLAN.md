# Technical Development Plan — 6 Months

Each month has a main theme, concepts to study in depth, concrete improvements to apply to current applications, and a soft skills component tied to the technical theme.

## Suggested rhythm

- **Weeks 1–2:** study the theory and experiment in a personal project.
- **Weeks 3–4:** apply one of the improvements at work and document the result (before vs. after, with numbers).

> At the start and end of the plan, ask 2 or 3 trusted colleagues for feedback to measure soft skills progress.

---

## Month 1 — Modern Java and JVM performance

### Deep dive
- Recent Java features (21 and 25 LTS): records, sealed classes, pattern matching and **virtual threads**.
- JVM garbage collectors (G1, ZGC) and how to tune them.
- Profiling with **Java Flight Recorder** and **async-profiler**.
- Quarkus native compilation with GraalVM.

### Improvements to make
- [ ] Profile a slow endpoint and identify where time is actually spent (N+1 queries, serialization, etc.).
- [ ] Review connection pools and timeouts.
- [ ] Test virtual threads in I/O-heavy services and measure the difference.

### Soft skill — Written communication
- [ ] Write a short profiling report: problem, analysis and result with numbers.
- [ ] Write two versions: a technical one for the team and a three-sentence one for management.

---

## Month 2 — Advanced Angular

### Deep dive
- **Signals** and the new reactive model.
- Standalone components and zoneless applications.
- `@defer` for deferred loading and OnPush change detection.
- State management with NgRx SignalStore.
- Testing with Jest/Vitest (unit) and **Playwright** (end-to-end).

### Improvements to make
- [ ] Measure the app with Lighthouse and the Angular DevTools profiler; fix components that re-render too often.
- [ ] Analyze bundle size (`source-map-explorer`) and apply lazy loading where missing.
- [ ] Use virtual scroll in large tables.
- [ ] Gradually migrate complex RxJS code to signals where it makes sense.

### Soft skill — Empathy
- [ ] Watch 2 or 3 users using the application and ask what frustrates them.
- [ ] Use that feedback to prioritize optimizations.

---

## Month 3 — Kafka and distributed systems

### Deep dive
- Internals: partitions, replication, consumer rebalancing.
- Delivery guarantees and **exactly-once** semantics.
- **Kafka Streams** for stateful processing.
- Schema Registry with Avro or Protobuf.
- Patterns: Outbox, Saga, idempotency, CQRS.
- Recommended reading: *Designing Data-Intensive Applications* (Martin Kleppmann).

### Improvements to make
- [ ] Monitor **consumer lag** and set up alerts.
- [ ] Ensure consumers are idempotent, with retries and a dead letter queue.
- [ ] Review partition key choices.

### Soft skill — Problem solving
- [ ] Run a root cause analysis (5 Whys) on a real or simulated incident.
- [ ] Write a blameless post-mortem focused on system and process improvements.

---

## Month 4 — Elasticsearch in depth

### Deep dive
- Mappings and analyzers.
- Relevance tuning: BM25, boosting, function score.
- Aggregations.
- **Vector and hybrid search** (kNN + text search).
- Operations: sharding, ILM (index lifecycle management), zero-downtime reindexing with aliases.

### Improvements to make
- [ ] Analyze the slowest queries with the Profile API.
- [ ] Review dynamic mappings that create unnecessary fields.
- [ ] Implement aliases to reindex without affecting users.

### Soft skill — Teamwork
- [ ] Pair program with a colleague on search tuning.
- [ ] Mentor a more junior colleague on a technical topic.

---

## Month 5 — AI and LLM engineering

### Deep dive
- Advanced RAG: chunking, re-ranking, hybrid search.
- Tool calling and agents.
- **Model Context Protocol (MCP)**.
- **Evaluation (evals)** of LLM-based systems.
- Java frameworks: **LangChain4j** (with Quarkus integration) and **Spring AI**; Python for quick experimentation.

### Improvements to make
- [ ] Build an MCP server that exposes internal data or tools to an assistant.
- [ ] Build an evaluation test set for an existing LLM feature.
- [ ] Use AI in your own workflow: test generation, code review, migrations.

### Soft skill — Creativity
- [ ] Identify 3 everyday problems for the team or users where AI could help.
- [ ] Pick one and present a short proposal with benefits, risks and how to measure success.

---

## Month 6 — Platform: OpenShift, CI/CD and observability

### Deep dive
- Kubernetes/OpenShift: resource requests and limits, probes, HPA, network policies.
- Helm or Kustomize.
- **GitOps with ArgoCD**.
- Observability with **OpenTelemetry**: distributed traces, metrics (Prometheus/Grafana) and structured logs.
- Goal: **Red Hat EX288** certification (OpenShift Application Developer).

### Improvements to make
- [ ] Add distributed tracing from Angular, through the backend, to Kafka.
- [ ] Review pod CPU and memory limits.
- [ ] Optimize Docker images (multi-stage builds, minimal base images).
- [ ] Add vulnerability scanning to the pipeline (Trivy).

### Soft skill — Public speaking
- [ ] Present the 6 months of improvements to the team (or at a meetup), with before and after numbers.
- [ ] Ask colleagues for final feedback and compare it with the initial feedback.

---

## Progress log

| Month | Theme | Improvement applied | Result (before → after) |
|-------|-------|---------------------|-------------------------|
| 1 | Java and JVM | | |
| 2 | Angular | | |
| 3 | Kafka | | |
| 4 | Elasticsearch | | |
| 5 | AI and LLMs | | |
| 6 | OpenShift and observability | | |