import 'dart:async';
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:mobile_scanner/mobile_scanner.dart';
import '../core/offline/offline_storage.dart';
import '../services/ble_scanner_service.dart';
import '../services/device_key_service.dart';
import '../services/presence_checkin_service.dart';
import '../services/qr_checkin_service.dart';

enum ScannerViewStatus {
  scanning,
  submitting,
  success,
  alreadyCredited,
  offlineRecorded,
  error,
}

/// Mobile scanner screen for students to capture rotating classroom dynamic QR codes
/// and simultaneously capture classroom BLE presence beacons.
class StudentQrScannerScreen extends StatefulWidget {
  final QrCheckInService checkInService;
  final PresenceCheckInService? presenceCheckInService;
  final BleScannerInterface? bleScanner;
  final DeviceKeyService? deviceKeyService;
  final String authToken;
  final String? userId;
  final String? universityId;
  final VoidCallback? onCompleted;
  final bool enableManualTokenEntry;
  final MobileScannerController? scannerController;
  final Widget? customScannerView;

  const StudentQrScannerScreen({
    super.key,
    required this.checkInService,
    this.presenceCheckInService,
    this.bleScanner,
    this.deviceKeyService,
    required this.authToken,
    this.userId,
    this.universityId,
    this.onCompleted,
    this.enableManualTokenEntry = kDebugMode,
    this.scannerController,
    this.customScannerView,
  });

  @override
  State<StudentQrScannerScreen> createState() => _StudentQrScannerScreenState();
}

class _StudentQrScannerScreenState extends State<StudentQrScannerScreen> {
  ScannerViewStatus _status = ScannerViewStatus.scanning;
  PresenceCheckInResult? _result;
  String? _errorMessage;
  final TextEditingController _manualTokenController = TextEditingController();
  late final MobileScannerController _controller;
  bool _internalControllerCreated = false;

  late final PresenceCheckInService _presenceService;
  BleScannerInterface? _bleScanner;
  StreamSubscription<BleObservation?>? _bleSubscription;
  BleObservation? _latestBleObservation;

  @override
  void initState() {
    super.initState();
    _presenceService = widget.presenceCheckInService ??
        PresenceCheckInService(baseUrl: widget.checkInService.baseUrl);

    _bleScanner = widget.bleScanner ?? BleScannerService();
    _bleScanner?.startScan();
    _bleSubscription = _bleScanner?.observationStream.listen((obs) {
      if (mounted) {
        setState(() {
          _latestBleObservation = obs;
        });
      }
    });

    if (widget.scannerController != null) {
      _controller = widget.scannerController!;
    } else {
      _controller = MobileScannerController(
        formats: const [BarcodeFormat.qrCode],
        detectionSpeed: DetectionSpeed.noDuplicates,
        facing: CameraFacing.back,
      );
      _internalControllerCreated = true;
    }
  }

  @override
  void dispose() {
    _manualTokenController.dispose();
    _bleSubscription?.cancel();
    _bleScanner?.stopScan();
    if (_internalControllerCreated) {
      _controller.dispose();
    }
    super.dispose();
  }

  Future<void> _processScannedToken(String rawToken) async {
    final trimmed = rawToken.trim();
    if (trimmed.isEmpty) return;

    // Check for offline QR presence challenge (Milestone 12 & 13)
    if (trimmed.contains('offline_qr')) {
      final claimId = 'claim_${DateTime.now().millisecondsSinceEpoch}';
      String? trustedDevId;
      String? deviceProofSig;

      if (widget.deviceKeyService != null) {
        trustedDevId = await widget.deviceKeyService!.getDeviceId();
        if (trustedDevId != null &&
            widget.userId != null &&
            widget.universityId != null) {
          deviceProofSig =
              await widget.deviceKeyService!.signOfflineAttendanceClaim(
            userId: widget.userId!,
            universityId: widget.universityId!,
            deviceId: trustedDevId,
            claimId: claimId,
            permitId: 'offline_permit',
            authorityEpoch: 1,
            checkpointType: 'START',
            qrChallengeToken: trimmed,
          );
        }
      }

      final claim = OfflineStudentClaimModel(
        claimId: claimId,
        permitId: 'offline_permit',
        checkpointType: 'START',
        rotationSlot: DateTime.now().millisecondsSinceEpoch ~/ 20000,
        qrChallengeToken: trimmed,
        bleEvidence: _latestBleObservation != null
            ? {'rssi': _latestBleObservation!.rssi}
            : null,
        clientCapturedAtUtc: DateTime.now().toUtc(),
        status: 'PENDING_SYNC',
        trustedDeviceId: trustedDevId,
        deviceProofSignature: deviceProofSig,
      );
      MobileOfflineStorage().addStudentClaim(claim);
      setState(() {
        _status = ScannerViewStatus.offlineRecorded;
      });
      if (widget.onCompleted != null) {
        widget.onCompleted!();
      }
      return;
    }

    setState(() {
      _status = ScannerViewStatus.submitting;
      _errorMessage = null;
    });

    try {
      // Build Device Proof (Milestone 13)
      Map<String, dynamic>? deviceProof;
      if (widget.deviceKeyService != null) {
        final devId = await widget.deviceKeyService!.getDeviceId();
        if (devId != null &&
            widget.userId != null &&
            widget.universityId != null) {
          final proofId = 'proof_${DateTime.now().millisecondsSinceEpoch}';
          final sig = await widget.deviceKeyService!.signOnlinePresenceCheckIn(
            userId: widget.userId!,
            universityId: widget.universityId!,
            deviceId: devId,
            proofId: proofId,
            qrToken: trimmed,
            blePayload: _latestBleObservation?.payloadBase64,
          );
          deviceProof = {
            'device_id': devId,
            'proof_id': proofId,
            'signature': sig,
          };
        }
      }

      final result = await _presenceService.submitPresenceCheckIn(
        qrToken: trimmed,
        bleObservation: _latestBleObservation ?? _bleScanner?.latestObservation,
        deviceProof: deviceProof,
        authToken: widget.authToken,
      );

      setState(() {
        _result = result;
        _status = result.alreadyCredited
            ? ScannerViewStatus.alreadyCredited
            : ScannerViewStatus.success;
      });

      if (widget.onCompleted != null) {
        widget.onCompleted!();
      }
    } on PresenceCheckInException catch (e) {
      setState(() {
        _status = ScannerViewStatus.error;
        _errorMessage = '${e.code}: ${e.message}';
      });
    } on QrCheckInException catch (e) {
      setState(() {
        _status = ScannerViewStatus.error;
        _errorMessage = '${e.code}: ${e.message}';
      });
    } catch (e) {
      setState(() {
        _status = ScannerViewStatus.error;
        _errorMessage = 'Network connection failed. Please try again.';
      });
    }
  }

  void _resetScanner() {
    setState(() {
      _status = ScannerViewStatus.scanning;
      _result = null;
      _errorMessage = null;
      _manualTokenController.clear();
    });
    _bleScanner?.startScan();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.black,
      appBar: AppBar(
        title: const Text('Attendance Check-In'),
        backgroundColor: Colors.black,
        foregroundColor: Colors.white,
        elevation: 0,
      ),
      body: SafeArea(
        child: Column(
          children: [
            // BLE Status Indicator Bar
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
              color: Colors.white10,
              child: Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Icon(
                    _latestBleObservation != null
                        ? Icons.bluetooth_connected
                        : Icons.bluetooth_searching,
                    size: 16,
                    color: _latestBleObservation != null
                        ? Colors.lightBlueAccent
                        : Colors.white54,
                  ),
                  const SizedBox(width: 8),
                  Text(
                    _latestBleObservation != null
                        ? 'Classroom BLE detected (${_latestBleObservation!.rssi} dBm)'
                        : 'Searching for classroom BLE beacon...',
                    style: TextStyle(
                      color: _latestBleObservation != null
                          ? Colors.lightBlueAccent
                          : Colors.white54,
                      fontSize: 12,
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                ],
              ),
            ),

            // Instruction header
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 12),
              child: Text(
                _status == ScannerViewStatus.scanning
                    ? 'Align the rotating QR code on the classroom projector screen inside the frame.'
                    : 'Processing presence evidence...',
                textAlign: TextAlign.center,
                style: const TextStyle(color: Colors.white70, fontSize: 14),
              ),
            ),

            // Viewfinder & Status Area
            Expanded(
              child: Center(
                child: Padding(
                  padding: const EdgeInsets.all(24.0),
                  child: _buildScannerContent(),
                ),
              ),
            ),

            // Development/testing manual token input (strictly submits to backend HMAC verification)
            if (_status == ScannerViewStatus.scanning &&
                widget.enableManualTokenEntry)
              Padding(
                padding: const EdgeInsets.all(16.0),
                child: Column(
                  children: [
                    TextField(
                      controller: _manualTokenController,
                      style: const TextStyle(color: Colors.white),
                      decoration: InputDecoration(
                        hintText:
                            '[DEV/TEST ONLY] Paste signed QR token string',
                        hintStyle: const TextStyle(color: Colors.white38),
                        filled: true,
                        fillColor: Colors.white10,
                        border: OutlineInputBorder(
                          borderRadius: BorderRadius.circular(8),
                          borderSide: BorderSide.none,
                        ),
                        suffixIcon: IconButton(
                          icon:
                              const Icon(Icons.send, color: Colors.blueAccent),
                          onPressed: () =>
                              _processScannedToken(_manualTokenController.text),
                        ),
                      ),
                      onSubmitted: _processScannedToken,
                    ),
                  ],
                ),
              ),
          ],
        ),
      ),
    );
  }

  Widget _buildScannerContent() {
    switch (_status) {
      case ScannerViewStatus.scanning:
        if (widget.customScannerView != null) {
          return widget.customScannerView!;
        }
        return Stack(
          alignment: Alignment.center,
          children: [
            ClipRRect(
              borderRadius: BorderRadius.circular(16),
              child: SizedBox(
                width: 280,
                height: 280,
                child: MobileScanner(
                  controller: _controller,
                  onDetect: (BarcodeCapture capture) {
                    if (_status != ScannerViewStatus.scanning) return;
                    for (final barcode in capture.barcodes) {
                      final raw = barcode.rawValue;
                      if (raw != null && raw.isNotEmpty) {
                        _processScannedToken(raw);
                        break;
                      }
                    }
                  },
                  errorBuilder: (context, error) {
                    return Container(
                      color: Colors.black87,
                      padding: const EdgeInsets.all(16),
                      child: Center(
                        child: Text(
                          'Camera error: ${error.errorCode.name}',
                          textAlign: TextAlign.center,
                          style: const TextStyle(
                              color: Colors.white70, fontSize: 13),
                        ),
                      ),
                    );
                  },
                ),
              ),
            ),
            IgnorePointer(
              child: Container(
                width: 280,
                height: 280,
                decoration: BoxDecoration(
                  border: Border.all(color: Colors.blueAccent, width: 3),
                  borderRadius: BorderRadius.circular(16),
                ),
              ),
            ),
          ],
        );

      case ScannerViewStatus.submitting:
        return const Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            CircularProgressIndicator(color: Colors.blueAccent),
            SizedBox(height: 24),
            Text(
              'Verifying Presence Evidence...',
              style: TextStyle(
                  color: Colors.white,
                  fontSize: 16,
                  fontWeight: FontWeight.w600),
            ),
          ],
        );

      case ScannerViewStatus.success:
        final factorsStr = _result?.verifiedFactors.isNotEmpty == true
            ? _result!.verifiedFactors.join(' + ')
            : 'Verified';
        return Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(Icons.check_circle, size: 80, color: Colors.green),
            const SizedBox(height: 16),
            Text(
              '${_result?.checkpointType} Checkpoint Credited!',
              style: const TextStyle(
                  color: Colors.white,
                  fontSize: 18,
                  fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 8),
            Text(
              'Presence verified via $factorsStr.',
              textAlign: TextAlign.center,
              style: const TextStyle(color: Colors.white70, fontSize: 13),
            ),
            const SizedBox(height: 24),
            ElevatedButton(
              onPressed: () => Navigator.of(context).maybePop(),
              style: ElevatedButton.styleFrom(backgroundColor: Colors.green),
              child: const Text('Done', style: TextStyle(color: Colors.white)),
            ),
          ],
        );

      case ScannerViewStatus.alreadyCredited:
        return Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(Icons.verified, size: 80, color: Colors.blueAccent),
            const SizedBox(height: 16),
            Text(
              '${_result?.checkpointType} Already Recorded',
              style: const TextStyle(
                  color: Colors.white,
                  fontSize: 18,
                  fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 8),
            const Text(
              'You have already received credit for this checkpoint window.',
              textAlign: TextAlign.center,
              style: TextStyle(color: Colors.white70, fontSize: 13),
            ),
            const SizedBox(height: 24),
            ElevatedButton(
              onPressed: () => Navigator.of(context).maybePop(),
              style:
                  ElevatedButton.styleFrom(backgroundColor: Colors.blueAccent),
              child: const Text('Done', style: TextStyle(color: Colors.white)),
            ),
          ],
        );

      case ScannerViewStatus.offlineRecorded:
        return Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(Icons.cloud_upload_outlined,
                size: 80, color: Colors.amberAccent),
            const SizedBox(height: 16),
            const Text(
              'Locally Recorded',
              style: TextStyle(
                  color: Colors.white,
                  fontSize: 18,
                  fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 8),
            const Padding(
              padding: EdgeInsets.symmetric(horizontal: 16),
              child: Text(
                'Offline attendance evidence stored in outbox. Official credit will be confirmed after server synchronization.',
                textAlign: TextAlign.center,
                style: TextStyle(color: Colors.white70, fontSize: 13),
              ),
            ),
            const SizedBox(height: 24),
            ElevatedButton(
              onPressed: () => Navigator.of(context).maybePop(),
              style: ElevatedButton.styleFrom(
                  backgroundColor: Colors.amber.shade800),
              child: const Text('Done', style: TextStyle(color: Colors.white)),
            ),
          ],
        );

      case ScannerViewStatus.error:
        return Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(Icons.error_outline, size: 80, color: Colors.redAccent),
            const SizedBox(height: 16),
            const Text(
              'Check-In Failed',
              style: TextStyle(
                  color: Colors.redAccent,
                  fontSize: 18,
                  fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 8),
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16),
              child: Text(
                _errorMessage ?? 'Verification failed.',
                textAlign: TextAlign.center,
                style: const TextStyle(color: Colors.white70, fontSize: 13),
              ),
            ),
            const SizedBox(height: 24),
            ElevatedButton.icon(
              onPressed: _resetScanner,
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
}
