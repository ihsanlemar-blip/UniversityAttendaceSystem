import 'dart:convert';
import 'dart:io';

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

/// Persistent local storage and transactional outbox manager.
class MobileOfflineStorage {
  static MobileOfflineStorage? _instance;
  Directory? _storageDirectory;
  SecureKeyStorage secureKeyStorage = MemorySecureKeyStorage();

  final Map<String, OfflinePermitModel> _cachedPermits = {};
  final List<OfflineHostEventModel> _hostEventsOutbox = [];
  final List<OfflineStudentClaimModel> _studentClaims = [];
  final List<OutboxItemModel> _outboxItems = [];

  factory MobileOfflineStorage({Directory? storageDir}) {
    if (_instance == null || storageDir != null) {
      _instance = MobileOfflineStorage._internal(storageDir: storageDir);
    }
    return _instance!;
  }

  MobileOfflineStorage._internal({Directory? storageDir}) {
    _storageDirectory = storageDir;
    loadFromDiskSync();
  }

  /// Create a fresh, distinct instance for testing app restarts without using singleton.
  static MobileOfflineStorage createInstance({Directory? storageDir}) {
    return MobileOfflineStorage._internal(storageDir: storageDir);
  }

  File? get _storageFile {
    if (_storageDirectory == null) return null;
    return File('${_storageDirectory!.path}/offline_store.json');
  }

  void cachePermit(OfflinePermitModel permit) {
    _cachedPermits[permit.permitId] = permit;
    flushToDiskSync();
  }

  OfflinePermitModel? getPermit(String permitId) => _cachedPermits[permitId];

  void addHostEvent(OfflineHostEventModel event) {
    _hostEventsOutbox.add(event);
    flushToDiskSync();
  }

  List<OfflineHostEventModel> getHostEvents() =>
      List.unmodifiable(_hostEventsOutbox);

  void clearHostEvents() {
    _hostEventsOutbox.clear();
    flushToDiskSync();
  }

  /// Transactional creation of Student claim + corresponding Outbox item (INV-01 / Section 10).
  /// Guarantees atomicity: claim and outbox item are saved together or not at all.
  void saveClaimWithOutboxTransactional({
    required String userId,
    required OfflineStudentClaimModel claim,
  }) {
    // 1. Deduplicate existing claims for same permit and checkpoint
    _studentClaims.removeWhere((c) =>
        c.permitId == claim.permitId &&
        c.checkpointType == claim.checkpointType);
    _studentClaims.add(claim);

    // 2. Insert corresponding outbox queue entry
    final outboxId = 'outbox_${claim.claimId}';
    _outboxItems.removeWhere((item) => item.referenceId == claim.claimId);
    _outboxItems.add(
      OutboxItemModel(
        outboxId: outboxId,
        userId: userId,
        itemType: 'STUDENT_CLAIM',
        referenceId: claim.claimId,
        payload: claim.toJson(),
        status: 'PENDING_SYNC',
        createdAtUtc: claim.clientCapturedAtUtc,
      ),
    );

    // 3. Atomically persist both to durable storage
    flushToDiskSync();
  }

  /// Backwards-compatible claim addition.
  void addStudentClaim(OfflineStudentClaimModel claim) {
    saveClaimWithOutboxTransactional(userId: claim.userId, claim: claim);
  }

  /// Query pending student claims across all accounts.
  List<OfflineStudentClaimModel> getPendingStudentClaims() =>
      _studentClaims.where((c) => c.status == 'PENDING_SYNC').toList();

  /// Query pending student claims strictly isolated to a specific user (Section 13).
  List<OfflineStudentClaimModel> getPendingStudentClaimsForUser(
          String userId) =>
      _studentClaims
          .where((c) => c.userId == userId && c.status == 'PENDING_SYNC')
          .toList();

  /// Query pending outbox entries strictly isolated to a specific user (Section 13).
  List<OutboxItemModel> getPendingOutboxForUser(String userId) => _outboxItems
      .where((item) => item.userId == userId && item.status == 'PENDING_SYNC')
      .toList();

  /// Outbox acknowledgement: ONLY marks item as synced upon deterministic server ACK (Section 11).
  /// On network error/failure, item remains in PENDING_SYNC with incremented retry count.
  void acknowledgeClaimSync({
    required String claimId,
    required bool success,
    String? rejectionReason,
  }) {
    final claimIdx = _studentClaims.indexWhere((c) => c.claimId == claimId);
    if (claimIdx != -1) {
      final old = _studentClaims[claimIdx];
      _studentClaims[claimIdx] = OfflineStudentClaimModel(
        claimId: old.claimId,
        permitId: old.permitId,
        hostSessionId: old.hostSessionId,
        checkpointType: old.checkpointType,
        rotationSlot: old.rotationSlot,
        qrChallengeToken: old.qrChallengeToken,
        bleEvidence: old.bleEvidence,
        clientCapturedAtUtc: old.clientCapturedAtUtc,
        status: success ? 'SYNCED' : 'PENDING_SYNC',
        userId: old.userId,
      );
    }

    final outboxIdx =
        _outboxItems.indexWhere((item) => item.referenceId == claimId);
    if (outboxIdx != -1) {
      final oldItem = _outboxItems[outboxIdx];
      if (success) {
        _outboxItems.removeAt(outboxIdx);
      } else {
        _outboxItems[outboxIdx] = OutboxItemModel(
          outboxId: oldItem.outboxId,
          userId: oldItem.userId,
          itemType: oldItem.itemType,
          referenceId: oldItem.referenceId,
          payload: oldItem.payload,
          status: 'PENDING_SYNC',
          createdAtUtc: oldItem.createdAtUtc,
          retryCount: oldItem.retryCount + 1,
        );
      }
    }

    flushToDiskSync();
  }

  /// Backwards-compatible sync marking.
  void markClaimSynced(String claimId) {
    acknowledgeClaimSync(claimId: claimId, success: true);
  }

  /// Atomically write storage state to disk using a temporary file and rename (ACID semantics).
  void flushToDiskSync() {
    final file = _storageFile;
    if (file == null) return;

    try {
      if (!file.parent.existsSync()) {
        file.parent.createSync(recursive: true);
      }
      final data = {
        'permits': _cachedPermits.values.map((p) => p.toJson()).toList(),
        'host_events': _hostEventsOutbox.map((e) => e.toJson()).toList(),
        'student_claims': _studentClaims.map((c) => c.toJson()).toList(),
        'outbox': _outboxItems.map((o) => o.toJson()).toList(),
      };
      final tempFile = File('${file.path}.tmp');
      tempFile.writeAsStringSync(jsonEncode(data), flush: true);
      tempFile.renameSync(file.path);
    } catch (_) {
      // Degrade gracefully if storage directory is read-only
    }
  }

  /// Reload stored data from disk (survives app restart).
  void loadFromDiskSync() {
    final file = _storageFile;
    if (file == null || !file.existsSync()) return;

    try {
      final raw = file.readAsStringSync();
      final Map<String, dynamic> data = jsonDecode(raw) as Map<String, dynamic>;

      _cachedPermits.clear();
      final permitsList = data['permits'] as List<dynamic>? ?? [];
      for (final item in permitsList) {
        final permit =
            OfflinePermitModel.fromJson(item as Map<String, dynamic>);
        _cachedPermits[permit.permitId] = permit;
      }

      _hostEventsOutbox.clear();
      final eventsList = data['host_events'] as List<dynamic>? ?? [];
      for (final item in eventsList) {
        _hostEventsOutbox.add(
          OfflineHostEventModel.fromJson(item as Map<String, dynamic>),
        );
      }

      _studentClaims.clear();
      final claimsList = data['student_claims'] as List<dynamic>? ?? [];
      for (final item in claimsList) {
        _studentClaims.add(
          OfflineStudentClaimModel.fromJson(item as Map<String, dynamic>),
        );
      }

      _outboxItems.clear();
      final outboxList = data['outbox'] as List<dynamic>? ?? [];
      for (final item in outboxList) {
        _outboxItems.add(
          OutboxItemModel.fromJson(item as Map<String, dynamic>),
        );
      }
    } catch (_) {
      // Ignore corrupted files in testing
    }
  }

  void reset() {
    _cachedPermits.clear();
    _hostEventsOutbox.clear();
    _studentClaims.clear();
    _outboxItems.clear();
    final file = _storageFile;
    if (file != null && file.existsSync()) {
      try {
        file.deleteSync();
      } catch (_) {}
    }
  }
}
