import 'dart:convert';
import 'dart:io';
import 'device_key_service.dart';

/// DTO for network challenge issued by server.
class NetworkChallengeDto {
  final String challengeId;
  final String nonce;
  final DateTime issuedAt;
  final DateTime expiresAt;
  final String sessionId;
  final String checkpointId;
  final String networkZoneId;
  final String networkZoneName;
  final String clientIp;

  const NetworkChallengeDto({
    required this.challengeId,
    required this.nonce,
    required this.issuedAt,
    required this.expiresAt,
    required this.sessionId,
    required this.checkpointId,
    required this.networkZoneId,
    required this.networkZoneName,
    required this.clientIp,
  });

  factory NetworkChallengeDto.fromJson(Map<String, dynamic> json) {
    return NetworkChallengeDto(
      challengeId: json['challenge_id'] as String,
      nonce: json['nonce'] as String,
      issuedAt: DateTime.parse(json['issued_at'] as String),
      expiresAt: DateTime.parse(json['expires_at'] as String),
      sessionId: json['session_id'] as String,
      checkpointId: json['checkpoint_id'] as String,
      networkZoneId: json['network_zone_id'] as String,
      networkZoneName: json['network_zone_name'] as String? ?? '',
      clientIp: json['client_ip'] as String? ?? '',
    );
  }
}

/// Service handling campus network presence challenges and proof construction.
class CampusNetworkService {
  final String baseUrl;
  final HttpClient _client;
  final DeviceKeyService _keyService;

  CampusNetworkService({
    String? baseUrl,
    HttpClient? client,
    DeviceKeyService? keyService,
  })  : baseUrl = baseUrl ?? 'http://10.0.2.2:8000',
        _client = client ?? HttpClient(),
        _keyService = keyService ?? DeviceKeyService();

  /// Request a short-lived (20s TTL) network challenge from the backend.
  Future<NetworkChallengeDto?> requestChallenge({
    required String checkpointId,
    required String authToken,
  }) async {
    final uri = Uri.parse('$baseUrl/api/v1/security/network-challenges');
    try {
      final request = await _client.postUrl(uri);
      request.headers.set(HttpHeaders.contentTypeHeader, 'application/json');
      request.headers.set(HttpHeaders.acceptHeader, 'application/json');
      request.headers.set(HttpHeaders.authorizationHeader, 'Bearer $authToken');

      request.write(jsonEncode({'checkpoint_id': checkpointId}));
      final response = await request.close();
      final body = await response.transform(utf8.decoder).join();

      if (response.statusCode >= 200 && response.statusCode < 300) {
        final decoded = jsonDecode(body) as Map<String, dynamic>;
        final data = decoded['data'] as Map<String, dynamic>;
        return NetworkChallengeDto.fromJson(data);
      }
      return null;
    } catch (_) {
      return null;
    }
  }

  /// Request challenge and sign network presence proof with registered device key.
  Future<Map<String, dynamic>?> obtainNetworkProof({
    required String checkpointId,
    required String authToken,
    required String userId,
    required String universityId,
  }) async {
    final devId = await _keyService.getDeviceId();
    if (devId == null) return null;

    final challenge = await requestChallenge(
      checkpointId: checkpointId,
      authToken: authToken,
    );
    if (challenge == null) return null;

    final proofId = 'proof_${DateTime.now().millisecondsSinceEpoch}';
    final sig = await _keyService.signNetworkPresenceChallenge(
      challengeId: challenge.challengeId,
      nonce: challenge.nonce,
      userId: userId,
      universityId: universityId,
      deviceId: devId,
      sessionId: challenge.sessionId,
      checkpointId: challenge.checkpointId,
      networkZoneId: challenge.networkZoneId,
      issuedIso: challenge.issuedAt.toUtc().toIso8601String(),
      expiresIso: challenge.expiresAt.toUtc().toIso8601String(),
    );

    return {
      'version': 'NETWORK_PRESENCE_V1',
      'challenge_id': challenge.challengeId,
      'trusted_device_id': devId,
      'proof_id': proofId,
      'signature': sig,
    };
  }
}
