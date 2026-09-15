import 'package:flutter_test/flutter_test.dart';
import 'package:university_attendance_mobile/core/offline/monotonic_clock.dart';
import 'package:university_attendance_mobile/core/offline/offline_storage.dart';

void main() {
  group('MonotonicClockAnchor Tests', () {
    test('Calculates current server time accurately using monotonic offset', () {
      final anchorTime = DateTime.utc(2026, 9, 15, 10, 0, 0);
      final anchor = MonotonicClockAnchor(
        serverTimeUtcAtAnchor: anchorTime,
        monotonicUptimeMsAtAnchor: 50000,
      );

      final estimated = anchor.estimateCurrentServerTime(70000); // +20s
      expect(estimated, equals(DateTime.utc(2026, 9, 15, 10, 0, 20)));
    });

    test('Throws StateError on monotonic clock rollback (reboot)', () {
      final anchorTime = DateTime.utc(2026, 9, 15, 10, 0, 0);
      final anchor = MonotonicClockAnchor(
        serverTimeUtcAtAnchor: anchorTime,
        monotonicUptimeMsAtAnchor: 50000,
      );

      expect(
        () => anchor.estimateCurrentServerTime(30000), // decreased!
        throwsA(isA<StateError>()),
      );
    });

    test('Serializes to and from JSON', () {
      final anchor = MonotonicClockAnchor(
        serverTimeUtcAtAnchor: DateTime.utc(2026, 9, 15, 10, 0, 0),
        monotonicUptimeMsAtAnchor: 12345,
      );

      final jsonMap = anchor.toJson();
      final restored = MonotonicClockAnchor.fromJson(jsonMap);

      expect(restored.serverTimeUtcAtAnchor, equals(anchor.serverTimeUtcAtAnchor));
      expect(restored.monotonicUptimeMsAtAnchor, equals(anchor.monotonicUptimeMsAtAnchor));
    });
  });

  group('MobileOfflineStorage Outbox Tests', () {
    final storage = MobileOfflineStorage();

    setUp(() {
      storage.reset();
    });

    test('Caches and retrieves offline permits', () {
      final permit = OfflinePermitModel(
        permitId: 'p-123',
        attendanceSessionId: 's-456',
        classOccurrenceId: 'o-789',
        temporaryHostPublicKey: 'pub_mock',
        signedPermitToken: 'tok_mock',
        validFromUtc: DateTime.utc(2026, 9, 15, 8, 0, 0),
        validUntilUtc: DateTime.utc(2026, 9, 15, 20, 0, 0),
      );

      storage.cachePermit(permit);
      final retrieved = storage.getPermit('p-123');

      expect(retrieved, isNotNull);
      expect(retrieved?.attendanceSessionId, equals('s-456'));
    });

    test('Records and dedupes student claims in outbox', () {
      final claim1 = OfflineStudentClaimModel(
        claimId: 'c-1',
        permitId: 'p-100',
        checkpointType: 'START',
        rotationSlot: 10,
        qrChallengeToken: 'token-1',
        clientCapturedAtUtc: DateTime.utc(2026, 9, 15, 10, 0, 5),
      );

      storage.addStudentClaim(claim1);
      expect(storage.getPendingStudentClaims().length, equals(1));

      // Same permit & checkpoint replaces / dedupes
      final claim2 = OfflineStudentClaimModel(
        claimId: 'c-2',
        permitId: 'p-100',
        checkpointType: 'START',
        rotationSlot: 11,
        qrChallengeToken: 'token-2',
        clientCapturedAtUtc: DateTime.utc(2026, 9, 15, 10, 0, 25),
      );

      storage.addStudentClaim(claim2);
      expect(storage.getPendingStudentClaims().length, equals(1));
      expect(storage.getPendingStudentClaims().first.claimId, equals('c-2'));

      // Mark claim synced
      storage.markClaimSynced('c-2');
      expect(storage.getPendingStudentClaims().isEmpty, isTrue);
    });
  });
}
