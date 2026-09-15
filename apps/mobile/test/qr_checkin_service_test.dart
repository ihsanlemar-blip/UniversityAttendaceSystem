import 'package:flutter_test/flutter_test.dart';
import 'package:university_attendance_mobile/services/qr_checkin_service.dart';

void main() {
  group('QrCheckInResult Tests', () {
    test('Correctly deserializes successful verification response', () {
      final json = {
        'accepted': true,
        'checkpoint_type': 'START',
        'already_credited': false,
        'verified_at': '2026-09-14T10:00:05Z',
        'attendance_record_id': '0192323e-6708-724a-a43b-8106daee86fa',
      };

      final result = QrCheckInResult.fromJson(json);
      expect(result.accepted, isTrue);
      expect(result.checkpointType, equals('START'));
      expect(result.alreadyCredited, isFalse);
      expect(result.attendanceRecordId, equals('0192323e-6708-724a-a43b-8106daee86fa'));
      expect(result.verifiedAt.isUtc, isTrue);
    });

    test('Correctly deserializes idempotent duplicate response (INV-05)', () {
      final json = {
        'accepted': true,
        'checkpoint_type': 'MIDDLE',
        'already_credited': true,
        'verified_at': '2026-09-14T10:15:00Z',
        'attendance_record_id': '0192323e-6708-724a-a43b-8106daee86fa',
      };

      final result = QrCheckInResult.fromJson(json);
      expect(result.accepted, isTrue);
      expect(result.checkpointType, equals('MIDDLE'));
      expect(result.alreadyCredited, isTrue);
    });

    test('Handles missing fields gracefully with defaults', () {
      final json = <String, dynamic>{};
      final result = QrCheckInResult.fromJson(json);
      expect(result.accepted, isFalse);
      expect(result.checkpointType, equals('UNKNOWN'));
      expect(result.alreadyCredited, isFalse);
      expect(result.attendanceRecordId, isEmpty);
    });
  });

  group('QrCheckInException Tests', () {
    test('Formats string with code, message, and status code', () {
      const exc = QrCheckInException(
        code: 'QR_TOKEN_EXPIRED',
        message: 'Token has expired.',
        statusCode: 400,
      );
      expect(exc.toString(), contains('QR_TOKEN_EXPIRED'));
      expect(exc.toString(), contains('Token has expired.'));
      expect(exc.toString(), contains('400'));
    });
  });
}
