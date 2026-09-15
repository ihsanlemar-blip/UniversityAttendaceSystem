import 'dart:convert';
import 'dart:io';
import 'ble_scanner_service.dart';

/// Result data structure returned upon unified presence verification by server.
class PresenceCheckInResult {
  final bool accepted;
  final String checkpointType;
  final bool alreadyCredited;
  final DateTime verifiedAt;
  final String attendanceRecordId;
  final List<String> verifiedFactors;
  final String presenceMode;

  const PresenceCheckInResult({
    required this.accepted,
    required this.checkpointType,
    required this.alreadyCredited,
    required this.verifiedAt,
    required this.attendanceRecordId,
    required this.verifiedFactors,
    required this.presenceMode,
  });

  factory PresenceCheckInResult.fromJson(Map<String, dynamic> json) {
    return PresenceCheckInResult(
      accepted: json['accepted'] as bool? ?? false,
      checkpointType: json['checkpoint_type'] as String? ?? 'UNKNOWN',
      alreadyCredited: json['already_credited'] as bool? ?? false,
      verifiedAt: json['verified_at'] != null
          ? DateTime.parse(json['verified_at'] as String)
          : DateTime.now().toUtc(),
      attendanceRecordId: json['attendance_record_id'] as String? ?? '',
      verifiedFactors: (json['verified_factors'] as List<dynamic>?)
              ?.map((e) => e.toString())
              .toList() ??
          const [],
      presenceMode: json['presence_mode'] as String? ?? 'QR_ONLY',
    );
  }
}

/// Exception thrown when presence check-in is rejected by server.
class PresenceCheckInException implements Exception {
  final String code;
  final String message;
  final int statusCode;

  const PresenceCheckInException({
    required this.code,
    required this.message,
    required this.statusCode,
  });

  @override
  String toString() =>
      'PresenceCheckInException($code: $message [HTTP $statusCode])';
}

/// Mobile service responsible for submitting multi-factor presence evidence to backend.
class PresenceCheckInService {
  final String baseUrl;
  final HttpClient _client;

  PresenceCheckInService({
    String? baseUrl,
    HttpClient? client,
  })  : baseUrl = baseUrl ?? 'http://10.0.2.2:8000',
        _client = client ?? HttpClient();

  /// Submit dynamic presence evidence (QR token and/or BLE observation) to server.
  /// (INV-01: student identity derived strictly from authenticated user token).
  Future<PresenceCheckInResult> submitPresenceCheckIn({
    String? qrToken,
    BleObservation? bleObservation,
    Map<String, dynamic>? deviceProof,
    required String authToken,
  }) async {
    final uri = Uri.parse('$baseUrl/api/v1/attendance/presence/check-in');
    final request = await _client.postUrl(uri);

    request.headers.set(HttpHeaders.contentTypeHeader, 'application/json');
    request.headers.set(HttpHeaders.acceptHeader, 'application/json');
    request.headers.set(HttpHeaders.authorizationHeader, 'Bearer $authToken');

    final Map<String, dynamic> body = {};
    if (qrToken != null && qrToken.isNotEmpty) {
      body['qr_token'] = qrToken;
    }
    if (bleObservation != null) {
      body['ble_observation'] = bleObservation.toJson();
    }
    if (deviceProof != null) {
      body['device_proof'] = deviceProof;
    }

    final payload = jsonEncode(body);
    request.write(payload);

    final response = await request.close();
    final responseBody = await response.transform(utf8.decoder).join();

    Map<String, dynamic> decoded;
    try {
      decoded = jsonDecode(responseBody) as Map<String, dynamic>;
    } catch (_) {
      throw PresenceCheckInException(
        code: 'MALFORMED_RESPONSE',
        message: 'Invalid response from attendance server.',
        statusCode: response.statusCode,
      );
    }

    if (response.statusCode >= 200 && response.statusCode < 300) {
      final data = decoded['data'] as Map<String, dynamic>? ?? {};
      return PresenceCheckInResult.fromJson(data);
    } else {
      final err = decoded['error'] as Map<String, dynamic>?;
      final code = err?['code'] as String? ?? 'CHECKIN_ERROR';
      final message =
          err?['message'] as String? ?? 'Attendance check-in rejected.';
      throw PresenceCheckInException(
        code: code,
        message: message,
        statusCode: response.statusCode,
      );
    }
  }
}
