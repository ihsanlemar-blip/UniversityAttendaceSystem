import 'package:flutter_test/flutter_test.dart';
import 'package:university_attendance_mobile/services/presence_checkin_service.dart';

void main() {
  group('PresenceCheckInResult Tests', () {
    test('Correctly deserializes dual-factor response', () {
      final json = {
        'accepted': true,
        'checkpoint_type': 'START',
        'already_credited': false,
        'verified_at': '2026-09-15T10:00:05Z',
        'attendance_record_id': '0192323e-6708-724a-a43b-8106daee86fa',
        'verified_factors': ['ONLINE_DYNAMIC_QR', 'BLUETOOTH_BLE'],
        'presence_mode': 'QR_AND_BLE',
      };

      final result = PresenceCheckInResult.fromJson(json);
      expect(result.accepted, isTrue);
      expect(result.checkpointType, equals('START'));
      expect(result.alreadyCredited, isFalse);
      expect(result.attendanceRecordId,
          equals('0192323e-6708-724a-a43b-8106daee86fa'));
      expect(result.verifiedFactors,
          containsAll(['ONLINE_DYNAMIC_QR', 'BLUETOOTH_BLE']));
      expect(result.presenceMode, equals('QR_AND_BLE'));
    });

    test('Correctly deserializes idempotent duplicate response (INV-05)', () {
      final json = {
        'accepted': true,
        'checkpoint_type': 'MIDDLE',
        'already_credited': true,
        'verified_at': '2026-09-15T10:15:00Z',
        'attendance_record_id': '0192323e-6708-724a-a43b-8106daee86fa',
        'verified_factors': ['ONLINE_DYNAMIC_QR'],
        'presence_mode': 'QR_ONLY',
      };

      final result = PresenceCheckInResult.fromJson(json);
      expect(result.accepted, isTrue);
      expect(result.checkpointType, equals('MIDDLE'));
      expect(result.alreadyCredited, isTrue);
      expect(result.presenceMode, equals('QR_ONLY'));
    });

    test('Handles missing fields gracefully with defaults', () {
      final json = <String, dynamic>{};
      final result = PresenceCheckInResult.fromJson(json);
      expect(result.accepted, isFalse);
      expect(result.checkpointType, equals('UNKNOWN'));
      expect(result.alreadyCredited, isFalse);
      expect(result.attendanceRecordId, isEmpty);
      expect(result.verifiedFactors, isEmpty);
      expect(result.presenceMode, equals('QR_ONLY'));
    });
  });

  group('PresenceCheckInException Tests', () {
    test('Formats string with code, message, and status code', () {
      const exc = PresenceCheckInException(
        code: 'PRESENCE_FACTORS_INCOMPLETE',
        message: 'BLE observation required.',
        statusCode: 400,
      );
      expect(exc.toString(), contains('PRESENCE_FACTORS_INCOMPLETE'));
      expect(exc.toString(), contains('BLE observation required.'));
      expect(exc.toString(), contains('400'));
    });
  });
}
