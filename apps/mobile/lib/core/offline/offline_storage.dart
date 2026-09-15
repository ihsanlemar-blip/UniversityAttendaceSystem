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
      );
}

/// In-memory and local cache outbox manager.
class MobileOfflineStorage {
  static final MobileOfflineStorage _instance = MobileOfflineStorage._();
  factory MobileOfflineStorage() => _instance;
  MobileOfflineStorage._();

  final Map<String, OfflinePermitModel> _cachedPermits = {};
  final List<OfflineHostEventModel> _hostEventsOutbox = [];
  final List<OfflineStudentClaimModel> _studentClaimsOutbox = [];

  void cachePermit(OfflinePermitModel permit) {
    _cachedPermits[permit.permitId] = permit;
  }

  OfflinePermitModel? getPermit(String permitId) => _cachedPermits[permitId];

  void addHostEvent(OfflineHostEventModel event) {
    _hostEventsOutbox.add(event);
  }

  List<OfflineHostEventModel> getHostEvents() =>
      List.unmodifiable(_hostEventsOutbox);

  void clearHostEvents() {
    _hostEventsOutbox.clear();
  }

  void addStudentClaim(OfflineStudentClaimModel claim) {
    // Deduplicate by permitId and checkpointType
    _studentClaimsOutbox.removeWhere((c) =>
        c.permitId == claim.permitId &&
        c.checkpointType == claim.checkpointType);
    _studentClaimsOutbox.add(claim);
  }

  List<OfflineStudentClaimModel> getPendingStudentClaims() =>
      _studentClaimsOutbox.where((c) => c.status == 'PENDING_SYNC').toList();

  void markClaimSynced(String claimId) {
    final idx = _studentClaimsOutbox.indexWhere((c) => c.claimId == claimId);
    if (idx != -1) {
      final old = _studentClaimsOutbox[idx];
      _studentClaimsOutbox[idx] = OfflineStudentClaimModel(
        claimId: old.claimId,
        permitId: old.permitId,
        hostSessionId: old.hostSessionId,
        checkpointType: old.checkpointType,
        rotationSlot: old.rotationSlot,
        qrChallengeToken: old.qrChallengeToken,
        bleEvidence: old.bleEvidence,
        clientCapturedAtUtc: old.clientCapturedAtUtc,
        status: 'SYNCED',
      );
    }
  }

  void reset() {
    _cachedPermits.clear();
    _hostEventsOutbox.clear();
    _studentClaimsOutbox.clear();
  }
}
