import 'dart:convert';
import 'dart:io';

/// Server-issued BLE advertisement payload for classroom broadcasting.
class LecturerBlePayload {
  final String serviceUuid;
  final String payloadBase64;
  final String payloadHex;
  final int protocolVersion;
  final int rotationSeconds;
  final DateTime issuedAt;
  final DateTime expiresAt;
  final String checkpointId;
  final String checkpointType;
  final DateTime serverTime;
  final int refreshAfterSeconds;

  const LecturerBlePayload({
    required this.serviceUuid,
    required this.payloadBase64,
    required this.payloadHex,
    required this.protocolVersion,
    required this.rotationSeconds,
    required this.issuedAt,
    required this.expiresAt,
    required this.checkpointId,
    required this.checkpointType,
    required this.serverTime,
    required this.refreshAfterSeconds,
  });

  factory LecturerBlePayload.fromJson(Map<String, dynamic> json) {
    return LecturerBlePayload(
      serviceUuid: json['service_uuid'] as String? ?? '',
      payloadBase64: json['payload_base64'] as String? ?? '',
      payloadHex: json['payload_hex'] as String? ?? '',
      protocolVersion: json['protocol_version'] as int? ?? 1,
      rotationSeconds: json['rotation_seconds'] as int? ?? 20,
      issuedAt: json['issued_at'] != null
          ? DateTime.parse(json['issued_at'] as String)
          : DateTime.now().toUtc(),
      expiresAt: json['expires_at'] != null
          ? DateTime.parse(json['expires_at'] as String)
          : DateTime.now().toUtc().add(const Duration(seconds: 20)),
      checkpointId: json['checkpoint_id'] as String? ?? '',
      checkpointType: json['checkpoint_type'] as String? ?? '',
      serverTime: json['server_time'] != null
          ? DateTime.parse(json['server_time'] as String)
          : DateTime.now().toUtc(),
      refreshAfterSeconds: json['refresh_after_seconds'] as int? ?? 20,
    );
  }
}

class LecturerBleException implements Exception {
  final String code;
  final String message;
  final int statusCode;

  const LecturerBleException({
    required this.code,
    required this.message,
    required this.statusCode,
  });

  @override
  String toString() =>
      'LecturerBleException($code: $message [HTTP $statusCode])';
}

/// Service for authorized lecturers to fetch live rotating classroom BLE presence payloads.
class LecturerBleService {
  final String baseUrl;
  final HttpClient _client;

  LecturerBleService({
    String? baseUrl,
    HttpClient? client,
  })  : baseUrl = baseUrl ?? 'http://10.0.2.2:8000',
        _client = client ?? HttpClient();

  /// Fetch active BLE advertisement payload for checkpoint.
  /// Enforces lecturer authorization and active session/open checkpoint status.
  Future<LecturerBlePayload> fetchBleAdvertisement({
    required String checkpointId,
    required String authToken,
  }) async {
    final uri = Uri.parse(
      '$baseUrl/api/v1/attendance/checkpoints/$checkpointId/ble-advertisement',
    );
    final request = await _client.getUrl(uri);

    request.headers.set(HttpHeaders.acceptHeader, 'application/json');
    request.headers.set(HttpHeaders.authorizationHeader, 'Bearer $authToken');

    final response = await request.close();
    final responseBody = await response.transform(utf8.decoder).join();

    Map<String, dynamic> decoded;
    try {
      decoded = jsonDecode(responseBody) as Map<String, dynamic>;
    } catch (_) {
      throw LecturerBleException(
        code: 'MALFORMED_RESPONSE',
        message: 'Invalid response from attendance server.',
        statusCode: response.statusCode,
      );
    }

    if (response.statusCode >= 200 && response.statusCode < 300) {
      final data = decoded['data'] as Map<String, dynamic>? ?? {};
      return LecturerBlePayload.fromJson(data);
    } else {
      final err = decoded['error'] as Map<String, dynamic>?;
      final code = err?['code'] as String? ?? 'BLE_FETCH_ERROR';
      final message =
          err?['message'] as String? ?? 'Failed to fetch BLE advertisement.';
      throw LecturerBleException(
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
