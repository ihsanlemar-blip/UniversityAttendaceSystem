import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:university_attendance_mobile/screens/student_attendance_history_screen.dart';
import 'package:university_attendance_mobile/services/attendance_operations_service.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  group('Attendance Operations DTO Models', () {
    test('CorrectionRequestModel correctly parses valid server payload', () {
      final json = {
        'id': '0192323e-6708-724a-a43b-8106daee8601',
        'attendance_record_id': '0192323e-6708-724a-a43b-8106daee8602',
        'attendance_session_id': '0192323e-6708-724a-a43b-8106daee8603',
        'student_id': '0192323e-6708-724a-a43b-8106daee8604',
        'request_type': 'TECHNICAL_ISSUE',
        'requested_status': 'PRESENT',
        'reason': 'Bluetooth radio scanner failed during session middle',
        'supporting_note': 'Lecturer witnessed physical presence in room 301',
        'status': 'PENDING',
        'created_at': '2026-09-16T12:00:00Z',
      };

      final model = CorrectionRequestModel.fromJson(json);
      expect(model.id, equals('0192323e-6708-724a-a43b-8106daee8601'));
      expect(model.requestType, equals('TECHNICAL_ISSUE'));
      expect(model.requestedStatus, equals('PRESENT'));
      expect(model.status, equals('PENDING'));
      expect(model.supportingNote, isNotNull);
      expect(model.createdAt.isUtc, isTrue);
    });

    test('ExcuseRequestModel correctly parses absence excuse payload', () {
      final json = {
        'id': '0192323e-6708-724a-a43b-8106daee8610',
        'student_id': '0192323e-6708-724a-a43b-8106daee8611',
        'attendance_session_id': '0192323e-6708-724a-a43b-8106daee8612',
        'category': 'MEDICAL',
        'description': 'Severe fever and doctor-prescribed bed rest',
        'document_reference': 'MED-CERT-2026-9921',
        'status': 'APPROVED',
        'review_note': 'Official clinic certificate verified',
        'reviewed_at_utc': '2026-09-16T14:30:00Z',
        'created_at': '2026-09-16T10:00:00Z',
      };

      final model = ExcuseRequestModel.fromJson(json);
      expect(model.id, equals('0192323e-6708-724a-a43b-8106daee8610'));
      expect(model.category, equals('MEDICAL'));
      expect(model.status, equals('APPROVED'));
      expect(model.documentReference, equals('MED-CERT-2026-9921'));
      expect(model.reviewNote, isNotNull);
    });

    test('LeaveRequestModel parses pre-class leave (Section 38: 0.00 credit)', () {
      final json = {
        'id': '0192323e-6708-724a-a43b-8106daee8620',
        'student_id': '0192323e-6708-724a-a43b-8106daee8621',
        'class_occurrence_id': '0192323e-6708-724a-a43b-8106daee8622',
        'reason': 'Attending national robotics tournament representing university',
        'status': 'PENDING',
        'created_at': '2026-09-16T08:00:00Z',
      };

      final model = LeaveRequestModel.fromJson(json);
      expect(model.id, equals('0192323e-6708-724a-a43b-8106daee8620'));
      expect(model.classOccurrenceId, equals('0192323e-6708-724a-a43b-8106daee8622'));
      expect(model.status, equals('PENDING'));
    });

    test('RecordEligibilityModel evaluates window and duplicate request flags', () {
      final eligibleJson = {
        'record_id': '0192323e-6708-724a-a43b-8106daee8630',
        'eligible_for_correction': true,
        'correction_ineligibility_reason': null,
        'correction_window_deadline_utc': '2026-09-17T18:00:00Z',
        'has_open_correction': false,
        'has_open_excuse': false,
        'current_status': 'ABSENT',
        'current_credit': 0.0,
      };

      final eligibleModel = RecordEligibilityModel.fromJson(eligibleJson);
      expect(eligibleModel.eligibleForCorrection, isTrue);
      expect(eligibleModel.correctionIneligibilityReason, isNull);
      expect(eligibleModel.correctionWindowDeadlineUtc, isNotNull);

      final ineligibleJson = {
        'record_id': '0192323e-6708-724a-a43b-8106daee8631',
        'eligible_for_correction': false,
        'correction_ineligibility_reason': 'Correction window expired at 2026-09-15T18:00:00 UTC.',
        'correction_window_deadline_utc': '2026-09-15T18:00:00Z',
        'has_open_correction': false,
        'has_open_excuse': false,
        'current_status': 'ABSENT',
        'current_credit': 0.0,
      };

      final ineligibleModel = RecordEligibilityModel.fromJson(ineligibleJson);
      expect(ineligibleModel.eligibleForCorrection, isFalse);
      expect(ineligibleModel.correctionIneligibilityReason, contains('expired'));
    });

    test('RecordTimelineModel parses revision history items correctly', () {
      final json = {
        'record_id': '0192323e-6708-724a-a43b-8106daee8640',
        'session_id': '0192323e-6708-724a-a43b-8106daee8641',
        'student_id': '0192323e-6708-724a-a43b-8106daee8642',
        'current_status': 'PRESENT',
        'current_credit': 1.0,
        'version_no': 2,
        'is_manual': true,
        'manual_reason': 'Correction approved by lecturer',
        'revisions': [
          {
            'id': '0192323e-6708-724a-a43b-8106daee8651',
            'event_type': 'CORRECTION_REQUESTED',
            'previous_status': 'ABSENT',
            'new_status': 'ABSENT',
            'previous_credit': 0.0,
            'new_credit': 0.0,
            'reason': 'Technical failure with QR code',
            'actor_user_id': '0192323e-6708-724a-a43b-8106daee8642',
            'occurred_at_utc': '2026-09-16T12:00:00Z',
          },
          {
            'id': '0192323e-6708-724a-a43b-8106daee8652',
            'event_type': 'CORRECTION_APPROVED',
            'previous_status': 'ABSENT',
            'new_status': 'PRESENT',
            'previous_credit': 0.0,
            'new_credit': 1.0,
            'reason': 'Correction approved by lecturer',
            'actor_user_id': '0192323e-6708-724a-a43b-8106daee8699',
            'occurred_at_utc': '2026-09-16T15:00:00Z',
          }
        ],
      };

      final timeline = RecordTimelineModel.fromJson(json);
      expect(timeline.recordId, equals('0192323e-6708-724a-a43b-8106daee8640'));
      expect(timeline.versionNo, equals(2));
      expect(timeline.isManual, isTrue);
      expect(timeline.revisions.length, equals(2));
      expect(timeline.revisions[1].eventType, equals('CORRECTION_APPROVED'));
      expect(timeline.revisions[1].previousStatus, equals('ABSENT'));
      expect(timeline.revisions[1].newStatus, equals('PRESENT'));
      expect(timeline.revisions[1].newCredit, equals(1.0));
    });

    test('Offline error message instructs student to connect to university system', () {
      const ex = AttendanceOperationsException(
        message: 'Connect to the university system to submit this request. Offline submission is not supported for operations.',
        code: 'OFFLINE_MODE',
      );
      expect(ex.code, equals('OFFLINE_MODE'));
      expect(ex.message, contains('Connect to the university system'));
    });
  });

  group('StudentAttendanceHistoryScreen Widget Tests', () {
    testWidgets('Renders tab bar and class session cards with correction buttons',
        (WidgetTester tester) async {
      final service = AttendanceOperationsService(baseUrl: 'http://localhost:8000');

      await tester.pumpWidget(
        MaterialApp(
          home: StudentAttendanceHistoryScreen(
            operationsService: service,
            authToken: 'test_token',
            studentId: 'test_student_id',
          ),
        ),
      );

      // Wait for async init / animations
      await tester.pumpAndSettle();

      // Check title and tabs
      expect(find.text('Attendance History & Requests'), findsOneWidget);
      expect(find.text('Attendance Records'), findsOneWidget);
      expect(find.text('My Requests'), findsOneWidget);

      // Check course cards
      expect(find.text('CS301'), findsOneWidget);
      expect(find.text('Operating Systems'), findsOneWidget);
      expect(find.text('CS302'), findsOneWidget);
      expect(find.text('CS303'), findsOneWidget);

      // Check action buttons on cards
      expect(find.text('Correction'), findsNWidgets(3));
      expect(find.text('Excuse'), findsNWidgets(3));
      expect(find.text('Leave'), findsNWidgets(3));

      // Tap on Correction button of the first card to open modal sheet
      await tester.tap(find.text('Correction').first);
      await tester.pumpAndSettle();

      // Check modal bottom sheet appeared
      expect(find.text('Request Attendance Correction'), findsOneWidget);
      expect(find.text('Correction Type'), findsOneWidget);
      expect(find.text('Requested Status'), findsOneWidget);
      expect(find.text('Submit Correction Request'), findsOneWidget);

      // Close modal
      await tester.tap(find.byIcon(Icons.close));
      await tester.pumpAndSettle();

      expect(find.text('Request Attendance Correction'), findsNothing);
    });

    testWidgets('Tapping Pre-Class Leave button displays Section 38 0-credit policy notice',
        (WidgetTester tester) async {
      final service = AttendanceOperationsService(baseUrl: 'http://localhost:8000');

      await tester.pumpWidget(
        MaterialApp(
          home: StudentAttendanceHistoryScreen(
            operationsService: service,
            authToken: 'test_token',
            studentId: 'test_student_id',
          ),
        ),
      );

      await tester.pumpAndSettle();

      // Tap on Leave button of first card
      await tester.tap(find.text('Leave').first);
      await tester.pumpAndSettle();

      // Check Section 38 policy notice is displayed
      expect(find.text('Submit Pre-Class Leave Request'), findsOneWidget);
      expect(find.textContaining('Section 38'), findsOneWidget);
      expect(find.textContaining('0.00 credit'), findsOneWidget);
      expect(find.text('Submit Leave Request'), findsOneWidget);
    });
  });
}
