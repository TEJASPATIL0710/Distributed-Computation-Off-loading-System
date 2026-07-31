# Major Project Plan: Distributed Computation Offloading System

## 1. What you're actually building

A **remote task offloading platform**: one or more "thin" client machines send compute-heavy jobs (arbitrary scripts, ML inference, rendering, or numeric simulation) to a server (or server cluster). The server queues, load-balances, executes, and streams results back. This sits in the domain of **distributed systems / edge-cloud offloading**, which is a well-respected and well-documented research area, so you'll have plenty of literature to cite.

Working title: **"Adaptive Multi-Client Computation Offloading Framework with Heterogeneous Task Support"** — sounds good on a report cover and accurately describes the scope.

## 2. Recommended tech stack (with reasoning)

Since you're supporting 4 very different task types + load balancing, you need a stack that separates **API/orchestration** from **execution**.

| Layer | Recommendation | Why |
|---|---|---|
| Client-server API | **FastAPI (Python)** | Async, fast to build, auto-generates docs (great for your report/demo), easy WebSocket support |
| Real-time result push | **WebSockets** | Client submits a job, doesn't need to poll — server pushes result when ready |
| Task queue / load balancing | **Celery + Redis** (or RabbitMQ) | This is the actual "load balancer" — distributes tasks across worker processes/machines, handles retries, priority queues |
| Task execution sandbox | **Docker containers** | Critical for the general-purpose "run any code" feature — you cannot safely `exec()` arbitrary client code on your host. Each task type gets its own container image (a Python/generic runner, a PyTorch/ONNX inference image, an FFmpeg/Blender rendering image, a NumPy/SciPy image) |
| ML inference | **PyTorch/ONNX Runtime** inside its own worker container | Keeps heavy ML deps isolated from the rest of the system |
| Rendering/video | **FFmpeg** for video, optionally **Blender CLI** for 3D render | Both scriptable headlessly |
| Numeric computation | **NumPy/SciPy** in a dedicated worker | Lightweight, fast |
| Data serialization | **Protocol Buffers or MessagePack** | Faster/smaller than JSON for large payloads (matrices, model weights, video chunks) |
| Monitoring | **Flower** (Celery monitoring) or a simple custom dashboard | Shows task distribution — great demo material |

**Why this combo:** Celery+Redis literally *is* a load balancer (round-robin/priority task distribution across workers) — you don't need to hand-roll load-balancing logic from scratch, which lets you spend your engineering time on the interesting parts (security, task-type abstraction, adaptive scheduling) instead of reinventing a scheduler.

If your course requires you to implement load balancing "yourself" (some evaluators want to see the algorithm, not a library doing it for you), plan a custom **weighted least-connections** or **round-robin with health checks** algorithm as a Sem 2 stretch goal that plugs in alongside/instead of Celery's default.

## 3. Prerequisite concepts you need to learn before/while building

Group these into what to study each month — don't try to learn everything before starting.

**Networking & communication**
- Sockets (TCP/UDP) fundamentals — even though you'll use FastAPI/WebSockets, understand what's underneath
- REST APIs vs WebSockets vs gRPC — trade-offs
- Serialization formats (JSON, Protobuf, MessagePack)

**Distributed systems concepts**
- Task queues & message brokers (Celery, RabbitMQ, Redis pub/sub)
- Load balancing algorithms: round robin, least connections, weighted, consistent hashing
- CAP theorem basics (just enough to discuss in your report)
- Fault tolerance: retries, timeouts, dead-letter queues, heartbeat/health checks

**Security (this is the part most students under-plan)**
- Sandboxing untrusted code execution (Docker resource limits: CPU/memory caps, network isolation, read-only filesystems)
- Authentication between client and server (API keys or JWT)
- Input validation (a malicious/buggy script shouldn't be able to crash your server)

**Domain-specific**
- Basics of running ML inference from a saved model (ONNX export, TorchScript)
- FFmpeg command-line usage for video tasks
- NumPy vectorized computation basics

**DevOps-adjacent (useful, not mandatory)**
- Docker & docker-compose
- Basic CI concept (even a simple test suite run script counts)

## 4. System Architecture (high level)

```
[Client 1] ─┐
[Client 2] ─┼──► [API Gateway / FastAPI] ──► [Task Queue (Redis/RabbitMQ)]
[Client N] ─┘            │                            │
                     [Auth Layer]              [Load Balancer / Celery]
                                                        │
                                    ┌───────────────────┼───────────────────┐
                              [Worker: General]   [Worker: ML]   [Worker: Render]   [Worker: Numeric]
                              (Docker sandbox)  (Docker sandbox)(Docker sandbox)  (Docker sandbox)
                                                        │
                                              [Result Store (Redis/DB)]
                                                        │
                                          [WebSocket push back to Client]
```

Key design decisions to document in your SRS: how a task is classified into one of the 4 types, how results are stored temporarily, how you handle a worker crashing mid-task, how you cap resource usage per task.

## 5. Semester-wise Breakdown

### Semester 1 — Foundation, Design, and Core Prototype

**Month 1: Research & Requirements**
- Literature survey: read 8–10 papers on computation offloading, edge computing, task scheduling. Look up terms like "mobile cloud offloading," "fog computing," "MEC (multi-access edge computing)" for related work section
- Finalize scope document / SRS (Software Requirements Specification)
- Define success metrics (latency, throughput, task success rate under load)

**Month 2: Architecture & Design**
- Finalize tech stack, draw architecture diagrams, sequence diagrams (task submission → execution → result)
- Design the task schema (how a task is described: type, payload, resource requirements, priority)
- Design the API contract (endpoints, WebSocket message formats)

**Month 3–4: Core Prototype (single task type, single client → single server)**
- Build basic FastAPI server + client CLI/app
- Implement one task type end-to-end (recommend starting with "general-purpose script execution" since it's conceptually simplest) inside a Docker sandbox
- Get task submission → execution → result return working reliably

**Month 5: Extend to Second Task Type + Basic Queue**
- Add Celery+Redis task queue
- Add ML inference task type
- Basic single-worker execution (no load balancing yet)

**Month 6: Sem 1 wrap-up**
- Add basic client authentication
- Write Sem 1 report, prepare demo (1 client, 2 task types, queue-based execution)
- Sem 1 review/viva prep

**Sem 1 deliverables:** SRS document, architecture design document, working prototype (2 task types, single client, queued execution), Sem 1 report

### Semester 2 — Scale, Load Balancing, Remaining Task Types, Polish

**Month 7: Remaining Task Types**
- Add rendering/video task type (FFmpeg-based)
- Add scientific/numeric computation task type
- All 4 task types now working individually

**Month 8: Multi-Client + Load Balancing**
- Support multiple simultaneous clients
- Implement/configure load balancing across multiple worker instances (this is your core "distributed" contribution — worth the most marks/discussion)
- Add health checks and failover (what happens if a worker dies mid-task)

**Month 9: Security Hardening & Resource Management**
- Docker resource limits (CPU/memory/time caps per task) — prevents one bad task from starving others
- Input sanitization, authentication, rate limiting per client

**Month 10: Testing & Performance Evaluation**
- Load testing (simulate many clients/tasks simultaneously — tools like Locust)
- Collect metrics: latency vs. number of concurrent clients, load-balancer efficiency, failure recovery time
- This is your "results and analysis" chapter — graphs of these metrics make your final report strong

**Month 11: Optional Stretch Features (pick 1–2 based on time)**
- Adaptive scheduling (route tasks based on real-time worker load, not just round robin)
- Web dashboard for monitoring task status
- Multi-server support (not just multi-worker on one server)
- Client-side decision logic (client itself decides whether to offload based on its own current load — closer to real edge-offloading research)

**Month 12: Final Documentation & Demo**
- Final report, full architecture docs, user manual
- Polish demo script (show all 4 task types, multiple clients, a simulated worker failure recovering gracefully — this "failure recovery" demo moment tends to impress evaluators)
- Final viva prep

**Sem 2 deliverables:** Full working system (4 task types, multi-client, load-balanced, secured), performance evaluation report, final documentation, demo

## 6. Typical Academic Deliverables to Prepare Alongside Building

- SRS (Software Requirements Specification)
- High-Level & Low-Level Design documents
- ER diagrams / schema (for task metadata, result storage, client auth)
- Sequence & architecture diagrams
- Test plan and test case documentation
- Sem 1 report + Sem 2 final report
- Research paper (many BE programs expect/encourage a conference-style paper from your final results — plan for this from Month 9 onward since it needs your performance data)

## 7. Risk Areas to Watch (common mid-project bottlenecks)

- **Security of arbitrary code execution** — don't leave this to the last month; Docker sandboxing needs to be baked in from the general-purpose task type onward, not bolted on later
- **Scope creep** — 4 task types + load balancing + multi-client is already a full plate; treat anything beyond that (Month 11 stretch goals) as optional, not core
- **Underestimating the "distributed" part** — many student projects end up as "one client, one server, one task" with no real load balancing; make sure Month 8 actually gets tested with concurrent load, not just claimed in the report
- **Leaving performance evaluation to the last week** — Month 10's metrics are the backbone of your results chapter; start collecting data as soon as multi-client + load balancing works, not right before submission

## 8. Suggested first concrete step

Before writing any code: draw the architecture diagram above in more detail, and write a one-page task schema (what fields does a "task" have — type, payload, priority, resource limits, client ID). Everything else builds on getting that data model right.
