import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mobile_scanner/mobile_scanner.dart';
import 'package:university_attendance_mobile/screens/student_qr_scanner_screen.dart';
import 'package:university_attendance_mobile/services/ble_scanner_service.dart';
import 'package:university_attendance_mobile/services/qr_checkin_service.dart';

void main() {
  testWidgets(
      'StudentQrScannerScreen renders MobileScanner camera preview and instructions',
      (tester) async {
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
      find.text(
          'Align the rotating QR code on the classroom projector screen inside the frame.'),
      findsOneWidget,
    );
    expect(find.byType(MobileScanner), findsOneWidget);
  });

  testWidgets('StudentQrScannerScreen hides manual token entry in release mode',
      (tester) async {
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
    expect(find.text('[DEV/TEST ONLY] Paste signed QR token string'),
        findsNothing);
  });

  testWidgets('StudentQrScannerScreen renders customScannerView when provided',
      (tester) async {
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

  testWidgets(
      'StudentQrScannerScreen displays BLE searching and detected status',
      (tester) async {
    final service = QrCheckInService(baseUrl: 'http://localhost:8000');
    final mockBle = _MockBleScannerForTest();

    await tester.pumpWidget(
      MaterialApp(
        home: StudentQrScannerScreen(
          checkInService: service,
          bleScanner: mockBle,
          authToken: 'mock-test-auth-token',
        ),
      ),
    );

    // Initially searching
    expect(find.text('Searching for classroom BLE beacon...'), findsOneWidget);

    // Emit observation
    mockBle.emit(BleObservation(
      payloadBase64: 'mockpayload',
      rssi: -65,
      observedAtClient: DateTime.now().toUtc(),
      platform: 'android',
    ));
    await tester.pump();

    // Now shows detected with RSSI
    expect(find.text('Classroom BLE detected (-65 dBm)'), findsOneWidget);
  });
}

class _MockBleScannerForTest implements BleScannerInterface {
  final _controller = StreamController<BleObservation?>.broadcast();
  BleObservation? _obs;

  @override
  Stream<BleObservation?> get observationStream => _controller.stream;

  @override
  BleObservation? get latestObservation => _obs;

  @override
  BleScannerState get state => BleScannerState.scanning;

  void emit(BleObservation observation) {
    _obs = observation;
    _controller.add(observation);
  }

  @override
  Future<void> startScan({String? serviceUuid}) async {}

  @override
  Future<void> stopScan() async {}

  @override
  void dispose() {
    _controller.close();
  }
}
