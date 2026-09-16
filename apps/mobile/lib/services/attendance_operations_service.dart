import 'dart:convert';
import 'dart:io';

/// DTO for an attendance correction request.
class CorrectionRequestModel {
  final String id;
  final String attendanceRecordId;
  final String attendanceSessionId;
  final String studentId;
  final String requestType;
  final String requestedStatus;
  final String reason;
  final String? supportingNote;
  final String status;
  final String? reviewNote;
  final DateTime? reviewedAtUtc;
  final DateTime createdAt;

  const CorrectionRequestModel({
    required this.id,
    required this.attendanceRecordId,
    required this.attendanceSessionId,
    required this.studentId,
    required this.requestType,
    required this.requestedStatus,
    required this.reason,
    this.supportingNote,
    required this.status,
    this.reviewNote,
    this.reviewedAtUtc,
    required this.createdAt,
  });

  factory CorrectionRequestModel.fromJson(Map<String, dynamic> json) {
    return CorrectionRequestModel(
      id: json['id'] as String,
      attendanceRecordId: json['attendance_record_id'] as String,
      attendanceSessionId: json['attendance_session_id'] as String,
      studentId: json['student_id'] as String,
      requestType: json['request_type'] as String? ?? 'OTHER',
      requestedStatus: json['requested_status'] as String? ?? 'PRESENT',
      reason: json['reason'] as String? ?? '',
      supportingNote: json['supporting_note'] as String?,
      status: json['status'] as String? ?? 'PENDING',
      reviewNote: json['review_note'] as String?,
      reviewedAtUtc: json['reviewed_at_utc'] != null
          ? DateTime.parse(json['reviewed_at_utc'] as String)
          : null,
      createdAt: json['created_at'] != null
          ? DateTime.parse(json['created_at'] as String)
          : DateTime.now().toUtc(),
    );
  }
}

/// DTO for an absence excuse request.
class ExcuseRequestModel {
  final String id;
  final String studentId;
  final String? attendanceRecordId;
  final String? attendanceSessionId;
  final String? classOccurrenceId;
  final String category;
  final String description;
  final String? documentReference;
  final String status;
  final String? reviewNote;
  final DateTime? reviewedAtUtc;
  final DateTime createdAt;

  const ExcuseRequestModel({
    required this.id,
    required this.studentId,
    this.attendanceRecordId,
    this.attendanceSessionId,
    this.classOccurrenceId,
    required this.category,
    required this.description,
    this.documentReference,
    required this.status,
    this.reviewNote,
    this.reviewedAtUtc,
    required this.createdAt,
  });

  factory ExcuseRequestModel.fromJson(Map<String, dynamic> json) {
    return ExcuseRequestModel(
      id: json['id'] as String,
      studentId: json['student_id'] as String,
      attendanceRecordId: json['attendance_record_id'] as String?,
      attendanceSessionId: json['attendance_session_id'] as String?,
      classOccurrenceId: json['class_occurrence_id'] as String?,
      category: json['category'] as String? ?? 'OTHER',
      description: json['description'] as String? ?? '',
      documentReference: json['document_reference'] as String?,
      status: json['status'] as String? ?? 'PENDING',
      reviewNote: json['review_note'] as String?,
      reviewedAtUtc: json['reviewed_at_utc'] != null
          ? DateTime.parse(json['reviewed_at_utc'] as String)
          : null,
      createdAt: json['created_at'] != null
          ? DateTime.parse(json['created_at'] as String)
          : DateTime.now().toUtc(),
    );
  }
}

/// DTO for a pre-class leave request (Section 38: LEAVE grants 0 credit).
class LeaveRequestModel {
  final String id;
  final String studentId;
  final String classOccurrenceId;
  final String reason;
  final String status;
  final String? reviewNote;
  final DateTime? reviewedAtUtc;
  final DateTime createdAt;

  const LeaveRequestModel({
    required this.id,
    required this.studentId,
    required this.classOccurrenceId,
    required this.reason,
    required this.status,
    this.reviewNote,
    this.reviewedAtUtc,
    required this.createdAt,
  });

  factory LeaveRequestModel.fromJson(Map<String, dynamic> json) {
    return LeaveRequestModel(
      id: json['id'] as String,
      studentId: json['student_id'] as String,
      classOccurrenceId: json['class_occurrence_id'] as String,
      reason: json['reason'] as String? ?? '',
      status: json['status'] as String? ?? 'PENDING',
      reviewNote: json['review_note'] as String?,
      reviewedAtUtc: json['reviewed_at_utc'] != null
          ? DateTime.parse(json['reviewed_at_utc'] as String)
          : null,
      createdAt: json['created_at'] != null
          ? DateTime.parse(json['created_at'] as String)
          : DateTime.now().toUtc(),
    );
  }
}

/// DTO for checking record eligibility for corrections and excuses.
class RecordEligibilityModel {
  final String recordId;
  final bool eligibleForCorrection;
  final String? correctionIneligibilityReason;
  final DateTime? correctionWindowDeadlineUtc;
  final bool hasOpenCorrection;
  final bool hasOpenExcuse;
  final String currentStatus;
  final double currentCredit;

  const RecordEligibilityModel({
    required this.recordId,
    required this.eligibleForCorrection,
    this.correctionIneligibilityReason,
    this.correctionWindowDeadlineUtc,
    required this.hasOpenCorrection,
    required this.hasOpenExcuse,
    required this.currentStatus,
    required this.currentCredit,
  });

  factory RecordEligibilityModel.fromJson(Map<String, dynamic> json) {
    return RecordEligibilityModel(
      recordId: json['record_id'] as String,
      eligibleForCorrection: json['eligible_for_correction'] as bool? ?? false,
      correctionIneligibilityReason:
          json['correction_ineligibility_reason'] as String?,
      correctionWindowDeadlineUtc:
          json['correction_window_deadline_utc'] != null
              ? DateTime.parse(json['correction_window_deadline_utc'] as String)
              : null,
      hasOpenCorrection: json['has_open_correction'] as bool? ?? false,
      hasOpenExcuse: json['has_open_excuse'] as bool? ?? false,
      currentStatus: json['current_status'] as String? ?? 'ABSENT',
      currentCredit: (json['current_credit'] as num?)?.toDouble() ?? 0.0,
    );
  }
}

/// DTO for an immutable revision item in the audit ledger.
class RevisionItemModel {
  final String id;
  final String eventType;
  final String? previousStatus;
  final String? newStatus;
  final double? previousCredit;
  final double? newCredit;
  final String? reason;
  final String actorUserId;
  final DateTime occurredAtUtc;

  const RevisionItemModel({
    required this.id,
    required this.eventType,
    this.previousStatus,
    this.newStatus,
    this.previousCredit,
    this.newCredit,
    this.reason,
    required this.actorUserId,
    required this.occurredAtUtc,
  });

  factory RevisionItemModel.fromJson(Map<String, dynamic> json) {
    return RevisionItemModel(
      id: json['id'] as String,
      eventType: json['event_type'] as String? ?? 'REVISED',
      previousStatus: json['previous_status'] as String?,
      newStatus: json['new_status'] as String?,
      previousCredit: (json['previous_credit'] as num?)?.toDouble(),
      newCredit: (json['new_credit'] as num?)?.toDouble(),
      reason: json['reason'] as String?,
      actorUserId: json['actor_user_id'] as String? ?? '',
      occurredAtUtc: json['occurred_at_utc'] != null
          ? DateTime.parse(json['occurred_at_utc'] as String)
          : DateTime.now().toUtc(),
    );
  }
}

/// DTO for comprehensive record timeline.
class RecordTimelineModel {
  final String recordId;
  final String sessionId;
  final String studentId;
  final String currentStatus;
  final double currentCredit;
  final int versionNo;
  final bool isManual;
  final String? manualReason;
  final List<RevisionItemModel> revisions;

  const RecordTimelineModel({
    required this.recordId,
    required this.sessionId,
    required this.studentId,
    required this.currentStatus,
    required this.currentCredit,
    required this.versionNo,
    required this.isManual,
    this.manualReason,
    required this.revisions,
  });

  factory RecordTimelineModel.fromJson(Map<String, dynamic> json) {
    final revList = (json['revisions'] as List<dynamic>?)
            ?.map((e) => RevisionItemModel.fromJson(e as Map<String, dynamic>))
            .toList() ??
        const [];
    return RecordTimelineModel(
      recordId: json['record_id'] as String,
      sessionId: json['session_id'] as String,
      studentId: json['student_id'] as String,
      currentStatus: json['current_status'] as String? ?? 'ABSENT',
      currentCredit: (json['current_credit'] as num?)?.toDouble() ?? 0.0,
      versionNo: json['version_no'] as int? ?? 1,
      isManual: json['is_manual'] as bool? ?? false,
      manualReason: json['manual_reason'] as String?,
      revisions: revList,
    );
  }
}

/// Exception representing an operational domain or network error.
class AttendanceOperationsException implements Exception {
  final String message;
  final String? code;
  final int? statusCode;

  const AttendanceOperationsException({
    required this.message,
    this.code,
    this.statusCode,
  });

  @override
  String toString() =>
      'AttendanceOperationsException: $message (${code ?? 'UNKNOWN'} [${statusCode ?? 0}])';
}

/// Service handling student attendance operations, corrections, excuses, leave,
/// and audit timeline queries.
class AttendanceOperationsService {
  final String baseUrl;
  final HttpClient _client;

  AttendanceOperationsService({
    String? baseUrl,
    HttpClient? client,
  })  : baseUrl = baseUrl ?? 'http://10.0.2.2:8000',
        _client = client ?? HttpClient();

  /// Check whether an attendance record is within the allowed correction window
  /// and eligible for submission.
  Future<RecordEligibilityModel> checkEligibility({
    required String recordId,
    required String authToken,
  }) async {
    final uri = Uri.parse(
        '$baseUrl/api/v1/attendance/operations/records/$recordId/eligibility');
    final response = await _sendRequest('GET', uri, authToken: authToken);
    final json = jsonDecode(response) as Map<String, dynamic>;
    return RecordEligibilityModel.fromJson(
        json['data'] as Map<String, dynamic>);
  }

  /// Submit a student attendance correction request.
  Future<CorrectionRequestModel> submitCorrectionRequest({
    required String recordId,
    required String requestType,
    required String requestedStatus,
    required String reason,
    String? supportingNote,
    required String authToken,
  }) async {
    final uri = Uri.parse('$baseUrl/api/v1/attendance/operations/corrections');
    final body = jsonEncode({
      'attendance_record_id': recordId,
      'request_type': requestType,
      'requested_status': requestedStatus,
      'reason': reason,
      if (supportingNote != null) 'supporting_note': supportingNote,
    });

    final response =
        await _sendRequest('POST', uri, authToken: authToken, body: body);
    final json = jsonDecode(response) as Map<String, dynamic>;
    return CorrectionRequestModel.fromJson(
        json['data'] as Map<String, dynamic>);
  }

  /// Cancel a pending correction request.
  Future<CorrectionRequestModel> cancelCorrectionRequest({
    required String requestId,
    required String authToken,
  }) async {
    final uri = Uri.parse(
        '$baseUrl/api/v1/attendance/operations/corrections/$requestId/cancel');
    final response = await _sendRequest('POST', uri, authToken: authToken);
    final json = jsonDecode(response) as Map<String, dynamic>;
    return CorrectionRequestModel.fromJson(
        json['data'] as Map<String, dynamic>);
  }

  /// List current student's correction requests.
  Future<List<CorrectionRequestModel>> getMyCorrections({
    required String authToken,
  }) async {
    final uri =
        Uri.parse('$baseUrl/api/v1/attendance/operations/corrections/my');
    final response = await _sendRequest('GET', uri, authToken: authToken);
    final json = jsonDecode(response) as Map<String, dynamic>;
    final data = (json['data'] as List<dynamic>?) ?? [];
    return data
        .map((e) => CorrectionRequestModel.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  /// Submit an absence excuse request.
  Future<ExcuseRequestModel> submitExcuseRequest({
    String? attendanceSessionId,
    String? classOccurrenceId,
    String? attendanceRecordId,
    required String category,
    required String description,
    String? documentReference,
    required String authToken,
  }) async {
    final uri = Uri.parse('$baseUrl/api/v1/attendance/operations/excuses');
    final body = jsonEncode({
      if (attendanceSessionId != null)
        'attendance_session_id': attendanceSessionId,
      if (classOccurrenceId != null) 'class_occurrence_id': classOccurrenceId,
      if (attendanceRecordId != null)
        'attendance_record_id': attendanceRecordId,
      'category': category,
      'description': description,
      if (documentReference != null) 'document_reference': documentReference,
    });

    final response =
        await _sendRequest('POST', uri, authToken: authToken, body: body);
    final json = jsonDecode(response) as Map<String, dynamic>;
    return ExcuseRequestModel.fromJson(json['data'] as Map<String, dynamic>);
  }

  /// List current student's absence excuses.
  Future<List<ExcuseRequestModel>> getMyExcuses({
    required String authToken,
  }) async {
    final uri = Uri.parse('$baseUrl/api/v1/attendance/operations/excuses/my');
    final response = await _sendRequest('GET', uri, authToken: authToken);
    final json = jsonDecode(response) as Map<String, dynamic>;
    final data = (json['data'] as List<dynamic>?) ?? [];
    return data
        .map((e) => ExcuseRequestModel.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  /// Submit a pre-class leave request (Section 38: LEAVE grants 0 credit).
  Future<LeaveRequestModel> submitLeaveRequest({
    required String classOccurrenceId,
    required String reason,
    required String authToken,
  }) async {
    final uri = Uri.parse('$baseUrl/api/v1/attendance/operations/leave');
    final body = jsonEncode({
      'class_occurrence_id': classOccurrenceId,
      'reason': reason,
    });

    final response =
        await _sendRequest('POST', uri, authToken: authToken, body: body);
    final json = jsonDecode(response) as Map<String, dynamic>;
    return LeaveRequestModel.fromJson(json['data'] as Map<String, dynamic>);
  }

  /// List current student's pre-class leave requests.
  Future<List<LeaveRequestModel>> getMyLeaves({
    required String authToken,
  }) async {
    final uri = Uri.parse('$baseUrl/api/v1/attendance/operations/leave/my');
    final response = await _sendRequest('GET', uri, authToken: authToken);
    final json = jsonDecode(response) as Map<String, dynamic>;
    final data = (json['data'] as List<dynamic>?) ?? [];
    return data
        .map((e) => LeaveRequestModel.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  /// Get immutable revision timeline for an attendance record.
  Future<RecordTimelineModel> getRecordTimeline({
    required String recordId,
    required String authToken,
  }) async {
    final uri = Uri.parse(
        '$baseUrl/api/v1/attendance/operations/records/$recordId/timeline');
    final response = await _sendRequest('GET', uri, authToken: authToken);
    final json = jsonDecode(response) as Map<String, dynamic>;
    return RecordTimelineModel.fromJson(json['data'] as Map<String, dynamic>);
  }

  /// Internal HTTP dispatcher with offline-safety checks and error parsing.
  Future<String> _sendRequest(
    String method,
    Uri uri, {
    required String authToken,
    String? body,
  }) async {
    try {
      final request = await _client.openUrl(method, uri);
      request.headers.set(HttpHeaders.acceptHeader, 'application/json');
      request.headers.set(HttpHeaders.authorizationHeader, 'Bearer $authToken');
      if (body != null) {
        request.headers.set(
            HttpHeaders.contentTypeHeader, 'application/json; charset=utf-8');
        request.write(body);
      }

      final response = await request.close();
      final responseBody = await response.transform(utf8.decoder).join();

      if (response.statusCode >= 200 && response.statusCode < 300) {
        return responseBody;
      }

      // Handle 409 Conflict specifically
      if (response.statusCode == 409) {
        throw const AttendanceOperationsException(
          message:
              'A conflicting request already exists for this attendance record.',
          code: 'DUPLICATE_OPEN_REQUEST',
          statusCode: 409,
        );
      }

      try {
        final errJson = jsonDecode(responseBody) as Map<String, dynamic>;
        final error = errJson['error'] as Map<String, dynamic>?;
        throw AttendanceOperationsException(
          message: error?['message'] as String? ??
              'Request failed with status ${response.statusCode}',
          code: error?['code'] as String?,
          statusCode: response.statusCode,
        );
      } catch (e) {
        if (e is AttendanceOperationsException) rethrow;
        throw AttendanceOperationsException(
          message: 'Server returned HTTP ${response.statusCode}',
          statusCode: response.statusCode,
        );
      }
    } on SocketException {
      throw const AttendanceOperationsException(
        message:
            'Connect to the university system to submit this request. Offline submission is not supported for operations.',
        code: 'OFFLINE_MODE',
      );
    }
  }

  void close() {
    _client.close(force: true);
  }
}
