import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:university_attendance_mobile/screens/lecturer_ble_broadcast_screen.dart';
import 'package:university_attendance_mobile/services/ble_advertiser_service.dart';
import 'package:university_attendance_mobile/services/lecturer_ble_service.dart';

class _MockBleAdvertiser implements BleAdvertiserInterface {
  bool isSupportedResponse = true;
  bool startResponse = true;
  bool _isAdvertising = false;
  int startCallCount = 0;
  int stopCallCount = 0;
  String? lastServiceUuid;
  String? lastPayloadBase64;

  @override
  bool get isAdvertising => _isAdvertising;

  @override
  Future<bool> checkSupported() async => isSupportedResponse;

  @override
  Future<bool> startAdvertising({
    required String serviceUuid,
    required Uint8List payload,
  }) async {
    return true;
  }

  @override
  Future<bool> startAdvertisingFromBase64({
    required String serviceUuid,
    required String payloadBase64,
  }) async {
    startCallCount++;
    lastServiceUuid = serviceUuid;
    lastPayloadBase64 = payloadBase64;
    _isAdvertising = startResponse;
    return startResponse;
  }

  @override
  Future<void> stopAdvertising() async {
    stopCallCount++;
    _isAdvertising = false;
  }
}

class _MockLecturerBleService extends LecturerBleService {
  LecturerBlePayload? mockPayload;
  Exception? errorToThrow;
  int fetchCallCount = 0;

  @override
  Future<LecturerBlePayload> fetchBleAdvertisement({
    required String checkpointId,
    required String authToken,
  }) async {
    fetchCallCount++;
    if (errorToThrow != null) {
      throw errorToThrow!;
    }
    return mockPayload ??
        LecturerBlePayload(
          serviceUuid: '0000feaa-0000-1000-8000-00805f9b34fb',
          payloadBase64: 'AX8r123456789012345678==',
          payloadHex: '017f2bd7...',
          protocolVersion: 1,
          rotationSeconds: 20,
          issuedAt: DateTime.now().toUtc(),
          expiresAt: DateTime.now().toUtc().add(const Duration(seconds: 20)),
          checkpointId: checkpointId,
          checkpointType: 'START',
          serverTime: DateTime.now().toUtc(),
          refreshAfterSeconds: 20,
        );
  }
}

void main() {
  late _MockBleAdvertiser mockAdvertiser;
  late _MockLecturerBleService mockService;

  setUp(() {
    mockAdvertiser = _MockBleAdvertiser();
    mockService = _MockLecturerBleService();
  });

  Widget buildTestScreen({
    VoidCallback? onStopped,
  }) {
    return MaterialApp(
      home: LecturerBleBroadcastScreen(
        checkpointId: 'chk-123',
        checkpointType: 'START',
        sessionId: 'sess-456',
        courseCode: 'CS101',
        courseName: 'Intro to Computer Science',
        authToken: 'test-jwt-token',
        bleService: mockService,
        advertiserService: mockAdvertiser,
        onStopped: onStopped,
      ),
    );
  }

  testWidgets(
      'LecturerBleBroadcastScreen initializes and displays active broadcast',
      (tester) async {
    await tester.pumpWidget(buildTestScreen());
    await tester.pumpAndSettle();

    // Verify header
    expect(find.text('CS101 — BLE Presence Beacon'), findsOneWidget);
    expect(find.text('CS101'), findsOneWidget);
    expect(find.text('START CHECKPOINT'), findsOneWidget);
    expect(find.text('Intro to Computer Science'), findsOneWidget);

    // Verify active status and countdown
    expect(find.text('BLE BROADCAST ACTIVE'), findsOneWidget);
    expect(find.text('20s'), findsOneWidget);
    expect(find.text('ROTATION'), findsOneWidget);

    // Verify advertiser was started with correct payload
    expect(mockAdvertiser.startCallCount, equals(1));
    expect(mockAdvertiser.lastServiceUuid,
        equals('0000feaa-0000-1000-8000-00805f9b34fb'));
    expect(
        mockAdvertiser.lastPayloadBase64, equals('AX8r123456789012345678=='));

    // Verify controls
    expect(find.text('Pause'), findsOneWidget);
    expect(find.text('Stop Beacon'), findsOneWidget);
  });

  testWidgets('Timer counts down and refreshes near rotation interval',
      (tester) async {
    await tester.pumpWidget(buildTestScreen());
    await tester.pumpAndSettle();

    expect(find.text('20s'), findsOneWidget);

    // Advance 5 seconds
    await tester.pump(const Duration(seconds: 5));
    expect(find.text('15s'), findsOneWidget);

    // Advance 14 more seconds (total 19s, remaining 1s)
    await tester.pump(const Duration(seconds: 14));
    expect(find.text('1s'), findsOneWidget);

    // Advance 1 more second to trigger refresh
    await tester.pump(const Duration(seconds: 1));
    await tester.pumpAndSettle();

    // Service fetched again
    expect(mockService.fetchCallCount, equals(2));
    expect(mockAdvertiser.startCallCount, equals(2));
    expect(find.text('20s'), findsOneWidget);
  });

  testWidgets('Pause and Resume toggle radio broadcast correctly',
      (tester) async {
    await tester.pumpWidget(buildTestScreen());
    await tester.pumpAndSettle();

    expect(find.text('BLE BROADCAST ACTIVE'), findsOneWidget);

    // Tap Pause
    await tester.tap(find.text('Pause'));
    await tester.pumpAndSettle();

    expect(find.text('Broadcast Paused'), findsOneWidget);
    expect(find.text('Resume'), findsOneWidget);
    expect(mockAdvertiser.stopCallCount, equals(1));

    // Tap Resume
    await tester.tap(find.text('Resume'));
    await tester.pumpAndSettle();

    expect(find.text('BLE BROADCAST ACTIVE'), findsOneWidget);
    expect(find.text('Pause'), findsOneWidget);
    expect(mockAdvertiser.startCallCount, equals(2));
  });

  testWidgets('Stop Beacon halts radio and calls onStopped callback',
      (tester) async {
    bool stoppedCalled = false;
    await tester.pumpWidget(buildTestScreen(onStopped: () {
      stoppedCalled = true;
    }));
    await tester.pumpAndSettle();

    // Tap Stop Beacon
    await tester.tap(find.text('Stop Beacon'));
    await tester.pumpAndSettle();

    expect(find.text('Broadcast Concluded'), findsOneWidget);
    expect(find.text('Done'), findsOneWidget);
    expect(mockAdvertiser.stopCallCount, equals(1));
    expect(stoppedCalled, isTrue);
  });

  testWidgets('Disposing screen stops advertising radio immediately',
      (tester) async {
    await tester.pumpWidget(buildTestScreen());
    await tester.pumpAndSettle();

    expect(mockAdvertiser.stopCallCount, equals(0));

    // Replace widget to trigger dispose
    await tester.pumpWidget(const MaterialApp(home: SizedBox()));
    await tester.pumpAndSettle();

    expect(mockAdvertiser.stopCallCount, equals(1));
  });

  testWidgets('Hardware unsupported shows unsupported state and error message',
      (tester) async {
    mockAdvertiser.isSupportedResponse = false;

    await tester.pumpWidget(buildTestScreen());
    await tester.pumpAndSettle();

    expect(find.text('BLE Peripheral Mode Unsupported'), findsOneWidget);
    expect(
      find.text('BLE broadcasting is not supported on this device hardware.\n'
          'Students can check in using the classroom projector dynamic QR code.'),
      findsOneWidget,
    );
    expect(mockService.fetchCallCount, equals(0));
    expect(mockAdvertiser.startCallCount, equals(0));
  });

  testWidgets('Bluetooth disabled shows prompt and retry button',
      (tester) async {
    mockAdvertiser.startResponse = false;

    await tester.pumpWidget(buildTestScreen());
    await tester.pumpAndSettle();

    expect(find.text('Bluetooth Disabled'), findsOneWidget);
    expect(find.text('Retry Connection'), findsOneWidget);

    // Simulate enabling bluetooth and clicking retry
    mockAdvertiser.startResponse = true;
    await tester.tap(find.text('Retry Connection'));
    await tester.pumpAndSettle();

    expect(find.text('BLE BROADCAST ACTIVE'), findsOneWidget);
  });

  testWidgets('SESSION_PAUSED error suspends broadcast', (tester) async {
    mockService.errorToThrow = const LecturerBleException(
      code: 'SESSION_PAUSED',
      message: 'Session is currently paused by instructor',
      statusCode: 400,
    );

    await tester.pumpWidget(buildTestScreen());
    await tester.pumpAndSettle();

    expect(find.text('Broadcast Paused'), findsOneWidget);
    expect(find.text('Attendance session is paused. Broadcasting stopped.'),
        findsOneWidget);
    expect(mockAdvertiser.stopCallCount, equals(1));
  });

  testWidgets('CHECKPOINT_NOT_OPEN error concludes broadcast', (tester) async {
    mockService.errorToThrow = const LecturerBleException(
      code: 'CHECKPOINT_NOT_OPEN',
      message: 'Checkpoint is not open',
      statusCode: 400,
    );

    await tester.pumpWidget(buildTestScreen());
    await tester.pumpAndSettle();

    expect(find.text('Broadcast Concluded'), findsOneWidget);
    expect(find.text('Checkpoint window has closed. Broadcasting concluded.'),
        findsOneWidget);
    expect(mockAdvertiser.stopCallCount, equals(1));
  });

  testWidgets('Generic network error displays error view and retry option',
      (tester) async {
    mockService.errorToThrow = const LecturerBleException(
      code: 'NETWORK_TIMEOUT',
      message: 'Connection timed out',
      statusCode: 504,
    );

    await tester.pumpWidget(buildTestScreen());
    await tester.pumpAndSettle();

    expect(find.text('Beacon Broadcast Error'), findsOneWidget);
    expect(find.text('NETWORK_TIMEOUT: Connection timed out'), findsOneWidget);
    expect(find.text('Try Again'), findsOneWidget);
  });
}
