import 'dart:convert';
import 'package:crypto/crypto.dart' as crypto;
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:university_attendance_mobile/services/device_key_service.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() {
    FlutterSecureStorage.setMockInitialValues({});
  });

  group('DeviceKeyService Cryptographic Identity Tests', () {
    test('Generates Ed25519 keypair and persists in secure storage', () async {
      final service = DeviceKeyService();
      await service.ensureKeyPair();

      final keyPair = await service.getKeyPair();
      expect(keyPair, isNotNull);

      final pubBytes = await service.getPublicKeyBytes();
      expect(pubBytes, isNotNull);
      expect(pubBytes!.length, equals(32));

      final pem = await service.getPublicKeyPem();
      expect(pem, isNotNull);
      expect(pem!, startsWith('-----BEGIN PUBLIC KEY-----'));
      expect(pem, endsWith('-----END PUBLIC KEY-----'));

      final fp = await service.getPublicKeyFingerprint();
      expect(fp, isNotNull);
      expect(fp!.length, equals(64)); // 32-byte SHA-256 hex string

      // Verify fingerprint matches SHA-256 of raw public bytes
      final expectedFp =
          crypto.sha256.convert(pubBytes).toString().toLowerCase();
      expect(fp, equals(expectedFp));

      final shortFp = await service.getShortFingerprint();
      expect(shortFp, isNotNull);
      expect(shortFp!.length, equals(15)); // 6 + 3 (...) + 6 = 15 chars
      expect(shortFp, contains('...'));
    });

    test('Ensuring keypair does not overwrite existing key', () async {
      final service = DeviceKeyService();
      await service.ensureKeyPair();
      final fp1 = await service.getPublicKeyFingerprint();

      await service.ensureKeyPair();
      final fp2 = await service.getPublicKeyFingerprint();

      expect(fp1, equals(fp2));
    });

    test('Signs registration challenge deterministically with Ed25519',
        () async {
      final service = DeviceKeyService();
      await service.ensureKeyPair();
      final fp = (await service.getPublicKeyFingerprint())!;

      final sig = await service.signRegistrationChallenge(
        challengeId: '0192323e-6708-724a-a43b-8106daee86fa',
        universityId: '0192323e-6708-724a-a43b-8106daee86fb',
        userId: '0192323e-6708-724a-a43b-8106daee86fc',
        candidateFingerprint: fp,
        nonce: 'test_random_nonce_12345',
        issuedAtUtcIso: '2026-09-14T10:00:00Z',
        expiresAtUtcIso: '2026-09-14T10:05:00Z',
      );

      expect(sig, isNotEmpty);
      final sigBytes = base64Decode(sig);
      expect(sigBytes.length, equals(64)); // Ed25519 signature is 64 bytes
    });

    test('Signs online presence check-in payload', () async {
      final service = DeviceKeyService();
      await service.ensureKeyPair();

      final sig = await service.signOnlinePresenceCheckIn(
        userId: '0192323e-6708-724a-a43b-8106daee86fa',
        universityId: '0192323e-6708-724a-a43b-8106daee86fb',
        deviceId: '0192323e-6708-724a-a43b-8106daee86fc',
        proofId: 'proof_123456789',
        qrToken: 'dyn_qr_token_abc123',
        blePayload: 'ble_payload_hex_456',
      );

      expect(sig, isNotEmpty);
      final sigBytes = base64Decode(sig);
      expect(sigBytes.length, equals(64));
    });

    test('Signs offline attendance claim payload', () async {
      final service = DeviceKeyService();
      await service.ensureKeyPair();

      final sig = await service.signOfflineAttendanceClaim(
        userId: '0192323e-6708-724a-a43b-8106daee86fa',
        universityId: '0192323e-6708-724a-a43b-8106daee86fb',
        deviceId: '0192323e-6708-724a-a43b-8106daee86fc',
        claimId: 'claim_987654321',
        permitId: '0192323e-6708-724a-a43b-8106daee86fd',
        authorityEpoch: 1,
        hostSessionId: '0192323e-6708-724a-a43b-8106daee86fe',
        checkpointType: 'START',
        qrChallengeToken: 'offline_qr_challenge_token',
      );

      expect(sig, isNotEmpty);
      final sigBytes = base64Decode(sig);
      expect(sigBytes.length, equals(64));
    });

    test('Signs campus network presence challenge payload', () async {
      final service = DeviceKeyService();
      await service.ensureKeyPair();

      final sig = await service.signNetworkPresenceChallenge(
        challengeId: '0192323e-6708-724a-a43b-8106daee86fa',
        nonce: 'nonce_hex_value_1234567890abcdef',
        userId: '0192323e-6708-724a-a43b-8106daee86fb',
        universityId: '0192323e-6708-724a-a43b-8106daee86fc',
        deviceId: '0192323e-6708-724a-a43b-8106daee86fd',
        sessionId: '0192323e-6708-724a-a43b-8106daee86fe',
        checkpointId: '0192323e-6708-724a-a43b-8106daee86ff',
        networkZoneId: '0192323e-6708-724a-a43b-8106daee8600',
        issuedIso: '2026-09-15T10:00:00.000000Z',
        expiresIso: '2026-09-15T10:00:20.000000Z',
      );

      expect(sig, isNotEmpty);
      final sigBytes = base64Decode(sig);
      expect(sigBytes.length, equals(64));
    });

    test('Device status and metadata persistence lifecycle', () async {
      final service = DeviceKeyService();
      expect(await service.getDeviceStatus(), equals('UNREGISTERED'));
      expect(await service.getDeviceId(), isNull);

      await service.setDeviceId('0192323e-6708-724a-a43b-8106daee86fa');
      await service.setDeviceStatus('ACTIVE');
      await service.setRegistrationDate('2026-09-14T10:00:00Z');

      expect(await service.getDeviceId(),
          equals('0192323e-6708-724a-a43b-8106daee86fa'));
      expect(await service.getDeviceStatus(), equals('ACTIVE'));
      expect(
          await service.getRegistrationDate(), equals('2026-09-14T10:00:00Z'));

      await service.clearAll();
      expect(await service.getDeviceStatus(), equals('UNREGISTERED'));
      expect(await service.getDeviceId(), isNull);
    });
  });
}
