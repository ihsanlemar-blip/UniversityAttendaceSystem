import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:flutter_ble_peripheral/flutter_ble_peripheral.dart';

/// Abstract interface for BLE presence advertiser to allow deterministic mocking.
abstract class BleAdvertiserInterface {
  bool get isAdvertising;
  Future<bool> checkSupported();
  Future<bool> startAdvertising({
    required String serviceUuid,
    required Uint8List payload,
  });
  Future<bool> startAdvertisingFromBase64({
    required String serviceUuid,
    required String payloadBase64,
  });
  Future<void> stopAdvertising();
}

/// Production implementation of BLE broadcaster for lecturer attendance sessions.
class BleAdvertiserService implements BleAdvertiserInterface {
  final FlutterBlePeripheral _peripheral = FlutterBlePeripheral();
  bool _isAdvertising = false;

  @override
  bool get isAdvertising => _isAdvertising;

  @override
  Future<bool> checkSupported() async {
    try {
      return await _peripheral.isSupported;
    } catch (_) {
      return false;
    }
  }

  @override
  Future<bool> startAdvertisingFromBase64({
    required String serviceUuid,
    required String payloadBase64,
  }) async {
    final rawBytes = base64.decode(payloadBase64.trim());
    return startAdvertising(
      serviceUuid: serviceUuid,
      payload: Uint8List.fromList(rawBytes),
    );
  }

  @override
  Future<bool> startAdvertising({
    required String serviceUuid,
    required Uint8List payload,
  }) async {
    if (payload.length != 17) {
      debugPrint(
        'Warning: Expected 17-byte binary BLE presence payload, got ${payload.length} bytes.',
      );
    }

    try {
      final isSupported = await _peripheral.isSupported;
      if (!isSupported) {
        debugPrint('BLE Peripheral mode unsupported on this device.');
        return false;
      }

      final advertiseData = AndroidAdvertiseData(
        serviceUuid: serviceUuid,
        serviceDataUuid: serviceUuid,
        serviceData: payload,
        manufacturerId: 0x004C, // Standard fallback manufacturer ID
        manufacturerData: payload,
      );

      await _peripheral.start(advertiseData: advertiseData);
      _isAdvertising = true;
      return true;
    } catch (e) {
      debugPrint('Failed to start BLE advertising: $e');
      _isAdvertising = false;
      return false;
    }
  }

  @override
  Future<void> stopAdvertising() async {
    try {
      if (_isAdvertising) {
        await _peripheral.stop();
        _isAdvertising = false;
      }
    } catch (e) {
      debugPrint('Failed to stop BLE advertising: $e');
    }
  }
}
