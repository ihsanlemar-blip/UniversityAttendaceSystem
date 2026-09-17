import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:university_attendance_mobile/core/api_client.dart';
import 'package:university_attendance_mobile/screens/student_home_screen.dart';

void main() {
  group('StudentHomeScreen Widget Tests', () {
    testWidgets('Renders N/A standing when student has zero eligible sessions',
        (WidgetTester tester) async {
      final mockClient = ApiClient(baseUrl: 'http://localhost:8000');

      await tester.pumpWidget(
        MaterialApp(
          home: StudentHomeScreen(
            apiClient: mockClient,
            studentName: 'Zalmay Khan',
            studentNumber: 'KBL-2024-CS-099',
            initialPercentage: null,
            initialStatus: 'NOT_APPLICABLE',
          ),
        ),
      );

      // Verify Student Profile
      expect(find.text('Zalmay Khan'), findsOneWidget);
      expect(find.text('Student ID: KBL-2024-CS-099'), findsOneWidget);

      // Verify Invariant: No evaluated sessions must display N/A, never 100% or 0%
      expect(find.text('N/A'), findsAtLeastNWidgets(1));
      expect(
          find.text('Not Applicable (No Eligible Sessions)'), findsOneWidget);
      expect(find.text('100%'), findsNothing);
      expect(find.text('100.0%'), findsNothing);

      // Verify Quick Action titles
      expect(find.text('Scan QR Check-In'), findsOneWidget);
      expect(find.text('Device Trust'), findsOneWidget);
      expect(find.text('Attendance Ledger'), findsOneWidget);
      expect(find.text('Offline Sync Queue'), findsOneWidget);

      // Verify Enrolled Courses Header
      expect(find.text('Enrolled Courses'), findsOneWidget);
    });

    testWidgets(
        'Renders percentage and Good Standing when eligible sessions exist',
        (WidgetTester tester) async {
      final mockClient = ApiClient(baseUrl: 'http://localhost:8000');

      await tester.pumpWidget(
        MaterialApp(
          home: StudentHomeScreen(
            apiClient: mockClient,
            studentName: 'Fatima Noori',
            studentNumber: 'KBL-2023-CS-015',
            initialPercentage: 88.5,
            initialStatus: 'GOOD_STANDING',
          ),
        ),
      );

      // Verify Student Profile
      expect(find.text('Fatima Noori'), findsOneWidget);

      // Verify Standing
      expect(find.text('88.5%'), findsOneWidget);
      expect(find.text('Good Standing (≥ 75%)'), findsOneWidget);

      // Verify 75% threshold notice
      expect(
        find.text('Minimum 75% required for final examination eligibility.'),
        findsOneWidget,
      );
    });
  });
}
