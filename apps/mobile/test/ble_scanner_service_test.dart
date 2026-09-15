import 'dart:async';
import 'package:flutter_test/flutter_test.dart';
import 'package:university_attendance_mobile/services/ble_scanner_service.dart';

class MockBleScanner implements BleScannerInterface {
  final _controller = StreamController<BleObservation?>.broadcast();
  BleObservation? _obs;
  BleScannerState _state = BleScannerState.idle;

  @override
  Stream<BleObservation?> get observationStream => _controller.stream;

  @override
  BleObservation? get latestObservation => _obs;

  @override
  BleScannerState get state => _state;

  void emitObservation(BleObservation observation) {
    _obs = observation;
    _controller.add(observation);
  }

  @override
  Future<void> startScan({String? serviceUuid}) async {
    _state = BleScannerState.scanning;
  }

  @override
  Future<void> stopScan() async {
    _state = BleScannerState.idle;
  }

  @override
  void dispose() {
    _controller.close();
  }
}

void main() {
  group('BleObservation Tests', () {
    test('Serializes to JSON accurately', () {
      final now = DateTime.utc(2026, 9, 15, 10, 0, 0);
      final obs = BleObservation(
        payloadBase64: 'AQOOK3BW9Y738zXwRr2MpGQ=',
        rssi: -68,
        observedAtClient: now,
        platform: 'android',
      );

      final json = obs.toJson();
      expect(json['payload'], equals('AQOOK3BW9Y738zXwRr2MpGQ='));
      expect(json['rssi'], equals(-68));
      expect(json['observed_at_client'], equals(now.toIso8601String()));
      expect(json['platform'], equals('android'));
    });
  });

  group('MockBleScanner Tests', () {
    test('Emits observations over stream and updates latestObservation',
        () async {
      final scanner = MockBleScanner();
      expect(scanner.state, equals(BleScannerState.idle));

      await scanner.startScan();
      expect(scanner.state, equals(BleScannerState.scanning));

      final obs = BleObservation(
        payloadBase64: 'payload123',
        rssi: -75,
        observedAtClient: DateTime.now().toUtc(),
        platform: 'ios',
      );

      final futureObs = scanner.observationStream.first;
      scanner.emitObservation(obs);

      final received = await futureObs;
      expect(received?.payloadBase64, equals('payload123'));
      expect(received?.rssi, equals(-75));
      expect(scanner.latestObservation?.rssi, equals(-75));

      await scanner.stopScan();
      expect(scanner.state, equals(BleScannerState.idle));
      scanner.dispose();
    });
  });
}
