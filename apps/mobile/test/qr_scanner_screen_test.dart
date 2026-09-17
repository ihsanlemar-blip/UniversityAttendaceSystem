import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mobile_scanner/mobile_scanner.dart';
import 'package:university_attendance_mobile/screens/student_qr_scanner_screen.dart';
import 'package:university_attendance_mobile/services/ble_scanner_service.dart';
import 'package:university_attendance_mobile/services/presence_checkin_service.dart';
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

  testWidgets(
      'StudentQrScannerScreen displays Attendance Confirmed on successful check-in',
      (tester) async {
    final service = QrCheckInService(baseUrl: 'http://localhost:8000');
    final mockPresence = _MockPresenceServiceForTest(
      mockResult: PresenceCheckInResult(
        accepted: true,
        checkpointType: 'START',
        alreadyCredited: false,
        verifiedAt: DateTime.now().toUtc(),
        attendanceRecordId: 'rec-123',
        verifiedFactors: ['QR', 'BLE_BEACON'],
        presenceMode: 'QR_AND_BLE',
      ),
    );

    await tester.pumpWidget(
      MaterialApp(
        home: StudentQrScannerScreen(
          checkInService: service,
          presenceCheckInService: mockPresence,
          authToken: 'mock-test-auth-token',
          enableManualTokenEntry: true,
        ),
      ),
    );

    await tester.enterText(find.byType(TextField), 'valid.qr.token');
    await tester.tap(find.byIcon(Icons.send));
    await tester.pumpAndSettle();

    expect(find.text('Attendance Confirmed'), findsOneWidget);
    expect(find.text('START Checkpoint Credited'), findsOneWidget);
    expect(find.text('Presence verified via QR + BLE_BEACON.'), findsOneWidget);
    expect(find.text('Done'), findsOneWidget);
  });

  testWidgets(
      'StudentQrScannerScreen displays Already Recorded on duplicate check-in (INV-05)',
      (tester) async {
    final service = QrCheckInService(baseUrl: 'http://localhost:8000');
    final mockPresence = _MockPresenceServiceForTest(
      mockResult: PresenceCheckInResult(
        accepted: true,
        checkpointType: 'START',
        alreadyCredited: true,
        verifiedAt: DateTime.now().toUtc(),
        attendanceRecordId: 'rec-123',
        verifiedFactors: ['QR'],
        presenceMode: 'QR_ONLY',
      ),
    );

    await tester.pumpWidget(
      MaterialApp(
        home: StudentQrScannerScreen(
          checkInService: service,
          presenceCheckInService: mockPresence,
          authToken: 'mock-test-auth-token',
          enableManualTokenEntry: true,
        ),
      ),
    );

    await tester.enterText(find.byType(TextField), 'valid.qr.token');
    await tester.tap(find.byIcon(Icons.send));
    await tester.pumpAndSettle();

    expect(find.text('START Already Recorded'), findsOneWidget);
    expect(
      find.text(
          'You have already received credit for this checkpoint window. Duplicate credit is prevented (INV-05).'),
      findsOneWidget,
    );
  });

  testWidgets(
      'StudentQrScannerScreen displays Saved for Synchronization on offline claim',
      (tester) async {
    final service = QrCheckInService(baseUrl: 'http://localhost:8000');

    await tester.pumpWidget(
      MaterialApp(
        home: StudentQrScannerScreen(
          checkInService: service,
          authToken: 'mock-test-auth-token',
          enableManualTokenEntry: true,
        ),
      ),
    );

    await tester.enterText(find.byType(TextField), 'offline_qr_challenge_xyz');
    await tester.tap(find.byIcon(Icons.send));
    await tester.pumpAndSettle();

    expect(find.text('Saved for Synchronization'), findsOneWidget);
    expect(find.text('(Pending server reconciliation)'), findsOneWidget);
    expect(
      find.text(
          'Offline attendance evidence stored in secure local outbox. Official credit will be confirmed after server synchronization.'),
      findsOneWidget,
    );
  });

  testWidgets(
      'StudentQrScannerScreen displays Token Expired card on TOKEN_EXPIRED error',
      (tester) async {
    final service = QrCheckInService(baseUrl: 'http://localhost:8000');
    final mockPresence = _MockPresenceServiceForTest(
      mockException: const PresenceCheckInException(
        code: 'TOKEN_EXPIRED',
        message: 'Token has expired',
        statusCode: 400,
      ),
    );

    await tester.pumpWidget(
      MaterialApp(
        home: StudentQrScannerScreen(
          checkInService: service,
          presenceCheckInService: mockPresence,
          authToken: 'mock-test-auth-token',
          enableManualTokenEntry: true,
        ),
      ),
    );

    await tester.enterText(find.byType(TextField), 'expired.token.str');
    await tester.tap(find.byIcon(Icons.send));
    await tester.pumpAndSettle();

    expect(find.text('Token Expired'), findsOneWidget);
    expect(find.text('Try Again'), findsOneWidget);

    // Tap Try Again and verify resets to scanner view
    await tester.tap(find.text('Try Again'));
    await tester.pumpAndSettle();

    expect(find.byType(TextField), findsOneWidget);
  });

  testWidgets(
      'StudentQrScannerScreen displays Checkpoint Not Open on CHECKPOINT_NOT_OPEN',
      (tester) async {
    final service = QrCheckInService(baseUrl: 'http://localhost:8000');
    final mockPresence = _MockPresenceServiceForTest(
      mockException: const PresenceCheckInException(
        code: 'CHECKPOINT_NOT_OPEN',
        message: 'No checkpoint is open',
        statusCode: 400,
      ),
    );

    await tester.pumpWidget(
      MaterialApp(
        home: StudentQrScannerScreen(
          checkInService: service,
          presenceCheckInService: mockPresence,
          authToken: 'mock-test-auth-token',
          enableManualTokenEntry: true,
        ),
      ),
    );

    await tester.enterText(find.byType(TextField), 'valid.token');
    await tester.tap(find.byIcon(Icons.send));
    await tester.pumpAndSettle();

    expect(find.text('Checkpoint Not Open'), findsOneWidget);
  });

  testWidgets(
      'StudentQrScannerScreen displays Session Closed on SESSION_CLOSED',
      (tester) async {
    final service = QrCheckInService(baseUrl: 'http://localhost:8000');
    final mockPresence = _MockPresenceServiceForTest(
      mockException: const PresenceCheckInException(
        code: 'SESSION_CLOSED',
        message: 'Session is closed',
        statusCode: 400,
      ),
    );

    await tester.pumpWidget(
      MaterialApp(
        home: StudentQrScannerScreen(
          checkInService: service,
          presenceCheckInService: mockPresence,
          authToken: 'mock-test-auth-token',
          enableManualTokenEntry: true,
        ),
      ),
    );

    await tester.enterText(find.byType(TextField), 'valid.token');
    await tester.tap(find.byIcon(Icons.send));
    await tester.pumpAndSettle();

    expect(find.text('Session Closed'), findsOneWidget);
  });

  testWidgets(
      'StudentQrScannerScreen displays Device Not Registered on DEVICE_NOT_REGISTERED',
      (tester) async {
    final service = QrCheckInService(baseUrl: 'http://localhost:8000');
    final mockPresence = _MockPresenceServiceForTest(
      mockException: const PresenceCheckInException(
        code: 'DEVICE_NOT_REGISTERED',
        message: 'Device not registered',
        statusCode: 400,
      ),
    );

    await tester.pumpWidget(
      MaterialApp(
        home: StudentQrScannerScreen(
          checkInService: service,
          presenceCheckInService: mockPresence,
          authToken: 'mock-test-auth-token',
          enableManualTokenEntry: true,
        ),
      ),
    );

    await tester.enterText(find.byType(TextField), 'valid.token');
    await tester.tap(find.byIcon(Icons.send));
    await tester.pumpAndSettle();

    expect(find.text('Device Not Registered'), findsOneWidget);
  });

  testWidgets(
      'StudentQrScannerScreen displays Classroom BLE Required on BLE_REQUIRED',
      (tester) async {
    final service = QrCheckInService(baseUrl: 'http://localhost:8000');
    final mockPresence = _MockPresenceServiceForTest(
      mockException: const PresenceCheckInException(
        code: 'BLE_REQUIRED',
        message: 'Beacon proximity missing',
        statusCode: 400,
      ),
    );

    await tester.pumpWidget(
      MaterialApp(
        home: StudentQrScannerScreen(
          checkInService: service,
          presenceCheckInService: mockPresence,
          authToken: 'mock-test-auth-token',
          enableManualTokenEntry: true,
        ),
      ),
    );

    await tester.enterText(find.byType(TextField), 'valid.token');
    await tester.tap(find.byIcon(Icons.send));
    await tester.pumpAndSettle();

    expect(find.text('Classroom BLE Required'), findsOneWidget);
  });

  testWidgets(
      'StudentQrScannerScreen displays Campus Wi-Fi Required on CAMPUS_NETWORK_NOT_DETECTED',
      (tester) async {
    final service = QrCheckInService(baseUrl: 'http://localhost:8000');
    final mockPresence = _MockPresenceServiceForTest(
      mockException: const PresenceCheckInException(
        code: 'CAMPUS_NETWORK_NOT_DETECTED',
        message: 'Not on campus network',
        statusCode: 400,
      ),
    );

    await tester.pumpWidget(
      MaterialApp(
        home: StudentQrScannerScreen(
          checkInService: service,
          presenceCheckInService: mockPresence,
          authToken: 'mock-test-auth-token',
          enableManualTokenEntry: true,
        ),
      ),
    );

    await tester.enterText(find.byType(TextField), 'valid.token');
    await tester.tap(find.byIcon(Icons.send));
    await tester.pumpAndSettle();

    expect(find.text('Campus Wi-Fi Required'), findsOneWidget);
  });

  testWidgets('StudentQrScannerScreen displays Not Enrolled on NOT_ENROLLED',
      (tester) async {
    final service = QrCheckInService(baseUrl: 'http://localhost:8000');
    final mockPresence = _MockPresenceServiceForTest(
      mockException: const PresenceCheckInException(
        code: 'NOT_ENROLLED',
        message: 'Student not enrolled in course',
        statusCode: 400,
      ),
    );

    await tester.pumpWidget(
      MaterialApp(
        home: StudentQrScannerScreen(
          checkInService: service,
          presenceCheckInService: mockPresence,
          authToken: 'mock-test-auth-token',
          enableManualTokenEntry: true,
        ),
      ),
    );

    await tester.enterText(find.byType(TextField), 'valid.token');
    await tester.tap(find.byIcon(Icons.send));
    await tester.pumpAndSettle();

    expect(find.text('Not Enrolled'), findsOneWidget);
  });

  testWidgets(
      'StudentQrScannerScreen displays Server Unreachable on SERVER_UNREACHABLE',
      (tester) async {
    final service = QrCheckInService(baseUrl: 'http://localhost:8000');
    final mockPresence = _MockPresenceServiceForTest(
      mockException: const PresenceCheckInException(
        code: 'SERVER_UNREACHABLE',
        message: 'Cannot reach server',
        statusCode: 503,
      ),
    );

    await tester.pumpWidget(
      MaterialApp(
        home: StudentQrScannerScreen(
          checkInService: service,
          presenceCheckInService: mockPresence,
          authToken: 'mock-test-auth-token',
          enableManualTokenEntry: true,
        ),
      ),
    );

    await tester.enterText(find.byType(TextField), 'valid.token');
    await tester.tap(find.byIcon(Icons.send));
    await tester.pumpAndSettle();

    expect(find.text('Server Unreachable'), findsOneWidget);
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

class _MockPresenceServiceForTest extends PresenceCheckInService {
  final PresenceCheckInResult? mockResult;
  final Exception? mockException;

  _MockPresenceServiceForTest({this.mockResult, this.mockException});

  @override
  Future<PresenceCheckInResult> submitPresenceCheckIn({
    String? qrToken,
    BleObservation? bleObservation,
    Map<String, dynamic>? deviceProof,
    Map<String, dynamic>? networkProof,
    required String authToken,
  }) async {
    if (mockException != null) throw mockException!;
    return mockResult!;
  }
}
