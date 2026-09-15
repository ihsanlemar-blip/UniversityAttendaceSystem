import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:university_attendance_mobile/screens/student_qr_scanner_screen.dart';
import 'package:university_attendance_mobile/services/qr_checkin_service.dart';

void main() {
  testWidgets('StudentQrScannerScreen renders viewfinder and instructions', (tester) async {
    final service = QrCheckInService(baseUrl: 'http://localhost:8000');

    await tester.pumpWidget(
      MaterialApp(
        home: StudentQrScannerScreen(
          checkInService: service,
          authToken: 'mock-test-auth-token',
        ),
      ),
    );

    // Verify title and viewfinder elements
    expect(find.text('Attendance Check-In'), findsOneWidget);
    expect(
      find.text('Align the rotating QR code on the classroom projector screen inside the frame.'),
      findsOneWidget,
    );
    expect(find.text('Camera Active'), findsOneWidget);
    expect(find.byType(TextField), findsOneWidget);
  });
}
