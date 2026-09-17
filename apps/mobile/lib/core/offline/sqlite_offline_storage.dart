import 'dart:convert';
import 'dart:io';
import 'package:sqlite3/sqlite3.dart';

import 'offline_storage.dart';

/// Explicit synchronization lifecycle states for offline claims and outbox items (M18 Section 13).
class SyncState {
  static const String pending = 'PENDING';
  static const String syncing = 'SYNCING';
  static const String synced = 'SYNCED';
  static const String conflict = 'CONFLICT';
  static const String failedRetryable = 'FAILED_RETRYABLE';
  static const String failedFinal = 'FAILED_FINAL';

  /// Legacy alias compatibility for M12 tests
  static const String pendingSyncLegacy = 'PENDING_SYNC';
}

/// Transactional SQLite offline storage implementing durable tables, account
/// isolation, transactional outbox, and zero-data-loss JSON migration (M18 Section 4-15).
///
/// NOTE on SQLite Encryption (M18 Section 7):
/// At-rest database protection is provided by native OS application sandboxing
/// (iOS Data Protection and Android App Sandbox). The SQLite database file itself
/// is unencrypted standard SQLite. All cryptographic keys (device private key and
/// host private keys) are classified as SECRET and stored exclusively in OS-protected
/// secure storage (KeyStore/KeyChain via SecureKeyStorage). No secrets are stored in SQLite.
class SqliteOfflineStorage {
  final Directory? storageDir;
  late final Database db;
  final SecureKeyStorage secureKeyStorage;

  SqliteOfflineStorage({
    this.storageDir,
    SecureKeyStorage? keyStorage,
  }) : secureKeyStorage = keyStorage ?? MemorySecureKeyStorage() {
    if (storageDir != null) {
      if (!storageDir!.existsSync()) {
        storageDir!.createSync(recursive: true);
      }
      final dbPath = '${storageDir!.path}/offline_attendance.db';
      db = sqlite3.open(dbPath);
    } else {
      db = sqlite3.openInMemory();
    }
    _initSchema();
    _migrateFromJsonIfPresent();
  }

  void _initSchema() {
    db.execute('PRAGMA foreign_keys = ON;');
    db.execute('''
      CREATE TABLE IF NOT EXISTS storage_metadata (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL
      );

      CREATE TABLE IF NOT EXISTS offline_permits (
        permit_id TEXT PRIMARY KEY,
        attendance_session_id TEXT NOT NULL,
        class_occurrence_id TEXT NOT NULL,
        temporary_host_public_key TEXT NOT NULL,
        signed_permit_token TEXT NOT NULL,
        valid_from_utc TEXT NOT NULL,
        valid_until_utc TEXT NOT NULL,
        created_at_utc TEXT NOT NULL
      );

      CREATE TABLE IF NOT EXISTS offline_host_events (
        sequence_number INTEGER PRIMARY KEY,
        event_type TEXT NOT NULL,
        prev_event_hash TEXT NOT NULL,
        event_hash TEXT NOT NULL,
        payload_json TEXT NOT NULL,
        signature TEXT NOT NULL,
        occurred_at_utc TEXT NOT NULL
      );

      CREATE TABLE IF NOT EXISTS offline_student_claims (
        claim_id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL,
        permit_id TEXT NOT NULL,
        host_session_id TEXT,
        checkpoint_type TEXT NOT NULL,
        rotation_slot INTEGER NOT NULL,
        qr_challenge_token TEXT NOT NULL,
        ble_evidence_json TEXT,
        client_captured_at_utc TEXT NOT NULL,
        status TEXT NOT NULL,
        trusted_device_id TEXT,
        device_proof_signature TEXT,
        created_at_utc TEXT NOT NULL
      );

      CREATE TABLE IF NOT EXISTS sync_outbox (
        outbox_id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL,
        item_type TEXT NOT NULL,
        reference_id TEXT NOT NULL,
        payload_json TEXT NOT NULL,
        status TEXT NOT NULL,
        created_at_utc TEXT NOT NULL,
        retry_count INTEGER NOT NULL DEFAULT 0,
        last_attempted_at_utc TEXT,
        error_message TEXT
      );

      CREATE TABLE IF NOT EXISTS sync_conflicts (
        conflict_id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL,
        reference_id TEXT NOT NULL,
        conflict_type TEXT NOT NULL,
        server_response_json TEXT,
        detected_at_utc TEXT NOT NULL
      );

      CREATE INDEX IF NOT EXISTS idx_student_claims_user_status 
        ON offline_student_claims(user_id, status);

      CREATE INDEX IF NOT EXISTS idx_outbox_user_status 
        ON sync_outbox(user_id, status);

      CREATE INDEX IF NOT EXISTS idx_student_claims_permit_checkpoint 
        ON offline_student_claims(permit_id, checkpoint_type);
    ''');
  }

  /// Safe, restart-durable migration from legacy M12 JSON store (M18 Section 8-10).
  void _migrateFromJsonIfPresent() {
    if (storageDir == null) return;
    final jsonFile = File('${storageDir!.path}/offline_store.json');
    if (!jsonFile.existsSync()) return;

    // Check if migration already marked completed
    final metaCheck = db.select(
      "SELECT value FROM storage_metadata WHERE key = 'json_migration_completed';",
    );
    if (metaCheck.isNotEmpty && metaCheck.first['value'] == 'true') {
      return;
    }

    String raw;
    try {
      raw = jsonFile.readAsStringSync();
    } catch (_) {
      return;
    }

    if (raw.trim().isEmpty) {
      jsonFile.renameSync('${jsonFile.path}.empty.bak');
      return;
    }

    Map<String, dynamic> data;
    try {
      data = jsonDecode(raw) as Map<String, dynamic>;
    } catch (e) {
      // Malformed/corrupt JSON: do NOT discard (M18 Section 10).
      final corruptTarget =
          '${jsonFile.path}.corrupt_${DateTime.now().millisecondsSinceEpoch}';
      try {
        jsonFile.renameSync(corruptTarget);
      } catch (_) {}
      db.execute(
        "INSERT OR REPLACE INTO storage_metadata (key, value) VALUES ('json_migration_status', 'corrupt_preserved');",
      );
      return;
    }

    // Begin atomic SQLite migration transaction
    db.execute('BEGIN TRANSACTION;');
    try {
      final permits = data['permits'] as List<dynamic>? ?? [];
      for (final item in permits) {
        final p = OfflinePermitModel.fromJson(item as Map<String, dynamic>);
        db.execute(
          '''
          INSERT OR REPLACE INTO offline_permits 
          (permit_id, attendance_session_id, class_occurrence_id, temporary_host_public_key, signed_permit_token, valid_from_utc, valid_until_utc, created_at_utc)
          VALUES (?, ?, ?, ?, ?, ?, ?, ?);
          ''',
          [
            p.permitId,
            p.attendanceSessionId,
            p.classOccurrenceId,
            p.temporaryHostPublicKey,
            p.signedPermitToken,
            p.validFromUtc.toIso8601String(),
            p.validUntilUtc.toIso8601String(),
            DateTime.now().toUtc().toIso8601String(),
          ],
        );
      }

      final hostEvents = data['host_events'] as List<dynamic>? ?? [];
      for (final item in hostEvents) {
        final e = OfflineHostEventModel.fromJson(item as Map<String, dynamic>);
        db.execute(
          '''
          INSERT OR REPLACE INTO offline_host_events 
          (sequence_number, event_type, prev_event_hash, event_hash, payload_json, signature, occurred_at_utc)
          VALUES (?, ?, ?, ?, ?, ?, ?);
          ''',
          [
            e.sequenceNumber,
            e.eventType,
            e.prevEventHash,
            e.eventHash,
            jsonEncode(e.payload),
            e.signature,
            e.occurredAtUtc,
          ],
        );
      }

      final studentClaims = data['student_claims'] as List<dynamic>? ?? [];
      for (final item in studentClaims) {
        final c =
            OfflineStudentClaimModel.fromJson(item as Map<String, dynamic>);
        db.execute(
          '''
          INSERT OR REPLACE INTO offline_student_claims
          (claim_id, user_id, permit_id, host_session_id, checkpoint_type, rotation_slot, qr_challenge_token, ble_evidence_json, client_captured_at_utc, status, trusted_device_id, device_proof_signature, created_at_utc)
          VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
          ''',
          [
            c.claimId,
            c.userId,
            c.permitId,
            c.hostSessionId,
            c.checkpointType,
            c.rotationSlot,
            c.qrChallengeToken,
            c.bleEvidence != null ? jsonEncode(c.bleEvidence) : null,
            c.clientCapturedAtUtc.toIso8601String(),
            c.status,
            c.trustedDeviceId,
            c.deviceProofSignature,
            DateTime.now().toUtc().toIso8601String(),
          ],
        );
      }

      final outbox = data['outbox'] as List<dynamic>? ?? [];
      for (final item in outbox) {
        final o = OutboxItemModel.fromJson(item as Map<String, dynamic>);
        db.execute(
          '''
          INSERT OR REPLACE INTO sync_outbox
          (outbox_id, user_id, item_type, reference_id, payload_json, status, created_at_utc, retry_count)
          VALUES (?, ?, ?, ?, ?, ?, ?, ?);
          ''',
          [
            o.outboxId,
            o.userId,
            o.itemType,
            o.referenceId,
            jsonEncode(o.payload),
            o.status,
            o.createdAtUtc.toIso8601String(),
            o.retryCount,
          ],
        );
      }

      db.execute(
        "INSERT OR REPLACE INTO storage_metadata (key, value) VALUES ('json_migration_completed', 'true');",
      );
      db.execute('COMMIT;');

      // Safely archive old JSON file now that commit succeeded
      try {
        jsonFile.renameSync('${jsonFile.path}.bak');
      } catch (_) {}
    } catch (e) {
      db.execute('ROLLBACK;');
      // Keep JSON file intact for retry on next restart
    }
  }

  // ===========================================================================
  // Permit Operations
  // ===========================================================================

  void cachePermit(OfflinePermitModel permit) {
    db.execute(
      '''
      INSERT OR REPLACE INTO offline_permits 
      (permit_id, attendance_session_id, class_occurrence_id, temporary_host_public_key, signed_permit_token, valid_from_utc, valid_until_utc, created_at_utc)
      VALUES (?, ?, ?, ?, ?, ?, ?, ?);
      ''',
      [
        permit.permitId,
        permit.attendanceSessionId,
        permit.classOccurrenceId,
        permit.temporaryHostPublicKey,
        permit.signedPermitToken,
        permit.validFromUtc.toIso8601String(),
        permit.validUntilUtc.toIso8601String(),
        DateTime.now().toUtc().toIso8601String(),
      ],
    );
  }

  OfflinePermitModel? getPermit(String permitId) {
    final rows = db.select(
      'SELECT * FROM offline_permits WHERE permit_id = ?;',
      [permitId],
    );
    if (rows.isEmpty) return null;
    final r = rows.first;
    return OfflinePermitModel(
      permitId: r['permit_id'] as String,
      attendanceSessionId: r['attendance_session_id'] as String,
      classOccurrenceId: r['class_occurrence_id'] as String,
      temporaryHostPublicKey: r['temporary_host_public_key'] as String,
      signedPermitToken: r['signed_permit_token'] as String,
      validFromUtc: DateTime.parse(r['valid_from_utc'] as String),
      validUntilUtc: DateTime.parse(r['valid_until_utc'] as String),
    );
  }

  // ===========================================================================
  // Host Event Operations
  // ===========================================================================

  void addHostEvent(OfflineHostEventModel event) {
    db.execute(
      '''
      INSERT OR REPLACE INTO offline_host_events 
      (sequence_number, event_type, prev_event_hash, event_hash, payload_json, signature, occurred_at_utc)
      VALUES (?, ?, ?, ?, ?, ?, ?);
      ''',
      [
        event.sequenceNumber,
        event.eventType,
        event.prevEventHash,
        event.eventHash,
        jsonEncode(event.payload),
        event.signature,
        event.occurredAtUtc,
      ],
    );
  }

  List<OfflineHostEventModel> getHostEvents() {
    final rows = db.select(
      'SELECT * FROM offline_host_events ORDER BY sequence_number ASC;',
    );
    return rows.map((r) {
      return OfflineHostEventModel(
        sequenceNumber: r['sequence_number'] as int,
        eventType: r['event_type'] as String,
        prevEventHash: r['prev_event_hash'] as String,
        eventHash: r['event_hash'] as String,
        payload:
            jsonDecode(r['payload_json'] as String) as Map<String, dynamic>,
        signature: r['signature'] as String,
        occurredAtUtc: r['occurred_at_utc'] as String,
      );
    }).toList();
  }

  void clearHostEvents() {
    db.execute('DELETE FROM offline_host_events;');
  }

  // ===========================================================================
  // Transactional Outbox & Student Claims (M18 Section 11 & 12)
  // ===========================================================================

  /// Atomically persists Student claim and enqueues Outbox entry in a single SQLite transaction.
  void saveClaimWithOutboxTransactional({
    required String userId,
    required OfflineStudentClaimModel claim,
  }) {
    db.execute('BEGIN TRANSACTION;');
    try {
      // 1. Remove duplicate claims for same permit and checkpoint (INV-05 idempotency)
      db.execute(
        '''
        DELETE FROM offline_student_claims 
        WHERE permit_id = ? AND checkpoint_type = ? AND user_id = ?;
        ''',
        [claim.permitId, claim.checkpointType, userId],
      );

      // 2. Insert student claim
      db.execute(
        '''
        INSERT INTO offline_student_claims
        (claim_id, user_id, permit_id, host_session_id, checkpoint_type, rotation_slot, qr_challenge_token, ble_evidence_json, client_captured_at_utc, status, trusted_device_id, device_proof_signature, created_at_utc)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        ''',
        [
          claim.claimId,
          userId,
          claim.permitId,
          claim.hostSessionId,
          claim.checkpointType,
          claim.rotationSlot,
          claim.qrChallengeToken,
          claim.bleEvidence != null ? jsonEncode(claim.bleEvidence) : null,
          claim.clientCapturedAtUtc.toIso8601String(),
          claim.status,
          claim.trustedDeviceId,
          claim.deviceProofSignature,
          DateTime.now().toUtc().toIso8601String(),
        ],
      );

      // 3. Remove existing outbox item for this reference ID if present
      db.execute(
        'DELETE FROM sync_outbox WHERE reference_id = ?;',
        [claim.claimId],
      );

      // 4. Insert outbox item
      final outboxId = 'outbox_${claim.claimId}';
      db.execute(
        '''
        INSERT INTO sync_outbox
        (outbox_id, user_id, item_type, reference_id, payload_json, status, created_at_utc, retry_count)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?);
        ''',
        [
          outboxId,
          userId,
          'STUDENT_CLAIM',
          claim.claimId,
          jsonEncode(claim.toJson()),
          claim.status,
          claim.clientCapturedAtUtc.toIso8601String(),
          0,
        ],
      );

      db.execute('COMMIT;');
    } catch (e) {
      db.execute('ROLLBACK;');
      rethrow;
    }
  }

  void addStudentClaim(OfflineStudentClaimModel claim) {
    saveClaimWithOutboxTransactional(userId: claim.userId, claim: claim);
  }

  /// Get pending claims (all accounts, legacy support).
  List<OfflineStudentClaimModel> getPendingStudentClaims() {
    final rows = db.select(
      "SELECT * FROM offline_student_claims WHERE status IN ('PENDING', 'PENDING_SYNC') ORDER BY client_captured_at_utc ASC;",
    );
    return rows.map(_mapClaimRow).toList();
  }

  /// Account-isolated query: only returns pending claims for the specified user (M18 Section 5).
  List<OfflineStudentClaimModel> getPendingStudentClaimsForUser(String userId) {
    final rows = db.select(
      "SELECT * FROM offline_student_claims WHERE user_id = ? AND status IN ('PENDING', 'PENDING_SYNC') ORDER BY client_captured_at_utc ASC;",
      [userId],
    );
    return rows.map(_mapClaimRow).toList();
  }

  /// Account-isolated query: returns pending outbox items for the specified user (M18 Section 5).
  List<OutboxItemModel> getPendingOutboxForUser(String userId) {
    final rows = db.select(
      "SELECT * FROM sync_outbox WHERE user_id = ? AND status IN ('PENDING', 'PENDING_SYNC', 'FAILED_RETRYABLE') ORDER BY created_at_utc ASC;",
      [userId],
    );
    return rows.map((r) {
      return OutboxItemModel(
        outboxId: r['outbox_id'] as String,
        userId: r['user_id'] as String,
        itemType: r['item_type'] as String,
        referenceId: r['reference_id'] as String,
        payload:
            jsonDecode(r['payload_json'] as String) as Map<String, dynamic>,
        status: r['status'] as String,
        createdAtUtc: DateTime.parse(r['created_at_utc'] as String),
        retryCount: r['retry_count'] as int,
      );
    }).toList();
  }

  /// Transactionally acknowledges synchronization result (M18 Section 13 & 15).
  void acknowledgeClaimSync({
    required String claimId,
    required bool success,
    String? rejectionReason,
    String failureStatus = 'PENDING_SYNC',
  }) {
    db.execute('BEGIN TRANSACTION;');
    try {
      if (success) {
        db.execute(
          "UPDATE offline_student_claims SET status = 'SYNCED' WHERE claim_id = ?;",
          [claimId],
        );
        db.execute(
          'DELETE FROM sync_outbox WHERE reference_id = ?;',
          [claimId],
        );
      } else {
        // Increment retry count and update status
        db.execute(
          '''
          UPDATE sync_outbox 
          SET status = ?,
              retry_count = retry_count + 1,
              last_attempted_at_utc = ?,
              error_message = ?
          WHERE reference_id = ?;
          ''',
          [
            failureStatus,
            DateTime.now().toUtc().toIso8601String(),
            rejectionReason,
            claimId,
          ],
        );
      }
      db.execute('COMMIT;');
    } catch (e) {
      db.execute('ROLLBACK;');
      rethrow;
    }
  }

  void markClaimSynced(String claimId) {
    acknowledgeClaimSync(claimId: claimId, success: true);
  }

  /// Record server reconciliation conflict (M18 Section 4).
  void recordConflict({
    required String conflictId,
    required String userId,
    required String referenceId,
    required String conflictType,
    Map<String, dynamic>? serverResponse,
  }) {
    db.execute(
      '''
      INSERT OR REPLACE INTO sync_conflicts
      (conflict_id, user_id, reference_id, conflict_type, server_response_json, detected_at_utc)
      VALUES (?, ?, ?, ?, ?, ?);
      ''',
      [
        conflictId,
        userId,
        referenceId,
        conflictType,
        serverResponse != null ? jsonEncode(serverResponse) : null,
        DateTime.now().toUtc().toIso8601String(),
      ],
    );
  }

  OfflineStudentClaimModel _mapClaimRow(Row r) {
    return OfflineStudentClaimModel(
      claimId: r['claim_id'] as String,
      permitId: r['permit_id'] as String,
      hostSessionId: r['host_session_id'] as String?,
      checkpointType: r['checkpoint_type'] as String,
      rotationSlot: r['rotation_slot'] as int,
      qrChallengeToken: r['qr_challenge_token'] as String,
      bleEvidence: r['ble_evidence_json'] != null
          ? jsonDecode(r['ble_evidence_json'] as String) as Map<String, dynamic>
          : null,
      clientCapturedAtUtc:
          DateTime.parse(r['client_captured_at_utc'] as String),
      status: r['status'] as String,
      userId: r['user_id'] as String,
      trustedDeviceId: r['trusted_device_id'] as String?,
      deviceProofSignature: r['device_proof_signature'] as String?,
    );
  }

  void reset() {
    db.execute('DELETE FROM sync_conflicts;');
    db.execute('DELETE FROM sync_outbox;');
    db.execute('DELETE FROM offline_student_claims;');
    db.execute('DELETE FROM offline_host_events;');
    db.execute('DELETE FROM offline_permits;');
    db.execute('DELETE FROM storage_metadata;');
  }

  void dispose() {
    db.close();
  }
}
