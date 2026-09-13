# Load and Stress Testing Suite

This directory contains load testing scripts using **Locust** and **k6**.

---

## Performance Targets & Simulation Scenarios (Phase 18)

- **Classroom Burst**: 500 concurrent check-ins submitted within a 3-minute checkpoint window across 15 classes.
- **Campus Peak**: 2,000 concurrent students active on the network.
- **Latency Target**: 95th percentile API response time < 250ms under peak load.
