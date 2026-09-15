/// Monotonic clock tracking device uptime to defend against device wall-clock tampering (INV-03).
class MonotonicClockAnchor {
  final DateTime serverTimeUtcAtAnchor;
  final int monotonicUptimeMsAtAnchor;

  MonotonicClockAnchor({
    required this.serverTimeUtcAtAnchor,
    required this.monotonicUptimeMsAtAnchor,
  });

  /// Estimates the current server UTC time based on elapsed monotonic device uptime.
  DateTime estimateCurrentServerTime(int currentUptimeMs) {
    if (currentUptimeMs < monotonicUptimeMsAtAnchor) {
      throw StateError(
        'Monotonic clock rollback detected: current uptime ($currentUptimeMs) '
        '< anchor uptime ($monotonicUptimeMsAtAnchor). Device may have restarted.',
      );
    }
    final elapsedMs = currentUptimeMs - monotonicUptimeMsAtAnchor;
    return serverTimeUtcAtAnchor.add(Duration(milliseconds: elapsedMs));
  }

  Map<String, dynamic> toJson() => {
        'server_time_utc_at_anchor': serverTimeUtcAtAnchor.toIso8601String(),
        'monotonic_uptime_ms_at_anchor': monotonicUptimeMsAtAnchor,
      };

  factory MonotonicClockAnchor.fromJson(Map<String, dynamic> json) =>
      MonotonicClockAnchor(
        serverTimeUtcAtAnchor:
            DateTime.parse(json['server_time_utc_at_anchor'] as String),
        monotonicUptimeMsAtAnchor:
            json['monotonic_uptime_ms_at_anchor'] as int,
      );
}
