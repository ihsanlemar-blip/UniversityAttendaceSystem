import 'dart:convert';
import 'dart:io';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../core/api_client.dart';
import '../services/device_key_service.dart';

final deviceKeyServiceProvider = Provider<DeviceKeyService>((ref) {
  return DeviceKeyService();
});

/// Screen allowing student to view device trust status and manage primary device registration.
class StudentDeviceSecurityScreen extends ConsumerStatefulWidget {
  final ApiClient apiClient;
  final String? authToken;
  final String? universityId;
  final String? userId;

  const StudentDeviceSecurityScreen({
    super.key,
    required this.apiClient,
    this.authToken,
    this.universityId,
    this.userId,
  });

  @override
  ConsumerState<StudentDeviceSecurityScreen> createState() =>
      _StudentDeviceSecurityScreenState();
}

class _StudentDeviceSecurityScreenState
    extends ConsumerState<StudentDeviceSecurityScreen> {
  bool _isLoading = true;
  String _deviceStatus = 'UNREGISTERED';
  String? _deviceId;
  String? _shortFingerprint;
  String? _fullFingerprint;
  String? _registrationDate;

  @override
  void initState() {
    super.initState();
    _loadDeviceState();
  }

  Future<void> _loadDeviceState() async {
    setState(() {
      _isLoading = true;
    });

    final keyService = ref.read(deviceKeyServiceProvider);
    await keyService.ensureKeyPair();

    final status = await keyService.getDeviceStatus();
    final devId = await keyService.getDeviceId();
    final shortFp = await keyService.getShortFingerprint();
    final fullFp = await keyService.getPublicKeyFingerprint();
    final regDate = await keyService.getRegistrationDate();

    if (mounted) {
      setState(() {
        _deviceStatus = status;
        _deviceId = devId;
        _shortFingerprint = shortFp;
        _fullFingerprint = fullFp;
        _registrationDate = regDate;
        _isLoading = false;
      });
    }
  }

  Future<void> _handleInitialRegistration() async {
    if (widget.authToken == null || widget.userId == null || widget.universityId == null) {
      _showSnackbar('Authentication required to register device.', isError: true);
      return;
    }

    setState(() => _isLoading = true);

    try {
      final keyService = ref.read(deviceKeyServiceProvider);
      await keyService.ensureKeyPair();
      final pubKeyPem = await keyService.getPublicKeyPem();
      final fingerprint = await keyService.getPublicKeyFingerprint();

      if (pubKeyPem == null || fingerprint == null) {
        throw Exception('Failed to access device cryptographic keypair.');
      }

      // 1. Request registration challenge from server
      final challengeUri = Uri.parse('${widget.apiClient.baseUrl}/api/v1/devices/challenges');
      final client = HttpClient();
      final challengeReq = await client.postUrl(challengeUri);
      challengeReq.headers.set(HttpHeaders.authorizationHeader, 'Bearer ${widget.authToken}');
      challengeReq.headers.set(HttpHeaders.contentTypeHeader, 'application/json');
      challengeReq.write(jsonEncode({
        'candidate_public_key': pubKeyPem,
      }));
      final challengeResp = await challengeReq.close();
      final challengeBody = await challengeResp.transform(utf8.decoder).join();

      if (challengeResp.statusCode != 200 && challengeResp.statusCode != 201) {
        final decodedErr = jsonDecode(challengeBody);
        throw Exception(decodedErr['detail'] ?? 'Failed to obtain registration challenge.');
      }

      final challengeData = jsonDecode(challengeBody)['data'];
      final challengeId = challengeData['challenge_id'] as String;
      final nonce = challengeData['nonce'] as String;
      final issuedAt = challengeData['issued_at'] as String;
      final expiresAt = challengeData['expires_at'] as String;

      // 2. Sign canonical challenge
      final signature = await keyService.signRegistrationChallenge(
        challengeId: challengeId,
        universityId: widget.universityId!,
        userId: widget.userId!,
        candidateFingerprint: fingerprint,
        nonce: nonce,
        issuedAtUtcIso: issuedAt,
        expiresAtUtcIso: expiresAt,
      );

      // 3. Submit confirmation to server
      final confirmUri = Uri.parse('${widget.apiClient.baseUrl}/api/v1/devices/register');
      final confirmReq = await client.postUrl(confirmUri);
      confirmReq.headers.set(HttpHeaders.authorizationHeader, 'Bearer ${widget.authToken}');
      confirmReq.headers.set(HttpHeaders.contentTypeHeader, 'application/json');
      confirmReq.write(jsonEncode({
        'challenge_id': challengeId,
        'proof_signature': signature,
        'platform': 'android',
        'device_label': 'Student Primary Mobile Phone',
        'app_version': '1.0.0',
      }));
      final confirmResp = await confirmReq.close();
      final confirmBody = await confirmResp.transform(utf8.decoder).join();

      if (confirmResp.statusCode != 200 && confirmResp.statusCode != 201) {
        final decodedErr = jsonDecode(confirmBody);
        throw Exception(decodedErr['detail'] ?? 'Failed to activate device.');
      }

      final confirmData = jsonDecode(confirmBody)['data'];
      final activatedDeviceId = confirmData['id'] as String;
      final activatedStatus = confirmData['status'] as String;
      final activatedAt = confirmData['activated_at'] as String?;

      await keyService.setDeviceId(activatedDeviceId);
      await keyService.setDeviceStatus(activatedStatus);
      if (activatedAt != null) {
        await keyService.setRegistrationDate(activatedAt);
      }

      _showSnackbar('Primary attendance device activated successfully!');
      await _loadDeviceState();
    } catch (e) {
      _showSnackbar(e.toString().replaceAll('Exception: ', ''), isError: true);
    } finally {
      if (mounted) {
        setState(() => _isLoading = false);
      }
    }
  }

  Future<void> _handleReportLost() async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Report Device Lost / Stolen'),
        content: const Text(
          'Are you sure you want to mark this device as lost or stolen? '
          'This will immediately revoke its authorization for attendance check-ins.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx, false),
            child: const Text('Cancel'),
          ),
          ElevatedButton(
            style: ElevatedButton.styleFrom(backgroundColor: Colors.red),
            onPressed: () => Navigator.pop(ctx, true),
            child: const Text('Confirm Revocation', style: TextStyle(color: Colors.white)),
          ),
        ],
      ),
    );

    if (confirmed != true) return;

    setState(() => _isLoading = true);
    try {
      final uri = Uri.parse('${widget.apiClient.baseUrl}/api/v1/devices/me/report-lost');
      final client = HttpClient();
      final req = await client.postUrl(uri);
      req.headers.set(HttpHeaders.authorizationHeader, 'Bearer ${widget.authToken}');
      final resp = await req.close();

      if (resp.statusCode == 200) {
        final keyService = ref.read(deviceKeyServiceProvider);
        await keyService.setDeviceStatus('REVOKED');
        _showSnackbar('Device reported lost. Attendance access revoked.');
        await _loadDeviceState();
      } else {
        throw Exception('Failed to report device lost on server.');
      }
    } catch (e) {
      _showSnackbar(e.toString().replaceAll('Exception: ', ''), isError: true);
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  void _showSnackbar(String message, {bool isError = false}) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(message),
        backgroundColor: isError ? Colors.red.shade700 : Colors.green.shade700,
      ),
    );
  }

  Color _getStatusBadgeColor(String status) {
    switch (status.toUpperCase()) {
      case 'ACTIVE':
        return Colors.green;
      case 'PENDING_REGISTRATION':
        return Colors.amber.shade800;
      case 'SUSPENDED':
      case 'REVOKED':
        return Colors.red;
      case 'REPLACED':
        return Colors.blueGrey;
      default:
        return Colors.grey;
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Device Security & Trust'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: _isLoading ? null : _loadDeviceState,
          ),
        ],
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : ListView(
              padding: const EdgeInsets.all(16.0),
              children: [
                _buildStatusCard(),
                const SizedBox(height: 16),
                _buildFingerprintCard(),
                const SizedBox(height: 24),
                _buildActionButtons(),
              ],
            ),
    );
  }

  Widget _buildStatusCard() {
    final statusColor = _getStatusBadgeColor(_deviceStatus);
    return Card(
      elevation: 2,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                const Text(
                  'Primary Attendance Device',
                  style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
                ),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                  decoration: BoxDecoration(
                    color: statusColor.withAlpha(38),
                    borderRadius: BorderRadius.circular(20),
                    border: Border.all(color: statusColor),
                  ),
                  child: Text(
                    _deviceStatus,
                    style: TextStyle(
                      color: statusColor,
                      fontWeight: FontWeight.bold,
                      fontSize: 12,
                    ),
                  ),
                ),
              ],
            ),
            const Divider(height: 24),
            if (_deviceId != null) ...[
              Text(
                'Device ID: $_deviceId',
                style: const TextStyle(fontSize: 12, color: Colors.grey),
              ),
              const SizedBox(height: 4),
            ],
            if (_registrationDate != null) ...[
              Text(
                'Activated: $_registrationDate',
                style: const TextStyle(fontSize: 12, color: Colors.grey),
              ),
              const SizedBox(height: 4),
            ],
            const SizedBox(height: 8),
            const Text(
              'Only your registered primary phone can sign attendance proofs. '
              'The server validates your device cryptography before granting checkpoint credit.',
              style: TextStyle(fontSize: 13),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildFingerprintCard() {
    return Card(
      elevation: 2,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Cryptographic Fingerprint (SHA-256)',
              style: TextStyle(fontSize: 14, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 8),
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: Colors.grey.shade100,
                borderRadius: BorderRadius.circular(8),
              ),
              child: Row(
                children: [
                  Expanded(
                    child: Text(
                      _shortFingerprint ?? 'No Keypair Generated',
                      style: const TextStyle(
                        fontFamily: 'monospace',
                        fontWeight: FontWeight.w600,
                        fontSize: 14,
                      ),
                    ),
                  ),
                  if (_fullFingerprint != null)
                    IconButton(
                      icon: const Icon(Icons.copy, size: 20),
                      onPressed: () {
                        Clipboard.setData(ClipboardData(text: _fullFingerprint!));
                        _showSnackbar('Full fingerprint copied to clipboard.');
                      },
                    ),
                ],
              ),
            ),
            const SizedBox(height: 8),
            const Text(
              'Ed25519 private key is held exclusively in this phone\'s hardware-backed keystore.',
              style: TextStyle(fontSize: 12, color: Colors.grey),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildActionButtons() {
    if (_deviceStatus == 'UNREGISTERED') {
      return ElevatedButton.icon(
        icon: const Icon(Icons.phonelink_lock),
        label: const Text('Register This Phone As Primary Device'),
        style: ElevatedButton.styleFrom(
          padding: const EdgeInsets.symmetric(vertical: 14),
          backgroundColor: Colors.indigo,
          foregroundColor: Colors.white,
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
        ),
        onPressed: _isLoading ? null : _handleInitialRegistration,
      );
    }

    if (_deviceStatus == 'ACTIVE') {
      return Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          OutlinedButton.icon(
            icon: const Icon(Icons.report_problem, color: Colors.red),
            label: const Text('Report Lost or Stolen', style: TextStyle(color: Colors.red)),
            style: OutlinedButton.styleFrom(
              padding: const EdgeInsets.symmetric(vertical: 12),
              side: const BorderSide(color: Colors.red),
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
            ),
            onPressed: _isLoading ? null : _handleReportLost,
          ),
        ],
      );
    }

    return const SizedBox.shrink();
  }
}
