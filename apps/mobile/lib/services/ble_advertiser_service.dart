import 'package:flutter/foundation.dart';
import 'package:flutter_ble_peripheral/flutter_ble_peripheral.dart';

/// Abstract interface for BLE presence advertiser.
abstract class BleAdvertiserInterface {
  bool get isAdvertising;
  Future<bool> startAdvertising({
    required String serviceUuid,
    required Uint8List payload,
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
  Future<bool> startAdvertising({
    required String serviceUuid,
    required Uint8List payload,
  }) async {
    try {
      final isSupported = await _peripheral.isSupported;
      if (!isSupported) {
        debugPrint('BLE Peripheral mode unsupported on this device.');
        return false;
      }

      final advertiseData = AdvertiseDataCore(
        serviceUuid: serviceUuid,
        manufacturerId: 0x004C, // Standard manufacturer identifier fallback
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
