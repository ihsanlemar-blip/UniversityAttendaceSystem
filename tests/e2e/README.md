# End-to-End (E2E) Test Suite

This directory contains cross-system integration and user journey tests using Playwright.

---

## Planned User Journey Tests (Milestone 4+)

1. **Lecturer Session Flow**:
   - Lecturer logs into web portal.
   - Starts attendance session for scheduled class occurrence.
   - Activates Start checkpoint and displays rotating QR code.
   - Closes session and reviews finalized attendee list.
2. **Student Check-in Flow**:
   - Student authenticates on device.
   - Scans active dynamic QR code.
   - Verifies check-in recorded successfully on backend.
3. **Dean / Admin Audit Flow**:
   - Administrator reviews attendance statistics.
   - Inspects immutable audit ledger.
