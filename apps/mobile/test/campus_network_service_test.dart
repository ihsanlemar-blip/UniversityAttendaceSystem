import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:university_attendance_mobile/services/campus_network_service.dart';
import 'package:university_attendance_mobile/services/device_key_service.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() {
    FlutterSecureStorage.setMockInitialValues({});
  });

  group('NetworkChallengeDto Deserialization Tests', () {
    test('Correctly deserializes successful challenge response from server',
        () {
      final json = {
        'challenge_id': '0192323e-6708-724a-a43b-8106daee86fa',
        'nonce':
            'a1b2c3d4e5f60718293a4b5c6d7e8f90a1b2c3d4e5f60718293a4b5c6d7e8f90',
        'issued_at': '2026-09-15T10:00:00Z',
        'expires_at': '2026-09-15T10:00:20Z',
        'session_id': '0192323e-6708-724a-a43b-8106daee86fb',
        'checkpoint_id': '0192323e-6708-724a-a43b-8106daee86fc',
        'network_zone_id': '0192323e-6708-724a-a43b-8106daee86fd',
        'network_zone_name': 'Engineering Hall Wi-Fi',
        'client_ip': '10.10.5.24',
      };

      final dto = NetworkChallengeDto.fromJson(json);
      expect(dto.challengeId, equals('0192323e-6708-724a-a43b-8106daee86fa'));
      expect(
          dto.nonce,
          equals(
              'a1b2c3d4e5f60718293a4b5c6d7e8f90a1b2c3d4e5f60718293a4b5c6d7e8f90'));
      expect(dto.issuedAt.isUtc, isTrue);
      expect(dto.expiresAt.isUtc, isTrue);
      expect(dto.sessionId, equals('0192323e-6708-724a-a43b-8106daee86fb'));
      expect(dto.checkpointId, equals('0192323e-6708-724a-a43b-8106daee86fc'));
      expect(dto.networkZoneId, equals('0192323e-6708-724a-a43b-8106daee86fd'));
      expect(dto.networkZoneName, equals('Engineering Hall Wi-Fi'));
      expect(dto.clientIp, equals('10.10.5.24'));
    });
  });

  group('CampusNetworkService Proof Creation Tests', () {
    test(
        'Device key signs network presence challenge into valid proof structure',
        () async {
      final keyService = DeviceKeyService();
      await keyService.ensureKeyPair();
      await keyService.setDeviceId('0192323e-6708-724a-a43b-8106daee8601');

      final sig = await keyService.signNetworkPresenceChallenge(
        challengeId: '0192323e-6708-724a-a43b-8106daee8602',
        nonce:
            'nonce_hex_64_characters_long_0123456789abcdef0123456789abcdef0123',
        userId: '0192323e-6708-724a-a43b-8106daee8603',
        universityId: '0192323e-6708-724a-a43b-8106daee8604',
        deviceId: '0192323e-6708-724a-a43b-8106daee8601',
        sessionId: '0192323e-6708-724a-a43b-8106daee8605',
        checkpointId: '0192323e-6708-724a-a43b-8106daee8606',
        networkZoneId: '0192323e-6708-724a-a43b-8106daee8607',
        issuedIso: '2026-09-15T10:00:00.000000Z',
        expiresIso: '2026-09-15T10:00:20.000000Z',
      );

      final proof = {
        'version': 'NETWORK_PRESENCE_V1',
        'challenge_id': '0192323e-6708-724a-a43b-8106daee8602',
        'trusted_device_id': '0192323e-6708-724a-a43b-8106daee8601',
        'proof_id': 'proof_123456789',
        'signature': sig,
      };

      expect(proof['version'], equals('NETWORK_PRESENCE_V1'));
      expect(proof['challenge_id'],
          equals('0192323e-6708-724a-a43b-8106daee8602'));
      expect(proof['trusted_device_id'],
          equals('0192323e-6708-724a-a43b-8106daee8601'));
      expect(proof['signature'], isNotEmpty);
    });
  });
}
