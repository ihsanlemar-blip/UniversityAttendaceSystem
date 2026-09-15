import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:university_attendance_mobile/core/offline/monotonic_clock.dart';
import 'package:university_attendance_mobile/core/offline/offline_storage.dart';

void main() {
  group('MonotonicClockAnchor Tests', () {
    test('Calculates current server time accurately using monotonic offset',
        () {
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

      expect(
          restored.serverTimeUtcAtAnchor, equals(anchor.serverTimeUtcAtAnchor));
      expect(restored.monotonicUptimeMsAtAnchor,
          equals(anchor.monotonicUptimeMsAtAnchor));
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

    test('Atomically creates claim and outbox item (Section 10)', () {
      final claim = OfflineStudentClaimModel(
        claimId: 'claim-atomic-1',
        permitId: 'permit-1',
        checkpointType: 'START',
        rotationSlot: 42,
        qrChallengeToken: 'qr-token-xyz',
        clientCapturedAtUtc: DateTime.utc(2026, 9, 15, 10, 0, 0),
        userId: 'student_123',
      );

      storage.saveClaimWithOutboxTransactional(
        userId: 'student_123',
        claim: claim,
      );

      final claims = storage.getPendingStudentClaimsForUser('student_123');
      final outbox = storage.getPendingOutboxForUser('student_123');

      expect(claims.length, equals(1));
      expect(outbox.length, equals(1));
      expect(outbox.first.referenceId, equals('claim-atomic-1'));
      expect(outbox.first.userId, equals('student_123'));
      expect(outbox.first.status, equals('PENDING_SYNC'));
    });

    test('Survives simulated application restart (Section 12)', () {
      final tempDir =
          Directory.systemTemp.createTempSync('offline_storage_test_');

      try {
        // 1. First storage instance writes data
        final storage1 =
            MobileOfflineStorage.createInstance(storageDir: tempDir);
        final claim = OfflineStudentClaimModel(
          claimId: 'restart-claim-1',
          permitId: 'restart-permit-1',
          checkpointType: 'START',
          rotationSlot: 55,
          qrChallengeToken: 'qr-token-restart',
          clientCapturedAtUtc: DateTime.utc(2026, 9, 15, 12, 0, 0),
          userId: 'student_restart',
        );
        storage1.saveClaimWithOutboxTransactional(
          userId: 'student_restart',
          claim: claim,
        );

        expect(storage1.getPendingStudentClaims().length, equals(1));

        // 2. Simulate app termination and restart: fresh instance loading from disk
        final storage2 =
            MobileOfflineStorage.createInstance(storageDir: tempDir);

        final loadedClaims =
            storage2.getPendingStudentClaimsForUser('student_restart');
        final loadedOutbox =
            storage2.getPendingOutboxForUser('student_restart');

        expect(loadedClaims.length, equals(1));
        expect(loadedClaims.first.claimId, equals('restart-claim-1'));
        expect(loadedClaims.first.status, equals('PENDING_SYNC'));
        expect(loadedOutbox.length, equals(1));
        expect(loadedOutbox.first.referenceId, equals('restart-claim-1'));
      } finally {
        if (tempDir.existsSync()) {
          tempDir.deleteSync(recursive: true);
        }
      }
    });

    test('Enforces strict local account isolation (Section 13)', () {
      final claimA = OfflineStudentClaimModel(
        claimId: 'claim-student-a',
        permitId: 'permit-iso-1',
        checkpointType: 'START',
        rotationSlot: 10,
        qrChallengeToken: 'qr-token-a',
        clientCapturedAtUtc: DateTime.utc(2026, 9, 15, 10, 0, 0),
        userId: 'student_A',
      );

      final claimB = OfflineStudentClaimModel(
        claimId: 'claim-student-b',
        permitId: 'permit-iso-2',
        checkpointType: 'START',
        rotationSlot: 10,
        qrChallengeToken: 'qr-token-b',
        clientCapturedAtUtc: DateTime.utc(2026, 9, 15, 10, 0, 0),
        userId: 'student_B',
      );

      storage.saveClaimWithOutboxTransactional(
          userId: 'student_A', claim: claimA);
      storage.saveClaimWithOutboxTransactional(
          userId: 'student_B', claim: claimB);

      // Student B cannot query or upload Student A's claims
      final studentBClaims =
          storage.getPendingStudentClaimsForUser('student_B');
      final studentBOutbox = storage.getPendingOutboxForUser('student_B');

      expect(studentBClaims.length, equals(1));
      expect(studentBClaims.first.claimId, equals('claim-student-b'));
      expect(studentBOutbox.length, equals(1));
      expect(studentBOutbox.first.referenceId, equals('claim-student-b'));

      // Verify Student A's items remain isolated
      final studentAClaims =
          storage.getPendingStudentClaimsForUser('student_A');
      expect(studentAClaims.length, equals(1));
      expect(studentAClaims.first.claimId, equals('claim-student-a'));
    });

    test('Does not delete outbox item on sync failure (Section 11)', () {
      final claim = OfflineStudentClaimModel(
        claimId: 'claim-retry-1',
        permitId: 'permit-retry',
        checkpointType: 'START',
        rotationSlot: 20,
        qrChallengeToken: 'token-retry',
        clientCapturedAtUtc: DateTime.utc(2026, 9, 15, 10, 0, 0),
        userId: 'student_retry',
      );

      storage.saveClaimWithOutboxTransactional(
          userId: 'student_retry', claim: claim);
      expect(
          storage.getPendingOutboxForUser('student_retry').length, equals(1));

      // 1. Sync failure (network timeout / 500 error): item MUST remain pending and increment retryCount
      storage.acknowledgeClaimSync(claimId: 'claim-retry-1', success: false);
      final outboxAfterFail = storage.getPendingOutboxForUser('student_retry');
      expect(outboxAfterFail.length, equals(1));
      expect(outboxAfterFail.first.retryCount, equals(1));
      expect(outboxAfterFail.first.status, equals('PENDING_SYNC'));

      // 2. Deterministic server ACK: item removed from pending outbox
      storage.acknowledgeClaimSync(claimId: 'claim-retry-1', success: true);
      expect(storage.getPendingOutboxForUser('student_retry').isEmpty, isTrue);
      expect(storage.getPendingStudentClaimsForUser('student_retry').isEmpty,
          isTrue);
    });

    test('Secure key storage lifecycle (Section 14 & 15)', () async {
      final secureStorage = storage.secureKeyStorage;
      const permitId = 'permit-secure-key-1';
      const mockPrivKey =
          'MC4CAQAwBQYDK2VwBCIEINmqhHd4Uz7002Yt007zEIPHYaMaPH6civdsgT9jiyMY';

      // 1. Store private key securely
      await secureStorage.writePrivateKey(
        permitId: permitId,
        privateKeyPem: mockPrivKey,
      );

      // 2. Retrieve key
      final retrieved = await secureStorage.readPrivateKey(permitId: permitId);
      expect(retrieved, equals(mockPrivKey));

      // 3. Delete key upon session completion
      await secureStorage.deletePrivateKey(permitId: permitId);
      final afterDelete =
          await secureStorage.readPrivateKey(permitId: permitId);
      expect(afterDelete, isNull);
    });
  });
}
