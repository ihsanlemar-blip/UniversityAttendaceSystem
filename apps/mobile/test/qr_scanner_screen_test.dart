import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mobile_scanner/mobile_scanner.dart';
import 'package:university_attendance_mobile/screens/student_qr_scanner_screen.dart';
import 'package:university_attendance_mobile/services/qr_checkin_service.dart';

void main() {
  testWidgets('StudentQrScannerScreen renders MobileScanner camera preview and instructions', (tester) async {
    final service = QrCheckInService(baseUrl: 'http://localhost:8000');

    await tester.pumpWidget(
      MaterialApp(
        home: StudentQrScannerScreen(
          checkInService: service,
          authToken: 'mock-test-auth-token',
        ),
      ),
    );

    // Verify title, instructions, and real MobileScanner camera widget
    expect(find.text('Attendance Check-In'), findsOneWidget);
    expect(
      find.text('Align the rotating QR code on the classroom projector screen inside the frame.'),
      findsOneWidget,
    );
    expect(find.byType(MobileScanner), findsOneWidget);
  });

  testWidgets('StudentQrScannerScreen hides manual token entry in release mode', (tester) async {
    final service = QrCheckInService(baseUrl: 'http://localhost:8000');

    await tester.pumpWidget(
      MaterialApp(
        home: StudentQrScannerScreen(
          checkInService: service,
          authToken: 'mock-test-auth-token',
          enableManualTokenEntry: false, // Simulates kReleaseMode behavior
        ),
      ),
    );

    // Verify manual paste field is completely absent
    expect(find.byType(TextField), findsNothing);
    expect(find.text('[DEV/TEST ONLY] Paste signed QR token string'), findsNothing);
  });

  testWidgets('StudentQrScannerScreen renders customScannerView when provided', (tester) async {
    final service = QrCheckInService(baseUrl: 'http://localhost:8000');

    await tester.pumpWidget(
      MaterialApp(
        home: StudentQrScannerScreen(
          checkInService: service,
          authToken: 'mock-test-auth-token',
          customScannerView: const KeyedSubtree(
            key: Key('mock_camera_preview'),
            child: Text('Custom Mock Camera Active'),
          ),
        ),
      ),
    );

    expect(find.byKey(const Key('mock_camera_preview')), findsOneWidget);
    expect(find.text('Custom Mock Camera Active'), findsOneWidget);
  });
}
