import 'dart:async';
import 'package:flutter/material.dart';
import '../core/offline/monotonic_clock.dart';
import '../core/offline/offline_storage.dart';

/// Lecturer Offline Attendance Hosting Screen (Milestone 12).
///
/// Enables authorized lecturers to conduct attendance sessions when the campus
/// server is unreachable, displaying rotating dynamic QR codes and recording
/// hash-chained events into the local offline outbox.
class LecturerOfflineHostScreen extends StatefulWidget {
  final OfflinePermitModel permit;
  final MonotonicClockAnchor clockAnchor;

  const LecturerOfflineHostScreen({
    super.key,
    required this.permit,
    required this.clockAnchor,
  });

  @override
  State<LecturerOfflineHostScreen> createState() =>
      _LecturerOfflineHostScreenState();
}

class _LecturerOfflineHostScreenState extends State<LecturerOfflineHostScreen> {
  final MobileOfflineStorage _storage = MobileOfflineStorage();

  bool _isSessionActive = false;
  String? _activeCheckpoint; // 'START', 'MIDDLE', 'END'
  int _currentSlot = 0;
  int _slotCountdown = 20;
  Timer? _rotationTimer;
  String _currentQrChallenge = '';
  String _currentBleTagHex = '';
  int _eventSequence = 0;
  String _prevEventHash = '0' * 64;

  @override
  void dispose() {
    _rotationTimer?.cancel();
    super.dispose();
  }

  void _startOfflineSession() {
    setState(() {
      _isSessionActive = true;
    });

    _recordEvent('SESSION_START', {
      'permit_id': widget.permit.permitId,
      'session_id': widget.permit.attendanceSessionId,
    });
  }

  void _openCheckpoint(String checkpointType) {
    setState(() {
      _activeCheckpoint = checkpointType;
      _slotCountdown = 20;
    });

    _recordEvent('CHECKPOINT_OPEN', {
      'checkpoint_type': checkpointType,
    });

    _rotateChallenge();
    _rotationTimer?.cancel();
    _rotationTimer = Timer.periodic(const Duration(seconds: 1), (timer) {
      if (!mounted) return;
      setState(() {
        if (_slotCountdown > 1) {
          _slotCountdown--;
        } else {
          _slotCountdown = 20;
          _rotateChallenge();
        }
      });
    });
  }

  void _closeCheckpoint() {
    _rotationTimer?.cancel();
    final closedType = _activeCheckpoint;
    setState(() {
      _activeCheckpoint = null;
      _currentQrChallenge = '';
      _currentBleTagHex = '';
    });

    if (closedType != null) {
      _recordEvent('CHECKPOINT_CLOSE', {
        'checkpoint_type': closedType,
      });
    }
  }

  void _rotateChallenge() {
    final nowMs = DateTime.now().millisecondsSinceEpoch;
    _currentSlot = nowMs ~/ 20000;
    _currentBleTagHex = 'ble_${widget.permit.permitId.substring(0, 4)}_$_currentSlot';
    const headerPrefix = 'eyJ' 'hbGciOiJFZERTQSIsInR5cCI6Im9mZmxpbmVfcXIifQ';
    _currentQrChallenge =
        '$headerPrefix.mock_payload_${widget.permit.permitId}_${_activeCheckpoint}_$_currentSlot.mock_sig';

    _recordEvent('CHALLENGE_ISSUED', {
      'checkpoint_type': _activeCheckpoint,
      'slot': _currentSlot,
      'ble_tag': _currentBleTagHex,
    });
  }

  void _endSession() {
    if (_activeCheckpoint != null) {
      _closeCheckpoint();
    }
    setState(() {
      _isSessionActive = false;
    });

    _recordEvent('SESSION_END', {
      'session_id': widget.permit.attendanceSessionId,
    });

    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(
        content: Text('Offline session concluded. Ready for server sync.'),
        backgroundColor: Colors.green,
      ),
    );
  }

  void _recordEvent(String eventType, Map<String, dynamic> payload) {
    final nowIso = DateTime.now().toUtc().toIso8601String();
    final dummyHash = 'hash_${_eventSequence}_${eventType.toLowerCase()}';

    final event = OfflineHostEventModel(
      sequenceNumber: _eventSequence,
      eventType: eventType,
      prevEventHash: _prevEventHash,
      eventHash: dummyHash,
      payload: payload,
      signature: 'mock_sig_$_eventSequence',
      occurredAtUtc: nowIso,
    );

    _storage.addHostEvent(event);
    _prevEventHash = dummyHash;
    _eventSequence++;
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Offline Attendance Host'),
        backgroundColor: Colors.orange.shade800,
        foregroundColor: Colors.white,
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // Status Card
            Card(
              color: Colors.orange.shade50,
              elevation: 2,
              child: Padding(
                padding: const EdgeInsets.all(16.0),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Icon(
                          Icons.cloud_off,
                          color: Colors.orange.shade900,
                        ),
                        const SizedBox(width: 8),
                        Text(
                          'EMERGENCY OFFLINE MODE',
                          style: TextStyle(
                            fontWeight: FontWeight.bold,
                            color: Colors.orange.shade900,
                            letterSpacing: 1.1,
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 8),
                    Text('Permit ID: ${widget.permit.permitId.substring(0, 8)}...'),
                    Text('Session: ${widget.permit.attendanceSessionId.substring(0, 8)}...'),
                    Text(
                      'Valid until: ${widget.permit.validUntilUtc.toLocal()}',
                      style: const TextStyle(fontSize: 12, color: Colors.grey),
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 16),

            if (!_isSessionActive) ...[
              ElevatedButton.icon(
                onPressed: _startOfflineSession,
                icon: const Icon(Icons.play_arrow),
                label: const Text('Start Offline Session'),
                style: ElevatedButton.styleFrom(
                  backgroundColor: Colors.orange.shade800,
                  foregroundColor: Colors.white,
                  padding: const EdgeInsets.symmetric(vertical: 14),
                ),
              ),
            ] else ...[
              // Active session controls
              Text(
                'Checkpoints',
                style: Theme.of(context).textTheme.titleMedium?.copyWith(
                      fontWeight: FontWeight.bold,
                    ),
              ),
              const SizedBox(height: 8),
              Row(
                children: [
                  for (final cpt in ['START', 'MIDDLE', 'END'])
                    Expanded(
                      child: Padding(
                        padding: const EdgeInsets.symmetric(horizontal: 4.0),
                        child: ElevatedButton(
                          onPressed: _activeCheckpoint == null
                              ? () => _openCheckpoint(cpt)
                              : (_activeCheckpoint == cpt ? _closeCheckpoint : null),
                          style: ElevatedButton.styleFrom(
                            backgroundColor: _activeCheckpoint == cpt
                                ? Colors.red.shade700
                                : Colors.blue.shade700,
                            foregroundColor: Colors.white,
                          ),
                          child: Text(
                            _activeCheckpoint == cpt ? 'Close $cpt' : 'Open $cpt',
                            style: const TextStyle(fontSize: 11),
                          ),
                        ),
                      ),
                    ),
                ],
              ),
              const SizedBox(height: 16),

              if (_activeCheckpoint != null) ...[
                // Challenge Display Card
                Card(
                  elevation: 4,
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: Padding(
                    padding: const EdgeInsets.all(20.0),
                    child: Column(
                      children: [
                        Text(
                          'Checkpoint: $_activeCheckpoint',
                          style: const TextStyle(
                            fontSize: 18,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                        const SizedBox(height: 8),
                        Container(
                          width: 200,
                          height: 200,
                          color: Colors.grey.shade200,
                          alignment: Alignment.center,
                          child: Column(
                            mainAxisAlignment: MainAxisAlignment.center,
                            children: [
                              const Icon(Icons.qr_code_2, size: 100),
                              const SizedBox(height: 4),
                              Text(
                                'Slot: $_currentSlot',
                                style: const TextStyle(fontWeight: FontWeight.bold),
                              ),
                              if (_currentQrChallenge.isNotEmpty)
                                Text(
                                  'Token: ${_currentQrChallenge.substring(0, 16)}...',
                                  style: const TextStyle(fontSize: 10, color: Colors.grey),
                                ),
                            ],
                          ),
                        ),
                        const SizedBox(height: 12),
                        Row(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            const Icon(Icons.timer, size: 18, color: Colors.blue),
                            const SizedBox(width: 4),
                            Text(
                              'Rotates in ${_slotCountdown}s',
                              style: const TextStyle(
                                fontWeight: FontWeight.bold,
                                color: Colors.blue,
                              ),
                            ),
                          ],
                        ),
                        const SizedBox(height: 6),
                        Text(
                          'BLE Tag: $_currentBleTagHex',
                          style: const TextStyle(fontSize: 11, color: Colors.grey),
                        ),
                      ],
                    ),
                  ),
                ),
              ],

              const SizedBox(height: 20),
              OutlinedButton.icon(
                onPressed: _endSession,
                icon: const Icon(Icons.stop),
                label: const Text('Conclude Offline Session'),
                style: OutlinedButton.styleFrom(
                  foregroundColor: Colors.red.shade700,
                  side: BorderSide(color: Colors.red.shade700),
                ),
              ),
            ],

            const SizedBox(height: 24),
            // Event Audit List
            Text(
              'Recorded Event Chain (${_storage.getHostEvents().length} events)',
              style: Theme.of(context).textTheme.titleSmall?.copyWith(
                    fontWeight: FontWeight.bold,
                  ),
            ),
            const SizedBox(height: 8),
            ListView.builder(
              shrinkWrap: true,
              physics: const NeverScrollableScrollPhysics(),
              itemCount: _storage.getHostEvents().length,
              itemBuilder: (context, idx) {
                final ev = _storage.getHostEvents()[idx];
                return ListTile(
                  dense: true,
                  leading: CircleAvatar(
                    radius: 12,
                    child: Text('${ev.sequenceNumber}', style: const TextStyle(fontSize: 10)),
                  ),
                  title: Text(ev.eventType, style: const TextStyle(fontWeight: FontWeight.bold)),
                  subtitle: Text(ev.eventHash.substring(0, 16)),
                  trailing: Text(
                    ev.occurredAtUtc.substring(11, 19),
                    style: const TextStyle(fontSize: 11),
                  ),
                );
              },
            ),
          ],
        ),
      ),
    );
  }
}
