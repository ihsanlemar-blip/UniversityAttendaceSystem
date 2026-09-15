import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import '../services/qr_checkin_service.dart';

enum ScannerViewStatus {
  scanning,
  submitting,
  success,
  alreadyCredited,
  error,
}

/// Mobile scanner screen for students to capture rotating classroom dynamic QR codes.
class StudentQrScannerScreen extends StatefulWidget {
  final QrCheckInService checkInService;
  final String authToken;
  final VoidCallback? onCompleted;
  final bool enableManualTokenEntry;

  const StudentQrScannerScreen({
    super.key,
    required this.checkInService,
    required this.authToken,
    this.onCompleted,
    this.enableManualTokenEntry = kDebugMode,
  });


  @override
  State<StudentQrScannerScreen> createState() => _StudentQrScannerScreenState();
}

class _StudentQrScannerScreenState extends State<StudentQrScannerScreen> {
  ScannerViewStatus _status = ScannerViewStatus.scanning;
  QrCheckInResult? _result;
  String? _errorMessage;
  final TextEditingController _manualTokenController = TextEditingController();

  @override
  void dispose() {
    _manualTokenController.dispose();
    super.dispose();
  }

  Future<void> _processScannedToken(String rawToken) async {
    final trimmed = rawToken.trim();
    if (trimmed.isEmpty) return;

    setState(() {
      _status = ScannerViewStatus.submitting;
      _errorMessage = null;
    });

    try {
      final result = await widget.checkInService.submitQrCheckIn(
        token: trimmed,
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
            // Instruction header
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 16),
              child: Text(
                _status == ScannerViewStatus.scanning
                    ? 'Align the rotating QR code on the classroom projector screen inside the frame.'
                    : 'Processing presence token...',
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
            if (_status == ScannerViewStatus.scanning && widget.enableManualTokenEntry)
              Padding(
                padding: const EdgeInsets.all(16.0),
                child: Column(
                  children: [
                    TextField(
                      controller: _manualTokenController,
                      style: const TextStyle(color: Colors.white),
                      decoration: InputDecoration(
                        hintText: '[DEV/TEST ONLY] Paste signed QR token string',
                        hintStyle: const TextStyle(color: Colors.white38),
                        filled: true,
                        fillColor: Colors.white10,
                        border: OutlineInputBorder(
                          borderRadius: BorderRadius.circular(8),
                          borderSide: BorderSide.none,
                        ),
                        suffixIcon: IconButton(
                          icon: const Icon(Icons.send, color: Colors.blueAccent),
                          onPressed: () => _processScannedToken(_manualTokenController.text),
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
        return Container(
          width: 280,
          height: 280,
          decoration: BoxDecoration(
            border: Border.all(color: Colors.blueAccent, width: 3),
            borderRadius: BorderRadius.circular(16),
          ),
          child: const Stack(
            alignment: Alignment.center,
            children: [
              Icon(Icons.qr_code_scanner, size: 80, color: Colors.white24),
              Positioned(
                bottom: 16,
                child: Text(
                  'Camera Active',
                  style: TextStyle(color: Colors.white54, fontSize: 12),
                ),
              ),
            ],
          ),
        );

      case ScannerViewStatus.submitting:
        return const Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            CircularProgressIndicator(color: Colors.blueAccent),
            SizedBox(height: 24),
            Text(
              'Verifying Presence Token...',
              style: TextStyle(color: Colors.white, fontSize: 16, fontWeight: FontWeight.w600),
            ),
          ],
        );

      case ScannerViewStatus.success:
        return Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(Icons.check_circle, size: 80, color: Colors.green),
            const SizedBox(height: 16),
            Text(
              '${_result?.checkpointType} Checkpoint Credited!',
              style: const TextStyle(color: Colors.white, fontSize: 18, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 8),
            const Text(
              'Attendance credit verified by university server.',
              style: TextStyle(color: Colors.white70, fontSize: 13),
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
              style: const TextStyle(color: Colors.white, fontSize: 18, fontWeight: FontWeight.bold),
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
              style: ElevatedButton.styleFrom(backgroundColor: Colors.blueAccent),
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
              style: TextStyle(color: Colors.redAccent, fontSize: 18, fontWeight: FontWeight.bold),
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
              label: const Text('Try Again', style: TextStyle(color: Colors.white)),
              style: ElevatedButton.styleFrom(backgroundColor: Colors.redAccent),
            ),
          ],
        );
    }
  }
}
