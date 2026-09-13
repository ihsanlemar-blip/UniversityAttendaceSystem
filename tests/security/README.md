# Security and Anti-Cheating Verification Suite

This directory contains automated security regression scripts and penetration test suites.

---

## Anti-Cheating Test Matrix (Phase 17)

1. **Replay Attack Simulation**: Re-submitting an already used dynamic QR token.
2. **Clock Skew Test**: Submitting a token outside the valid rotation window (±1 step).
3. **Unregistered Device Check**: Submitting a check-in payload signed by an unregistered public key.
4. **Duplicate Credit Prevention**: Submitting two check-ins for the same student in one checkpoint window.
5. **Rate Limiting Verification**: Flooding the login or check-in endpoints to verify automatic 429 Too Many Requests response.
