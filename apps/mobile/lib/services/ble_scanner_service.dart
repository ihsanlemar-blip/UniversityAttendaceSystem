import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'package:flutter/foundation.dart';
import 'package:flutter_blue_plus/flutter_blue_plus.dart';

/// Observed BLE telemetry captured by student device.
class BleObservation {
  final String payloadBase64;
  final int rssi;
  final DateTime observedAtClient;
  final String platform;

  const BleObservation({
    required this.payloadBase64,
    required this.rssi,
    required this.observedAtClient,
    required this.platform,
  });

  Map<String, dynamic> toJson() => {
        'payload': payloadBase64,
        'rssi': rssi,
        'observed_at_client': observedAtClient.toIso8601String(),
        'platform': platform,
      };
}

enum BleScannerState {
  unsupported,
  unauthorized,
  poweredOff,
  scanning,
  idle,
}

/// Abstract interface for BLE presence scanning to allow deterministic testing and mocking.
abstract class BleScannerInterface {
  Stream<BleObservation?> get observationStream;
  BleObservation? get latestObservation;
  BleScannerState get state;
  Future<void> startScan({String? serviceUuid});
  Future<void> stopScan();
  void dispose();
}

/// Production implementation of BLE proximity scanner using flutter_blue_plus.
class BleScannerService implements BleScannerInterface {
  static const String defaultServiceUuid =
      '0000fee0-0000-1000-8000-00805f9b34fb';

  final _observationController = StreamController<BleObservation?>.broadcast();
  StreamSubscription? _scanSubscription;
  BleObservation? _latestObservation;
  BleScannerState _state = BleScannerState.idle;

  @override
  Stream<BleObservation?> get observationStream =>
      _observationController.stream;

  @override
  BleObservation? get latestObservation => _latestObservation;

  @override
  BleScannerState get state => _state;

  @override
  Future<void> startScan({String? serviceUuid}) async {
    final targetUuid = (serviceUuid ?? defaultServiceUuid).toLowerCase();

    // Check adapter availability
    try {
      if (!await FlutterBluePlus.isSupported) {
        _state = BleScannerState.unsupported;
        return;
      }

      final adapterState = await FlutterBluePlus.adapterState.first;
      if (adapterState != BluetoothAdapterState.on) {
        _state = BleScannerState.poweredOff;
        return;
      }
    } catch (_) {
      // In test/unsupported environments
      _state = BleScannerState.unsupported;
      return;
    }

    _state = BleScannerState.scanning;

    // Listen to scan results
    await _scanSubscription?.cancel();
    _scanSubscription = FlutterBluePlus.scanResults.listen((results) {
      for (final r in results) {
        // Inspect service data or manufacturer data
        final serviceData = r.advertisementData.serviceData;
        for (final entry in serviceData.entries) {
          if (entry.key.toString().toLowerCase().contains(targetUuid) ||
              targetUuid.contains(entry.key.toString().toLowerCase())) {
            final rawBytes = entry.value;
            if (rawBytes.isNotEmpty) {
              _recordObservation(rawBytes, r.rssi);
              return;
            }
          }
        }

        // Fallback check: manufacturer data if service data is empty
        if (r.advertisementData.manufacturerData.isNotEmpty) {
          final mData = r.advertisementData.manufacturerData.values.first;
          if (mData.length == 17) {
            _recordObservation(mData, r.rssi);
            return;
          }
        }
      }
    });

    try {
      await FlutterBluePlus.startScan(
        timeout: const Duration(seconds: 45),
        androidScanMode: AndroidScanMode.lowLatency,
      );
    } catch (e) {
      debugPrint('BLE Scan error: $e');
      _state = BleScannerState.unauthorized;
    }
  }

  void _recordObservation(List<int> bytes, int rssi) {
    final b64 = base64.encode(bytes);
    final obs = BleObservation(
      payloadBase64: b64,
      rssi: rssi,
      observedAtClient: DateTime.now().toUtc(),
      platform: Platform.isAndroid
          ? 'android'
          : Platform.isIOS
              ? 'ios'
              : 'other',
    );
    _latestObservation = obs;
    if (!_observationController.isClosed) {
      _observationController.add(obs);
    }
  }

  @override
  Future<void> stopScan() async {
    try {
      await FlutterBluePlus.stopScan();
    } catch (_) {}
    await _scanSubscription?.cancel();
    _scanSubscription = null;
    _state = BleScannerState.idle;
  }

  @override
  void dispose() {
    stopScan();
    _observationController.close();
  }
}
