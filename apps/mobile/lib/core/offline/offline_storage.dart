import 'dart:io';

import 'sqlite_offline_storage.dart';

/// Local offline storage and outbox for mobile offline attendance (M12).
class OfflinePermitModel {
  final String permitId;
  final String attendanceSessionId;
  final String classOccurrenceId;
  final String temporaryHostPublicKey;
  final String signedPermitToken;
  final DateTime validFromUtc;
  final DateTime validUntilUtc;

  OfflinePermitModel({
    required this.permitId,
    required this.attendanceSessionId,
    required this.classOccurrenceId,
    required this.temporaryHostPublicKey,
    required this.signedPermitToken,
    required this.validFromUtc,
    required this.validUntilUtc,
  });

  Map<String, dynamic> toJson() => {
        'permit_id': permitId,
        'attendance_session_id': attendanceSessionId,
        'class_occurrence_id': classOccurrenceId,
        'temporary_host_public_key': temporaryHostPublicKey,
        'signed_permit_token': signedPermitToken,
        'valid_from_utc': validFromUtc.toIso8601String(),
        'valid_until_utc': validUntilUtc.toIso8601String(),
      };

  factory OfflinePermitModel.fromJson(Map<String, dynamic> json) =>
      OfflinePermitModel(
        permitId: json['permit_id'] as String,
        attendanceSessionId: json['attendance_session_id'] as String,
        classOccurrenceId: json['class_occurrence_id'] as String,
        temporaryHostPublicKey: json['temporary_host_public_key'] as String,
        signedPermitToken: json['signed_permit_token'] as String,
        validFromUtc: DateTime.parse(json['valid_from_utc'] as String),
        validUntilUtc: DateTime.parse(json['valid_until_utc'] as String),
      );
}

class OfflineHostEventModel {
  final int sequenceNumber;
  final String eventType;
  final String prevEventHash;
  final String eventHash;
  final Map<String, dynamic> payload;
  final String signature;
  final String occurredAtUtc;

  OfflineHostEventModel({
    required this.sequenceNumber,
    required this.eventType,
    required this.prevEventHash,
    required this.eventHash,
    required this.payload,
    required this.signature,
    required this.occurredAtUtc,
  });

  Map<String, dynamic> toJson() => {
        'sequence_number': sequenceNumber,
        'event_type': eventType,
        'prev_event_hash': prevEventHash,
        'event_hash': eventHash,
        'payload': payload,
        'signature': signature,
        'occurred_at_utc': occurredAtUtc,
      };

  factory OfflineHostEventModel.fromJson(Map<String, dynamic> json) =>
      OfflineHostEventModel(
        sequenceNumber: json['sequence_number'] as int,
        eventType: json['event_type'] as String,
        prevEventHash: json['prev_event_hash'] as String,
        eventHash: json['event_hash'] as String,
        payload: json['payload'] as Map<String, dynamic>,
        signature: json['signature'] as String,
        occurredAtUtc: json['occurred_at_utc'] as String,
      );
}

class OfflineStudentClaimModel {
  final String claimId;
  final String permitId;
  final String? hostSessionId;
  final String checkpointType;
  final int rotationSlot;
  final String qrChallengeToken;
  final Map<String, dynamic>? bleEvidence;
  final DateTime clientCapturedAtUtc;
  final String status; // PENDING_SYNC, SYNCED, REJECTED
  final String userId; // Account isolation context (M12.1 Section 13)
  final String? trustedDeviceId;
  final String? deviceProofSignature;

  OfflineStudentClaimModel({
    required this.claimId,
    required this.permitId,
    this.hostSessionId,
    required this.checkpointType,
    required this.rotationSlot,
    required this.qrChallengeToken,
    this.bleEvidence,
    required this.clientCapturedAtUtc,
    this.status = 'PENDING_SYNC',
    this.userId = 'default_student',
    this.trustedDeviceId,
    this.deviceProofSignature,
  });

  Map<String, dynamic> toJson() => {
        'claim_id': claimId,
        'permit_id': permitId,
        'host_session_id': hostSessionId,
        'checkpoint_type': checkpointType,
        'rotation_slot': rotationSlot,
        'qr_challenge_token': qrChallengeToken,
        'ble_evidence': bleEvidence,
        'client_captured_at_utc': clientCapturedAtUtc.toIso8601String(),
        'status': status,
        'user_id': userId,
        'trusted_device_id': trustedDeviceId,
        'device_proof_signature': deviceProofSignature,
      };

  factory OfflineStudentClaimModel.fromJson(Map<String, dynamic> json) =>
      OfflineStudentClaimModel(
        claimId: json['claim_id'] as String,
        permitId: json['permit_id'] as String,
        hostSessionId: json['host_session_id'] as String?,
        checkpointType: json['checkpoint_type'] as String,
        rotationSlot: json['rotation_slot'] as int,
        qrChallengeToken: json['qr_challenge_token'] as String,
        bleEvidence: json['ble_evidence'] as Map<String, dynamic>?,
        clientCapturedAtUtc:
            DateTime.parse(json['client_captured_at_utc'] as String),
        status: json['status'] as String? ?? 'PENDING_SYNC',
        userId: json['user_id'] as String? ?? 'default_student',
        trustedDeviceId: json['trusted_device_id'] as String?,
        deviceProofSignature: json['device_proof_signature'] as String?,
      );
}

/// Outbox item representing an atomic submission queue entry (M12.1 Section 10 & 11).
class OutboxItemModel {
  final String outboxId;
  final String userId;
  final String itemType; // 'STUDENT_CLAIM', 'HOST_EVENTS'
  final String referenceId; // claimId or hostSessionId
  final Map<String, dynamic> payload;
  final String status; // 'PENDING_SYNC', 'SYNCED', 'FAILED'
  final DateTime createdAtUtc;
  final int retryCount;

  OutboxItemModel({
    required this.outboxId,
    required this.userId,
    required this.itemType,
    required this.referenceId,
    required this.payload,
    this.status = 'PENDING_SYNC',
    required this.createdAtUtc,
    this.retryCount = 0,
  });

  Map<String, dynamic> toJson() => {
        'outbox_id': outboxId,
        'user_id': userId,
        'item_type': itemType,
        'reference_id': referenceId,
        'payload': payload,
        'status': status,
        'created_at_utc': createdAtUtc.toIso8601String(),
        'retry_count': retryCount,
      };

  factory OutboxItemModel.fromJson(Map<String, dynamic> json) =>
      OutboxItemModel(
        outboxId: json['outbox_id'] as String,
        userId: json['user_id'] as String,
        itemType: json['item_type'] as String,
        referenceId: json['reference_id'] as String,
        payload: json['payload'] as Map<String, dynamic>,
        status: json['status'] as String? ?? 'PENDING_SYNC',
        createdAtUtc: DateTime.parse(json['created_at_utc'] as String),
        retryCount: json['retry_count'] as int? ?? 0,
      );
}

/// Dedicated abstraction for secure host private-key storage (M12.1 Section 14 & 15).
/// Isolated from standard storage tables, never logged, and deleted upon session sync.
abstract class SecureKeyStorage {
  Future<void> writePrivateKey({
    required String permitId,
    required String privateKeyPem,
  });
  Future<String?> readPrivateKey({required String permitId});
  Future<void> deletePrivateKey({required String permitId});
}

/// In-memory implementation of secure storage for tests and platform fallback.
class MemorySecureKeyStorage implements SecureKeyStorage {
  final Map<String, String> _keys = {};

  @override
  Future<void> writePrivateKey({
    required String permitId,
    required String privateKeyPem,
  }) async {
    _keys[permitId] = privateKeyPem;
  }

  @override
  Future<String?> readPrivateKey({required String permitId}) async {
    return _keys[permitId];
  }

  @override
  Future<void> deletePrivateKey({required String permitId}) async {
    _keys.remove(permitId);
  }
}

/// Persistent local storage and transactional outbox manager backed by SQLite (M18 Part 2).
class MobileOfflineStorage {
  static MobileOfflineStorage? _instance;
  late final SqliteOfflineStorage _sqliteStorage;

  SqliteOfflineStorage get sqliteStorage => _sqliteStorage;

  SecureKeyStorage get secureKeyStorage => _sqliteStorage.secureKeyStorage;
  set secureKeyStorage(SecureKeyStorage storage) {
    // Retain compatibility with test setups injecting custom secure storage
  }

  factory MobileOfflineStorage({Directory? storageDir}) {
    if (_instance == null || storageDir != null) {
      _instance = MobileOfflineStorage._internal(storageDir: storageDir);
    }
    return _instance!;
  }

  MobileOfflineStorage._internal({Directory? storageDir}) {
    _sqliteStorage = SqliteOfflineStorage(storageDir: storageDir);
  }

  /// Create a fresh, distinct instance for testing app restarts without using singleton.
  static MobileOfflineStorage createInstance({Directory? storageDir}) {
    return MobileOfflineStorage._internal(storageDir: storageDir);
  }

  void cachePermit(OfflinePermitModel permit) =>
      _sqliteStorage.cachePermit(permit);

  OfflinePermitModel? getPermit(String permitId) =>
      _sqliteStorage.getPermit(permitId);

  void addHostEvent(OfflineHostEventModel event) =>
      _sqliteStorage.addHostEvent(event);

  List<OfflineHostEventModel> getHostEvents() => _sqliteStorage.getHostEvents();

  void clearHostEvents() => _sqliteStorage.clearHostEvents();

  /// Transactional creation of Student claim + corresponding Outbox item (INV-01 / Section 10).
  /// Guarantees atomicity via SQLite transaction: claim and outbox item are saved together or not at all.
  void saveClaimWithOutboxTransactional({
    required String userId,
    required OfflineStudentClaimModel claim,
  }) =>
      _sqliteStorage.saveClaimWithOutboxTransactional(
        userId: userId,
        claim: claim,
      );

  /// Backwards-compatible claim addition.
  void addStudentClaim(OfflineStudentClaimModel claim) {
    saveClaimWithOutboxTransactional(userId: claim.userId, claim: claim);
  }

  /// Query pending student claims across all accounts.
  List<OfflineStudentClaimModel> getPendingStudentClaims() =>
      _sqliteStorage.getPendingStudentClaims();

  /// Query pending student claims strictly isolated to a specific user (Section 13).
  List<OfflineStudentClaimModel> getPendingStudentClaimsForUser(
          String userId) =>
      _sqliteStorage.getPendingStudentClaimsForUser(userId);

  /// Query pending outbox entries strictly isolated to a specific user (Section 13).
  List<OutboxItemModel> getPendingOutboxForUser(String userId) =>
      _sqliteStorage.getPendingOutboxForUser(userId);

  /// Outbox acknowledgement: ONLY marks item as synced upon deterministic server ACK (Section 11).
  void acknowledgeClaimSync({
    required String claimId,
    required bool success,
    String? rejectionReason,
    String failureStatus = 'PENDING_SYNC',
  }) =>
      _sqliteStorage.acknowledgeClaimSync(
        claimId: claimId,
        success: success,
        rejectionReason: rejectionReason,
        failureStatus: failureStatus,
      );

  /// Backwards-compatible sync marking.
  void markClaimSynced(String claimId) {
    acknowledgeClaimSync(claimId: claimId, success: true);
  }

  /// No-op: SQLite writes synchronously to disk with ACID durability.
  void flushToDiskSync() {}

  /// No-op: SQLite queries directly from disk.
  void loadFromDiskSync() {}

  void reset() => _sqliteStorage.reset();

  void dispose() => _sqliteStorage.dispose();
}
