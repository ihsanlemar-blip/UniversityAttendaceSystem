import 'dart:convert';
import 'package:crypto/crypto.dart' as crypto;
import 'package:cryptography/cryptography.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

/// Secure storage keys for Milestone 13 device trust
abstract class DeviceStorageKeys {
  static const String privateKeySeed = 'dsas_device_private_key_seed';
  static const String publicKeyRaw = 'dsas_device_public_key_raw';
  static const String deviceId = 'dsas_device_registered_id';
  static const String deviceStatus = 'dsas_device_status';
  static const String registrationDate = 'dsas_device_registered_at';
}

/// Service managing device cryptographic identity (Ed25519) in OS-level secure storage.
///
/// Directives Enforced:
/// - Private key is generated on-device and stored in OS secure keystore.
/// - Private key NEVER leaves the device (never transmitted or logged).
/// - Asymmetric Ed25519 proof of possession for registration challenges and attendance.
/// - Canonical payload serialization matching backend specification.
class DeviceKeyService {
  final FlutterSecureStorage _storage;
  final Ed25519 _algorithm;

  DeviceKeyService({
    FlutterSecureStorage? storage,
    Ed25519? algorithm,
  })  : _storage = storage ??
            const FlutterSecureStorage(
              aOptions: AndroidOptions(encryptedSharedPreferences: true),
              iOptions:
                  IOSOptions(accessibility: KeychainAccessibility.first_unlock),
            ),
        _algorithm = algorithm ?? Ed25519();

  /// Ensure a local device keypair exists; generates one if missing.
  Future<void> ensureKeyPair() async {
    final existingSeed =
        await _storage.read(key: DeviceStorageKeys.privateKeySeed);
    if (existingSeed == null || existingSeed.isEmpty) {
      await generateNewKeyPair();
    }
  }

  /// Generate a new Ed25519 keypair and persist private seed & public key to secure storage.
  Future<SimpleKeyPair> generateNewKeyPair() async {
    final keyPair = await _algorithm.newKeyPair();
    final privBytes = await keyPair.extractPrivateKeyBytes();
    final pubKey = await keyPair.extractPublicKey();

    final seedHex = _bytesToHex(privBytes);
    final pubHex = _bytesToHex(pubKey.bytes);

    await _storage.write(key: DeviceStorageKeys.privateKeySeed, value: seedHex);
    await _storage.write(key: DeviceStorageKeys.publicKeyRaw, value: pubHex);

    return keyPair;
  }

  /// Get the current keypair from secure storage.
  Future<SimpleKeyPair?> getKeyPair() async {
    final seedHex = await _storage.read(key: DeviceStorageKeys.privateKeySeed);
    if (seedHex == null || seedHex.isEmpty) {
      return null;
    }
    final seedBytes = _hexToBytes(seedHex);
    return _algorithm.newKeyPairFromSeed(seedBytes);
  }

  /// Get public key raw 32 bytes.
  Future<List<int>?> getPublicKeyBytes() async {
    final pubHex = await _storage.read(key: DeviceStorageKeys.publicKeyRaw);
    if (pubHex == null || pubHex.isEmpty) {
      return null;
    }
    return _hexToBytes(pubHex);
  }

  /// Get standard PKIX SubjectPublicKeyInfo PEM string.
  Future<String?> getPublicKeyPem() async {
    final rawBytes = await getPublicKeyBytes();
    if (rawBytes == null) {
      return null;
    }
    // 12-byte standard Ed25519 ASN.1 SPKI header
    final derHeader = [
      0x30,
      0x2a,
      0x30,
      0x05,
      0x06,
      0x03,
      0x2b,
      0x65,
      0x70,
      0x03,
      0x21,
      0x00,
    ];
    final fullDer = [...derHeader, ...rawBytes];
    final b64 = base64Encode(fullDer);
    return '-----BEGIN PUBLIC KEY-----\n$b64\n-----END PUBLIC KEY-----';
  }

  /// Get canonical SHA-256 fingerprint over raw 32-byte public key (64 hex characters, lowercase).
  Future<String?> getPublicKeyFingerprint() async {
    final rawBytes = await getPublicKeyBytes();
    if (rawBytes == null) {
      return null;
    }
    final digest = crypto.sha256.convert(rawBytes);
    return digest.toString().toLowerCase();
  }

  /// Get short human-readable fingerprint: first 6 and last 6 hex chars uppercase (e.g. A1B2C3...D4E5F6).
  Future<String?> getShortFingerprint() async {
    final fp = await getPublicKeyFingerprint();
    if (fp == null || fp.length < 12) {
      return null;
    }
    return '${fp.substring(0, 6)}...${fp.substring(fp.length - 6)}'
        .toUpperCase();
  }

  /// Get registered device UUID string (if registered with server).
  Future<String?> getDeviceId() async {
    return _storage.read(key: DeviceStorageKeys.deviceId);
  }

  /// Store server-assigned device UUID upon successful activation.
  Future<void> setDeviceId(String deviceId) async {
    await _storage.write(key: DeviceStorageKeys.deviceId, value: deviceId);
  }

  /// Get current cached device status.
  Future<String> getDeviceStatus() async {
    final status = await _storage.read(key: DeviceStorageKeys.deviceStatus);
    return status ?? 'UNREGISTERED';
  }

  /// Store device status (e.g. ACTIVE, SUSPENDED, REVOKED).
  Future<void> setDeviceStatus(String status) async {
    await _storage.write(key: DeviceStorageKeys.deviceStatus, value: status);
  }

  /// Store activation timestamp.
  Future<void> setRegistrationDate(String isoString) async {
    await _storage.write(
        key: DeviceStorageKeys.registrationDate, value: isoString);
  }

  /// Get activation timestamp.
  Future<String?> getRegistrationDate() async {
    return _storage.read(key: DeviceStorageKeys.registrationDate);
  }

  // ===========================================================================
  // Cryptographic Signing Methods
  // ===========================================================================

  /// Sign registration challenge response with the local private key.
  ///
  /// Format:
  /// DEVICE_REGISTRATION_V1|{challengeId}|{universityId}|{userId}|{fingerprint.toLowerCase()}|{nonce}|{issuedAt}|{expiresAt}
  Future<String> signRegistrationChallenge({
    required String challengeId,
    required String universityId,
    required String userId,
    required String candidateFingerprint,
    required String nonce,
    required String issuedAtUtcIso,
    required String expiresAtUtcIso,
  }) async {
    final keyPair = await getKeyPair();
    if (keyPair == null) {
      throw StateError('No local device keypair available for signing.');
    }

    final canonicalString =
        'DEVICE_REGISTRATION_V1|$challengeId|$universityId|$userId|'
        '${candidateFingerprint.toLowerCase()}|$nonce|$issuedAtUtcIso|$expiresAtUtcIso';

    final sig = await _algorithm.sign(
      utf8.encode(canonicalString),
      keyPair: keyPair,
    );

    return base64Encode(sig.bytes);
  }

  /// Sign online attendance presence check-in payload.
  ///
  /// Format:
  /// DEVICE_PROOF_V1|ONLINE_PRESENCE_CHECKIN|{userId}|{universityId}|{deviceId}|{proofId}|{qrDigest}|{bleDigest}
  Future<String> signOnlinePresenceCheckIn({
    required String userId,
    required String universityId,
    required String deviceId,
    required String proofId,
    String? qrToken,
    String? blePayload,
  }) async {
    final keyPair = await getKeyPair();
    if (keyPair == null) {
      throw StateError(
          'No local device keypair available for signing attendance proof.');
    }

    var qrDigest = '';
    if (qrToken != null && qrToken.trim().isNotEmpty) {
      qrDigest = crypto.sha256.convert(utf8.encode(qrToken.trim())).toString();
    }

    var bleDigest = '';
    if (blePayload != null && blePayload.trim().isNotEmpty) {
      bleDigest =
          crypto.sha256.convert(utf8.encode(blePayload.trim())).toString();
    }

    final canonicalString =
        'DEVICE_PROOF_V1|ONLINE_PRESENCE_CHECKIN|$userId|$universityId|$deviceId|$proofId|$qrDigest|$bleDigest';

    final sig = await _algorithm.sign(
      utf8.encode(canonicalString),
      keyPair: keyPair,
    );

    return base64Encode(sig.bytes);
  }

  /// Sign offline student attendance claim.
  ///
  /// Format:
  /// DEVICE_PROOF_V1|OFFLINE_ATTENDANCE_CLAIM|{userId}|{universityId}|{deviceId}|{claimId}|{permitId}|{authorityEpoch}|{hostSessionId ?? ""}|{checkpointType.toUpperCase()}|{qrDigest}|{bleDigest}
  Future<String> signOfflineAttendanceClaim({
    required String userId,
    required String universityId,
    required String deviceId,
    required String claimId,
    required String permitId,
    required int authorityEpoch,
    String? hostSessionId,
    required String checkpointType,
    required String qrChallengeToken,
    String? blePayload,
  }) async {
    final keyPair = await getKeyPair();
    if (keyPair == null) {
      throw StateError(
          'No local device keypair available for signing offline claim.');
    }

    final qrDigest =
        crypto.sha256.convert(utf8.encode(qrChallengeToken.trim())).toString();
    var bleDigest = '';
    if (blePayload != null && blePayload.trim().isNotEmpty) {
      bleDigest =
          crypto.sha256.convert(utf8.encode(blePayload.trim())).toString();
    }

    final hostStr = hostSessionId ?? '';
    final canonicalString =
        'DEVICE_PROOF_V1|OFFLINE_ATTENDANCE_CLAIM|$userId|$universityId|$deviceId|$claimId|$permitId|'
        '$authorityEpoch|$hostStr|${checkpointType.toUpperCase()}|$qrDigest|$bleDigest';

    final sig = await _algorithm.sign(
      utf8.encode(canonicalString),
      keyPair: keyPair,
    );

    return base64Encode(sig.bytes);
  }

  /// Reset all stored keys and device metadata.
  Future<void> clearAll() async {
    await _storage.delete(key: DeviceStorageKeys.privateKeySeed);
    await _storage.delete(key: DeviceStorageKeys.publicKeyRaw);
    await _storage.delete(key: DeviceStorageKeys.deviceId);
    await _storage.delete(key: DeviceStorageKeys.deviceStatus);
    await _storage.delete(key: DeviceStorageKeys.registrationDate);
  }

  // ===========================================================================
  // Internal Helpers
  // ===========================================================================

  static String _bytesToHex(List<int> bytes) {
    final buffer = StringBuffer();
    for (final b in bytes) {
      buffer.write(b.toRadixString(16).padLeft(2, '0'));
    }
    return buffer.toString();
  }

  static List<int> _hexToBytes(String hex) {
    final clean = hex.trim();
    final result = <int>[];
    for (var i = 0; i < clean.length; i += 2) {
      result.add(int.parse(clean.substring(i, i + 2), radix: 16));
    }
    return result;
  }
}
