import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:university_attendance_mobile/core/offline/monotonic_clock.dart';
import 'package:university_attendance_mobile/core/offline/offline_storage.dart';
import 'package:university_attendance_mobile/core/offline/sqlite_offline_storage.dart';

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
      MobileOfflineStorage? storage1;
      MobileOfflineStorage? storage2;

      try {
        // 1. First storage instance writes data
        storage1 = MobileOfflineStorage.createInstance(storageDir: tempDir);
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
        storage2 = MobileOfflineStorage.createInstance(storageDir: tempDir);

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
        storage1?.dispose();
        storage2?.dispose();
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

  group('SqliteOfflineStorage Hardening & Migration Tests (M18 Part 2)', () {
    test('Initializes schema and tables correctly in memory', () {
      final sqlite = SqliteOfflineStorage();
      try {
        final tables = sqlite.db
            .select("SELECT name FROM sqlite_master WHERE type='table';")
            .map((r) => r['name'] as String)
            .toSet();

        expect(tables.contains('storage_metadata'), isTrue);
        expect(tables.contains('offline_permits'), isTrue);
        expect(tables.contains('offline_host_events'), isTrue);
        expect(tables.contains('offline_student_claims'), isTrue);
        expect(tables.contains('sync_outbox'), isTrue);
        expect(tables.contains('sync_conflicts'), isTrue);
      } finally {
        sqlite.dispose();
      }
    });

    test('Migrates legacy JSON store to SQLite with complete fidelity', () {
      final tempDir =
          Directory.systemTemp.createTempSync('sqlite_migration_test_');

      try {
        final jsonFile = File('${tempDir.path}/offline_store.json');
        final legacyJson = {
          'permits': [
            {
              'permit_id': 'legacy-p1',
              'attendance_session_id': 'sess-1',
              'class_occurrence_id': 'occ-1',
              'temporary_host_public_key': 'pub-key-1',
              'signed_permit_token': 'tok-1',
              'valid_from_utc': '2026-09-17T08:00:00.000Z',
              'valid_until_utc': '2026-09-17T12:00:00.000Z',
            }
          ],
          'host_events': [
            {
              'sequence_number': 1,
              'event_type': 'SESSION_STARTED',
              'prev_event_hash':
                  '0000000000000000000000000000000000000000000000000000000000000000',
              'event_hash': 'abc123hash',
              'payload': {'title': 'Lecture 1'},
              'signature': 'sig1',
              'occurred_at_utc': '2026-09-17T08:01:00.000Z',
            }
          ],
          'student_claims': [
            {
              'claim_id': 'legacy-c1',
              'permit_id': 'legacy-p1',
              'checkpoint_type': 'START',
              'rotation_slot': 1,
              'qr_challenge_token': 'token-m12',
              'client_captured_at_utc': '2026-09-17T08:05:00.000Z',
              'status': 'PENDING_SYNC',
              'user_id': 'stu-m12',
            }
          ],
          'outbox': [
            {
              'outbox_id': 'outbox_legacy-c1',
              'user_id': 'stu-m12',
              'item_type': 'STUDENT_CLAIM',
              'reference_id': 'legacy-c1',
              'payload': {'claim_id': 'legacy-c1'},
              'status': 'PENDING_SYNC',
              'created_at_utc': '2026-09-17T08:05:00.000Z',
              'retry_count': 0,
            }
          ],
        };
        jsonFile.writeAsStringSync(jsonEncode(legacyJson));

        // Create SqliteOfflineStorage on this directory
        final sqlite = SqliteOfflineStorage(storageDir: tempDir);
        try {
          // Verify permit migrated
          final permit = sqlite.getPermit('legacy-p1');
          expect(permit, isNotNull);
          expect(permit!.attendanceSessionId, equals('sess-1'));

          // Verify host event migrated
          final events = sqlite.getHostEvents();
          expect(events.length, equals(1));
          expect(events.first.eventType, equals('SESSION_STARTED'));

          // Verify student claim migrated
          final claims = sqlite.getPendingStudentClaimsForUser('stu-m12');
          expect(claims.length, equals(1));
          expect(claims.first.claimId, equals('legacy-c1'));

          // Verify outbox migrated
          final outbox = sqlite.getPendingOutboxForUser('stu-m12');
          expect(outbox.length, equals(1));
          expect(outbox.first.referenceId, equals('legacy-c1'));

          // Verify metadata marker recorded
          final meta = sqlite.db.select(
            "SELECT value FROM storage_metadata WHERE key = 'json_migration_completed';",
          );
          expect(meta.isNotEmpty, isTrue);
          expect(meta.first['value'], equals('true'));

          // Verify original JSON file archived to .bak
          expect(File('${tempDir.path}/offline_store.json.bak').existsSync(),
              isTrue);
        } finally {
          sqlite.dispose();
        }
      } finally {
        if (tempDir.existsSync()) {
          tempDir.deleteSync(recursive: true);
        }
      }
    });

    test('Migration is idempotent and safely re-opens without duplicates', () {
      final tempDir =
          Directory.systemTemp.createTempSync('sqlite_idempotency_test_');

      try {
        final jsonFile = File('${tempDir.path}/offline_store.json');
        final legacyJson = {
          'permits': [
            {
              'permit_id': 'p-idemp',
              'attendance_session_id': 'sess-idemp',
              'class_occurrence_id': 'occ-idemp',
              'temporary_host_public_key': 'pub-key',
              'signed_permit_token': 'tok',
              'valid_from_utc': '2026-09-17T08:00:00.000Z',
              'valid_until_utc': '2026-09-17T12:00:00.000Z',
            }
          ],
          'host_events': [],
          'student_claims': [],
          'outbox': [],
        };
        jsonFile.writeAsStringSync(jsonEncode(legacyJson));

        // Open first time (migrates)
        final sqlite1 = SqliteOfflineStorage(storageDir: tempDir);
        sqlite1.dispose();

        // Open second time (idempotent, skips already migrated)
        final sqlite2 = SqliteOfflineStorage(storageDir: tempDir);
        try {
          final count = sqlite2.db.select(
            'SELECT COUNT(*) as c FROM offline_permits;',
          );
          expect(count.first['c'], equals(1));
        } finally {
          sqlite2.dispose();
        }
      } finally {
        if (tempDir.existsSync()) {
          tempDir.deleteSync(recursive: true);
        }
      }
    });

    test('Corrupt legacy JSON is preserved as .corrupt_* without crashing', () {
      final tempDir =
          Directory.systemTemp.createTempSync('sqlite_corrupt_test_');

      try {
        final jsonFile = File('${tempDir.path}/offline_store.json');
        jsonFile.writeAsStringSync(
            '{ malformed JSON content: missing closing brace');

        final sqlite = SqliteOfflineStorage(storageDir: tempDir);
        try {
          // Metadata status records corrupt_preserved
          final meta = sqlite.db.select(
            "SELECT value FROM storage_metadata WHERE key = 'json_migration_status';",
          );
          expect(meta.isNotEmpty, isTrue);
          expect(meta.first['value'], equals('corrupt_preserved'));

          // Check that a .corrupt_ file exists
          final corruptFiles = tempDir
              .listSync()
              .where((f) => f.path.contains('.corrupt_'))
              .toList();
          expect(corruptFiles.isNotEmpty, isTrue);
        } finally {
          sqlite.dispose();
        }
      } finally {
        if (tempDir.existsSync()) {
          tempDir.deleteSync(recursive: true);
        }
      }
    });

    test('Explicit sync state lifecycle transitions and conflict recording',
        () {
      final sqlite = SqliteOfflineStorage();
      try {
        final claim = OfflineStudentClaimModel(
          claimId: 'claim-sync-flow-1',
          permitId: 'p-flow',
          checkpointType: 'START',
          rotationSlot: 10,
          qrChallengeToken: 'token-flow',
          clientCapturedAtUtc: DateTime.utc(2026, 9, 17, 9, 0, 0),
          userId: 'stu-flow',
        );

        // 1. Save claim and outbox (PENDING_SYNC)
        sqlite.saveClaimWithOutboxTransactional(
          userId: 'stu-flow',
          claim: claim,
        );
        var outbox = sqlite.getPendingOutboxForUser('stu-flow');
        expect(outbox.length, equals(1));
        expect(outbox.first.status, equals(SyncState.pendingSyncLegacy));
        expect(outbox.first.retryCount, equals(0));

        // 2. Simulate transient failure -> FAILED_RETRYABLE
        sqlite.acknowledgeClaimSync(
          claimId: 'claim-sync-flow-1',
          success: false,
          failureStatus: SyncState.failedRetryable,
          rejectionReason: 'HTTP 503 Gateway Timeout',
        );
        outbox = sqlite.getPendingOutboxForUser('stu-flow');
        expect(outbox.length, equals(1));
        expect(outbox.first.status, equals(SyncState.failedRetryable));
        expect(outbox.first.retryCount, equals(1));

        // 3. Record conflict resolution
        sqlite.recordConflict(
          conflictId: 'conf-1',
          userId: 'stu-flow',
          referenceId: 'claim-sync-flow-1',
          conflictType: 'ALREADY_MARKED_PRESENT',
          serverResponse: {'error': 'DUPLICATE_CHECKPOINT'},
        );
        final conflictRows = sqlite.db.select(
          'SELECT * FROM sync_conflicts WHERE conflict_id = ?;',
          ['conf-1'],
        );
        expect(conflictRows.length, equals(1));
        expect(conflictRows.first['conflict_type'],
            equals('ALREADY_MARKED_PRESENT'));

        // 4. Successful sync acknowledgment -> SYNCED
        sqlite.acknowledgeClaimSync(
          claimId: 'claim-sync-flow-1',
          success: true,
        );
        expect(sqlite.getPendingOutboxForUser('stu-flow').isEmpty, isTrue);

        final claimRow = sqlite.db.select(
          'SELECT status FROM offline_student_claims WHERE claim_id = ?;',
          ['claim-sync-flow-1'],
        );
        expect(claimRow.first['status'], equals(SyncState.synced));
      } finally {
        sqlite.dispose();
      }
    });

    test('Cryptographic keys remain isolated from SQLite database', () {
      final sqlite = SqliteOfflineStorage();
      try {
        final tableColumns = sqlite.db.select(
          "SELECT sql FROM sqlite_master WHERE type='table';",
        );
        for (final row in tableColumns) {
          final sql = (row['sql'] as String).toLowerCase();
          expect(sql.contains('private_key'), isFalse);
          expect(sql.contains('privatekey'), isFalse);
          expect(sql.contains('secret_key'), isFalse);
        }
      } finally {
        sqlite.dispose();
      }
    });
  });
}
