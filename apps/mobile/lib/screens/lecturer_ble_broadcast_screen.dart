import 'dart:async';
import 'package:flutter/material.dart';
import '../services/ble_advertiser_service.dart';
import '../services/lecturer_ble_service.dart';

enum BroadcastUiState {
  loading,
  broadcasting,
  paused,
  stopped,
  bluetoothDisabled,
  unsupported,
  error,
}

/// Mobile screen for lecturers to broadcast rotating classroom BLE presence beacons.
///
/// Enforces:
/// - INV-01: Zero local HMAC key storage; advertisements are strictly server-generated.
/// - Radio Lifecycle: Automatically stops advertising on pause, close, or screen disposal.
/// - Deterministic Rotation: Refreshes before token expiration and re-broadcasts new payload.
class LecturerBleBroadcastScreen extends StatefulWidget {
  final String checkpointId;
  final String checkpointType;
  final String sessionId;
  final String courseCode;
  final String courseName;
  final String authToken;
  final LecturerBleService? bleService;
  final BleAdvertiserInterface? advertiserService;
  final VoidCallback? onStopped;

  const LecturerBleBroadcastScreen({
    super.key,
    required this.checkpointId,
    required this.checkpointType,
    required this.sessionId,
    required this.courseCode,
    required this.courseName,
    required this.authToken,
    this.bleService,
    this.advertiserService,
    this.onStopped,
  });

  @override
  State<LecturerBleBroadcastScreen> createState() =>
      _LecturerBleBroadcastScreenState();
}

class _LecturerBleBroadcastScreenState
    extends State<LecturerBleBroadcastScreen> {
  late final LecturerBleService _bleService;
  late final BleAdvertiserInterface _advertiserService;

  BroadcastUiState _uiState = BroadcastUiState.loading;
  LecturerBlePayload? _currentPayload;
  String? _errorMessage;
  int _secondsRemaining = 20;
  Timer? _countdownTimer;

  @override
  void initState() {
    super.initState();
    _bleService = widget.bleService ?? LecturerBleService();
    _advertiserService = widget.advertiserService ?? BleAdvertiserService();
    _initBroadcast();
  }

  @override
  void dispose() {
    _countdownTimer?.cancel();
    _advertiserService.stopAdvertising();
    super.dispose();
  }

  Future<void> _initBroadcast() async {
    setState(() {
      _uiState = BroadcastUiState.loading;
      _errorMessage = null;
    });

    final isSupported = await _advertiserService.checkSupported();
    if (!isSupported) {
      setState(() {
        _uiState = BroadcastUiState.unsupported;
        _errorMessage =
            'BLE broadcasting is not supported on this device hardware.\n'
            'Students can check in using the classroom projector dynamic QR code.';
      });
      return;
    }

    await _fetchAndBroadcast();
  }

  Future<void> _fetchAndBroadcast() async {
    try {
      final payload = await _bleService.fetchBleAdvertisement(
        checkpointId: widget.checkpointId,
        authToken: widget.authToken,
      );

      final success = await _advertiserService.startAdvertisingFromBase64(
        serviceUuid: payload.serviceUuid,
        payloadBase64: payload.payloadBase64,
      );

      if (!success) {
        setState(() {
          _uiState = BroadcastUiState.bluetoothDisabled;
          _errorMessage =
              'Bluetooth is turned off or advertising permission was denied.\n'
              'Please enable Bluetooth to broadcast the presence beacon.';
        });
        return;
      }

      setState(() {
        _currentPayload = payload;
        _uiState = BroadcastUiState.broadcasting;
        _secondsRemaining = payload.refreshAfterSeconds;
      });

      _startRotationTimer();
    } on LecturerBleException catch (e) {
      if (e.code == 'SESSION_PAUSED' || e.code == 'SESSION_NOT_ACTIVE') {
        await _advertiserService.stopAdvertising();
        setState(() {
          _uiState = BroadcastUiState.paused;
          _errorMessage = 'Attendance session is paused. Broadcasting stopped.';
        });
      } else if (e.code == 'CHECKPOINT_NOT_OPEN' ||
          e.code == 'CHECKPOINT_WINDOW_EXPIRED') {
        await _advertiserService.stopAdvertising();
        setState(() {
          _uiState = BroadcastUiState.stopped;
          _errorMessage =
              'Checkpoint window has closed. Broadcasting concluded.';
        });
      } else {
        setState(() {
          _uiState = BroadcastUiState.error;
          _errorMessage = '${e.code}: ${e.message}';
        });
      }
    } catch (e) {
      setState(() {
        _uiState = BroadcastUiState.error;
        _errorMessage = 'Failed to connect to university server: $e';
      });
    }
  }

  void _startRotationTimer() {
    _countdownTimer?.cancel();
    _countdownTimer = Timer.periodic(const Duration(seconds: 1), (timer) {
      if (!mounted) {
        timer.cancel();
        return;
      }

      if (_uiState != BroadcastUiState.broadcasting) {
        timer.cancel();
        return;
      }

      if (_secondsRemaining > 1) {
        setState(() {
          _secondsRemaining--;
        });
      } else {
        timer.cancel();
        _fetchAndBroadcast();
      }
    });
  }

  Future<void> _togglePause() async {
    if (_uiState == BroadcastUiState.broadcasting) {
      _countdownTimer?.cancel();
      await _advertiserService.stopAdvertising();
      setState(() {
        _uiState = BroadcastUiState.paused;
      });
    } else if (_uiState == BroadcastUiState.paused) {
      await _fetchAndBroadcast();
    }
  }

  Future<void> _stopBroadcast() async {
    _countdownTimer?.cancel();
    await _advertiserService.stopAdvertising();
    setState(() {
      _uiState = BroadcastUiState.stopped;
    });
    if (widget.onStopped != null) {
      widget.onStopped!();
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF0F172A), // Slate 900
      appBar: AppBar(
        title: Text('${widget.courseCode} — BLE Presence Beacon'),
        backgroundColor: const Color(0xFF1E293B), // Slate 800
        foregroundColor: Colors.white,
        elevation: 0,
      ),
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(24.0),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              // Header Card
              _buildHeaderCard(),
              const SizedBox(height: 24),

              // Main Status Center
              Expanded(
                child: Center(
                  child: _buildStateContent(),
                ),
              ),

              // Bottom Action Controls
              _buildBottomControls(),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildHeaderCard() {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: const Color(0xFF1E293B),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: Colors.white12),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                widget.courseCode,
                style: const TextStyle(
                  color: Colors.white,
                  fontSize: 18,
                  fontWeight: FontWeight.bold,
                ),
              ),
              Container(
                padding:
                    const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                decoration: BoxDecoration(
                  color: Colors.blueAccent.withValues(alpha: 0.2),
                  borderRadius: BorderRadius.circular(16),
                  border: Border.all(color: Colors.blueAccent),
                ),
                child: Text(
                  '${widget.checkpointType} CHECKPOINT',
                  style: const TextStyle(
                    color: Colors.lightBlueAccent,
                    fontSize: 11,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 4),
          Text(
            widget.courseName,
            style: const TextStyle(color: Colors.white70, fontSize: 13),
          ),
        ],
      ),
    );
  }

  Widget _buildStateContent() {
    switch (_uiState) {
      case BroadcastUiState.loading:
        return const Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            CircularProgressIndicator(color: Colors.blueAccent),
            SizedBox(height: 20),
            Text(
              'Initializing Classroom BLE Beacon...',
              style: TextStyle(color: Colors.white70, fontSize: 15),
            ),
          ],
        );

      case BroadcastUiState.broadcasting:
        return Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Stack(
              alignment: Alignment.center,
              children: [
                SizedBox(
                  width: 160,
                  height: 160,
                  child: CircularProgressIndicator(
                    value: _currentPayload != null &&
                            _currentPayload!.rotationSeconds > 0
                        ? _secondsRemaining / _currentPayload!.rotationSeconds
                        : 1.0,
                    strokeWidth: 8,
                    backgroundColor: Colors.white12,
                    valueColor: const AlwaysStoppedAnimation(Colors.blueAccent),
                  ),
                ),
                Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    const Icon(Icons.bluetooth_audio,
                        size: 44, color: Colors.lightBlueAccent),
                    const SizedBox(height: 6),
                    Text(
                      '${_secondsRemaining}s',
                      style: const TextStyle(
                        color: Colors.white,
                        fontSize: 24,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                    const Text(
                      'ROTATION',
                      style: TextStyle(
                        color: Colors.white54,
                        fontSize: 10,
                        fontWeight: FontWeight.w600,
                        letterSpacing: 1.2,
                      ),
                    ),
                  ],
                ),
              ],
            ),
            const SizedBox(height: 28),
            const Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Icon(Icons.circle, size: 10, color: Colors.greenAccent),
                SizedBox(width: 8),
                Text(
                  'BLE BROADCAST ACTIVE',
                  style: TextStyle(
                    color: Colors.greenAccent,
                    fontSize: 14,
                    fontWeight: FontWeight.bold,
                    letterSpacing: 1.1,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 8),
            const Text(
              'Broadcasting classroom presence beacon.\nStudents in proximity will verify automatically.',
              textAlign: TextAlign.center,
              style: TextStyle(color: Colors.white70, fontSize: 12),
            ),
          ],
        );

      case BroadcastUiState.paused:
        return Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(Icons.pause_circle_outline,
                size: 72, color: Colors.amberAccent),
            const SizedBox(height: 16),
            const Text(
              'Broadcast Paused',
              style: TextStyle(
                  color: Colors.white,
                  fontSize: 18,
                  fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 8),
            Text(
              _errorMessage ?? 'Radio transmission is temporarily suspended.',
              textAlign: TextAlign.center,
              style: const TextStyle(color: Colors.white70, fontSize: 13),
            ),
          ],
        );

      case BroadcastUiState.stopped:
        return Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(Icons.stop_circle_outlined,
                size: 72, color: Colors.white54),
            const SizedBox(height: 16),
            const Text(
              'Broadcast Concluded',
              style: TextStyle(
                  color: Colors.white,
                  fontSize: 18,
                  fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 8),
            Text(
              _errorMessage ?? 'BLE presence beacon is no longer active.',
              textAlign: TextAlign.center,
              style: const TextStyle(color: Colors.white70, fontSize: 13),
            ),
          ],
        );

      case BroadcastUiState.bluetoothDisabled:
        return Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(Icons.bluetooth_disabled,
                size: 72, color: Colors.orangeAccent),
            const SizedBox(height: 16),
            const Text(
              'Bluetooth Disabled',
              style: TextStyle(
                  color: Colors.orangeAccent,
                  fontSize: 18,
                  fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 8),
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16),
              child: Text(
                _errorMessage ?? 'Please enable Bluetooth to continue.',
                textAlign: TextAlign.center,
                style: const TextStyle(color: Colors.white70, fontSize: 13),
              ),
            ),
            const SizedBox(height: 20),
            ElevatedButton.icon(
              onPressed: _fetchAndBroadcast,
              icon: const Icon(Icons.refresh, color: Colors.white),
              label: const Text('Retry Connection',
                  style: TextStyle(color: Colors.white)),
              style:
                  ElevatedButton.styleFrom(backgroundColor: Colors.blueAccent),
            ),
          ],
        );

      case BroadcastUiState.unsupported:
        return Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(Icons.phonelink_erase, size: 72, color: Colors.white54),
            const SizedBox(height: 16),
            const Text(
              'BLE Peripheral Mode Unsupported',
              style: TextStyle(
                  color: Colors.white,
                  fontSize: 16,
                  fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 8),
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16),
              child: Text(
                _errorMessage ?? 'Hardware does not support BLE advertising.',
                textAlign: TextAlign.center,
                style: const TextStyle(color: Colors.white70, fontSize: 12),
              ),
            ),
          ],
        );

      case BroadcastUiState.error:
        return Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(Icons.error_outline, size: 72, color: Colors.redAccent),
            const SizedBox(height: 16),
            const Text(
              'Beacon Broadcast Error',
              style: TextStyle(
                  color: Colors.redAccent,
                  fontSize: 18,
                  fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 8),
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16),
              child: Text(
                _errorMessage ?? 'Unknown error occurred.',
                textAlign: TextAlign.center,
                style: const TextStyle(color: Colors.white70, fontSize: 13),
              ),
            ),
            const SizedBox(height: 20),
            ElevatedButton.icon(
              onPressed: _fetchAndBroadcast,
              icon: const Icon(Icons.refresh, color: Colors.white),
              label: const Text('Try Again',
                  style: TextStyle(color: Colors.white)),
              style:
                  ElevatedButton.styleFrom(backgroundColor: Colors.redAccent),
            ),
          ],
        );
    }
  }

  Widget _buildBottomControls() {
    if (_uiState == BroadcastUiState.broadcasting ||
        _uiState == BroadcastUiState.paused) {
      return Row(
        children: [
          Expanded(
            child: OutlinedButton.icon(
              onPressed: _togglePause,
              icon: Icon(
                _uiState == BroadcastUiState.broadcasting
                    ? Icons.pause
                    : Icons.play_arrow,
                color: Colors.white,
              ),
              label: Text(
                _uiState == BroadcastUiState.broadcasting ? 'Pause' : 'Resume',
                style: const TextStyle(color: Colors.white),
              ),
              style: OutlinedButton.styleFrom(
                padding: const EdgeInsets.symmetric(vertical: 14),
                side: const BorderSide(color: Colors.white30),
              ),
            ),
          ),
          const SizedBox(width: 16),
          Expanded(
            child: ElevatedButton.icon(
              onPressed: _stopBroadcast,
              icon: const Icon(Icons.stop, color: Colors.white),
              label: const Text('Stop Beacon',
                  style: TextStyle(color: Colors.white)),
              style: ElevatedButton.styleFrom(
                backgroundColor: Colors.redAccent,
                padding: const EdgeInsets.symmetric(vertical: 14),
              ),
            ),
          ),
        ],
      );
    }

    return ElevatedButton(
      onPressed: () => Navigator.of(context).maybePop(),
      style: ElevatedButton.styleFrom(
        backgroundColor: const Color(0xFF334155),
        padding: const EdgeInsets.symmetric(vertical: 14),
      ),
      child: const Text('Done', style: TextStyle(color: Colors.white)),
    );
  }
}
