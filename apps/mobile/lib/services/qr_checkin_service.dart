import 'dart:convert';
import 'dart:io';

/// Result data structure returned upon dynamic QR verification by server.
class QrCheckInResult {
  final bool accepted;
  final String checkpointType;
  final bool alreadyCredited;
  final DateTime verifiedAt;
  final String attendanceRecordId;

  const QrCheckInResult({
    required this.accepted,
    required this.checkpointType,
    required this.alreadyCredited,
    required this.verifiedAt,
    required this.attendanceRecordId,
  });

  factory QrCheckInResult.fromJson(Map<String, dynamic> json) {
    return QrCheckInResult(
      accepted: json['accepted'] as bool? ?? false,
      checkpointType: json['checkpoint_type'] as String? ?? 'UNKNOWN',
      alreadyCredited: json['already_credited'] as bool? ?? false,
      verifiedAt: json['verified_at'] != null
          ? DateTime.parse(json['verified_at'] as String)
          : DateTime.now().toUtc(),
      attendanceRecordId: json['attendance_record_id'] as String? ?? '',
    );
  }
}

/// Exception thrown when QR check-in is rejected by server.
class QrCheckInException implements Exception {
  final String code;
  final String message;
  final int statusCode;

  const QrCheckInException({
    required this.code,
    required this.message,
    required this.statusCode,
  });

  @override
  String toString() => 'QrCheckInException($code: $message [HTTP $statusCode])';
}

/// Mobile service responsible for submitting scanned dynamic QR tokens to the backend.
class QrCheckInService {
  final String baseUrl;
  final HttpClient _client;

  QrCheckInService({
    String? baseUrl,
    HttpClient? client,
  })  : baseUrl = baseUrl ?? 'http://10.0.2.2:8000',
        _client = client ?? HttpClient();

  /// Submit dynamic presence token to server (INV-01: student identity derived strictly from auth token).
  Future<QrCheckInResult> submitQrCheckIn({
    required String token,
    Map<String, dynamic>? deviceProof,
    Map<String, dynamic>? networkProof,
    required String authToken,
  }) async {
    final uri = Uri.parse('$baseUrl/api/v1/attendance/qr/check-in');
    final request = await _client.postUrl(uri);

    request.headers.set(HttpHeaders.contentTypeHeader, 'application/json');
    request.headers.set(HttpHeaders.acceptHeader, 'application/json');
    request.headers.set(HttpHeaders.authorizationHeader, 'Bearer $authToken');

    final Map<String, dynamic> body = {'token': token};
    if (deviceProof != null) {
      body['device_proof'] = deviceProof;
    }
    if (networkProof != null) {
      body['network_proof'] = networkProof;
    }
    final payload = jsonEncode(body);
    request.write(payload);

    final response = await request.close();
    final responseBody = await response.transform(utf8.decoder).join();

    Map<String, dynamic> decoded;
    try {
      decoded = jsonDecode(responseBody) as Map<String, dynamic>;
    } catch (_) {
      throw QrCheckInException(
        code: 'MALFORMED_RESPONSE',
        message: 'Invalid response from attendance server.',
        statusCode: response.statusCode,
      );
    }

    if (response.statusCode >= 200 && response.statusCode < 300) {
      final data = decoded['data'] as Map<String, dynamic>? ?? {};
      return QrCheckInResult.fromJson(data);
    } else {
      final err = decoded['error'] as Map<String, dynamic>?;
      final code = err?['code'] as String? ?? 'CHECKIN_ERROR';
      final message =
          err?['message'] as String? ?? 'Attendance check-in rejected.';
      throw QrCheckInException(
        code: code,
        message: message,
        statusCode: response.statusCode,
      );
    }
  }

  void close() {
    _client.close(force: true);
  }
}
