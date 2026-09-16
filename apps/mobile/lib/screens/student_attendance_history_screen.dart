import 'package:flutter/material.dart';
import '../services/attendance_operations_service.dart';

/// Screen allowing enrolled students to inspect their attendance history,
/// check correction eligibility, submit correction/excuse/leave requests,
/// view audit revision timelines, and cancel pending requests.
class StudentAttendanceHistoryScreen extends StatefulWidget {
  final AttendanceOperationsService operationsService;
  final String authToken;
  final String studentId;

  const StudentAttendanceHistoryScreen({
    super.key,
    required this.operationsService,
    required this.authToken,
    required this.studentId,
  });

  @override
  State<StudentAttendanceHistoryScreen> createState() =>
      _StudentAttendanceHistoryScreenState();
}

class _StudentAttendanceHistoryScreenState
    extends State<StudentAttendanceHistoryScreen>
    with SingleTickerProviderStateMixin {
  late final TabController _tabController;
  bool _isLoading = true;
  String? _errorMessage;
  String? _successMessage;

  // Requests state
  List<CorrectionRequestModel> _corrections = [];
  List<ExcuseRequestModel> _excuses = [];
  List<LeaveRequestModel> _leaves = [];

  // Sample student attendance sessions for demonstration
  final List<Map<String, dynamic>> _sampleRecords = [
    {
      'record_id': '0192323e-6708-724a-a43b-8106daee8611',
      'course_code': 'CS301',
      'course_title': 'Operating Systems',
      'date': 'Yesterday',
      'status': 'ABSENT',
      'credit': 0.0,
      'is_manual': false,
      'session_id': '0192323e-6708-724a-a43b-8106daee8622',
      'occurrence_id': '0192323e-6708-724a-a43b-8106daee8633',
    },
    {
      'record_id': '0192323e-6708-724a-a43b-8106daee8612',
      'course_code': 'CS302',
      'course_title': 'Database Systems',
      'date': '2 days ago',
      'status': 'LATE',
      'credit': 0.5,
      'is_manual': false,
      'session_id': '0192323e-6708-724a-a43b-8106daee8624',
      'occurrence_id': '0192323e-6708-724a-a43b-8106daee8635',
    },
    {
      'record_id': '0192323e-6708-724a-a43b-8106daee8613',
      'course_code': 'CS303',
      'course_title': 'Computer Networks',
      'date': 'Last week',
      'status': 'PRESENT',
      'credit': 1.0,
      'is_manual': false,
      'session_id': '0192323e-6708-724a-a43b-8106daee8626',
      'occurrence_id': '0192323e-6708-724a-a43b-8106daee8637',
    },
  ];

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 2, vsync: this);
    _loadRequests();
  }

  @override
  void dispose() {
    _tabController.dispose();
    super.dispose();
  }

  Future<void> _loadRequests() async {
    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });

    try {
      final corrections = await widget.operationsService
          .getMyCorrections(authToken: widget.authToken);
      final excuses = await widget.operationsService
          .getMyExcuses(authToken: widget.authToken);
      final leaves = await widget.operationsService
          .getMyLeaves(authToken: widget.authToken);

      if (mounted) {
        setState(() {
          _corrections = corrections;
          _excuses = excuses;
          _leaves = leaves;
          _isLoading = false;
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _errorMessage = e.toString();
          _isLoading = false;
        });
      }
    }
  }

  void _showCorrectionDialog(Map<String, dynamic> record) {
    final recordId = record['record_id'] as String;
    String requestType = 'TECHNICAL_ISSUE';
    String requestedStatus = 'PRESENT';
    final reasonController = TextEditingController();
    final noteController = TextEditingController();
    bool isSubmitting = false;

    showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (ctx) {
        return StatefulBuilder(
          builder: (context, setModalState) {
            return Padding(
              padding: EdgeInsets.only(
                left: 20,
                right: 20,
                top: 20,
                bottom: MediaQuery.of(context).viewInsets.bottom + 20,
              ),
              child: SingleChildScrollView(
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        Text(
                          'Request Attendance Correction',
                          style:
                              Theme.of(context).textTheme.titleMedium?.copyWith(
                                    fontWeight: FontWeight.bold,
                                  ),
                        ),
                        IconButton(
                          icon: const Icon(Icons.close),
                          onPressed: () => Navigator.pop(ctx),
                        ),
                      ],
                    ),
                    const SizedBox(height: 8),
                    Container(
                      padding: const EdgeInsets.all(12),
                      decoration: BoxDecoration(
                        color: Colors.indigo.shade50,
                        borderRadius: BorderRadius.circular(8),
                      ),
                      child: Text(
                        'Record: ${record['course_code']} (${record['date']})\nCurrent Status: ${record['status']}',
                        style: TextStyle(
                            fontSize: 12, color: Colors.indigo.shade900),
                      ),
                    ),
                    const SizedBox(height: 16),
                    DropdownButtonFormField<String>(
                      initialValue: requestType,
                      decoration: const InputDecoration(
                        labelText: 'Correction Type',
                        border: OutlineInputBorder(),
                      ),
                      items: const [
                        DropdownMenuItem(
                          value: 'TECHNICAL_ISSUE',
                          child: Text('Technical Issue (BLE/Camera)'),
                        ),
                        DropdownMenuItem(
                          value: 'MEDICAL_REASON',
                          child: Text('Medical Emergency'),
                        ),
                        DropdownMenuItem(
                          value: 'OFFICIAL_ACTIVITY',
                          child: Text('University Official Activity'),
                        ),
                        DropdownMenuItem(
                          value: 'OTHER',
                          child: Text('Other Justification'),
                        ),
                      ],
                      onChanged: (val) {
                        if (val != null) setModalState(() => requestType = val);
                      },
                    ),
                    const SizedBox(height: 12),
                    DropdownButtonFormField<String>(
                      initialValue: requestedStatus,
                      decoration: const InputDecoration(
                        labelText: 'Requested Status',
                        border: OutlineInputBorder(),
                      ),
                      items: const [
                        DropdownMenuItem(
                            value: 'PRESENT', child: Text('PRESENT (1.0 cr)')),
                        DropdownMenuItem(
                            value: 'LATE', child: Text('LATE (0.5 cr)')),
                        DropdownMenuItem(
                            value: 'EXCUSED',
                            child: Text('EXCUSED (Policy cr)')),
                      ],
                      onChanged: (val) {
                        if (val != null) {
                          setModalState(() => requestedStatus = val);
                        }
                      },
                    ),
                    const SizedBox(height: 12),
                    TextField(
                      controller: reasonController,
                      maxLines: 2,
                      decoration: const InputDecoration(
                        labelText: 'Reason for correction *',
                        border: OutlineInputBorder(),
                      ),
                    ),
                    const SizedBox(height: 12),
                    TextField(
                      controller: noteController,
                      maxLines: 2,
                      decoration: const InputDecoration(
                        labelText: 'Supporting Notes / Context (Optional)',
                        border: OutlineInputBorder(),
                      ),
                    ),
                    const SizedBox(height: 16),
                    ElevatedButton(
                      style: ElevatedButton.styleFrom(
                        backgroundColor: Colors.indigo,
                        foregroundColor: Colors.white,
                        padding: const EdgeInsets.symmetric(vertical: 14),
                      ),
                      onPressed: isSubmitting
                          ? null
                          : () async {
                              final reason = reasonController.text.trim();
                              if (reason.length < 3) {
                                ScaffoldMessenger.of(context).showSnackBar(
                                  const SnackBar(
                                      content: Text(
                                          'Please enter a valid reason (3+ chars).')),
                                );
                                return;
                              }

                              final messenger = ScaffoldMessenger.of(context);
                              final navigator = Navigator.of(ctx);
                              setModalState(() => isSubmitting = true);
                              try {
                                await widget.operationsService
                                    .submitCorrectionRequest(
                                  recordId: recordId,
                                  requestType: requestType,
                                  requestedStatus: requestedStatus,
                                  reason: reason,
                                  supportingNote:
                                      noteController.text.trim().isNotEmpty
                                          ? noteController.text.trim()
                                          : null,
                                  authToken: widget.authToken,
                                );
                                if (mounted) {
                                  navigator.pop();
                                  setState(() {
                                    _successMessage =
                                        'Correction request submitted successfully.';
                                  });
                                  _loadRequests();
                                }
                              } catch (e) {
                                setModalState(() => isSubmitting = false);
                                messenger.showSnackBar(
                                  SnackBar(content: Text('Error: $e')),
                                );
                              }
                            },
                      child: isSubmitting
                          ? const CircularProgressIndicator(color: Colors.white)
                          : const Text('Submit Correction Request'),
                    ),
                  ],
                ),
              ),
            );
          },
        );
      },
    );
  }

  void _showExcuseDialog(Map<String, dynamic> record) {
    String category = 'MEDICAL';
    final descController = TextEditingController();
    final docRefController = TextEditingController();
    bool isSubmitting = false;

    showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (ctx) {
        return StatefulBuilder(
          builder: (context, setModalState) {
            return Padding(
              padding: EdgeInsets.only(
                left: 20,
                right: 20,
                top: 20,
                bottom: MediaQuery.of(context).viewInsets.bottom + 20,
              ),
              child: SingleChildScrollView(
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        Text(
                          'Submit Absence Excuse',
                          style:
                              Theme.of(context).textTheme.titleMedium?.copyWith(
                                    fontWeight: FontWeight.bold,
                                  ),
                        ),
                        IconButton(
                          icon: const Icon(Icons.close),
                          onPressed: () => Navigator.pop(ctx),
                        ),
                      ],
                    ),
                    const SizedBox(height: 16),
                    DropdownButtonFormField<String>(
                      initialValue: category,
                      decoration: const InputDecoration(
                        labelText: 'Excuse Category',
                        border: OutlineInputBorder(),
                      ),
                      items: const [
                        DropdownMenuItem(
                            value: 'MEDICAL', child: Text('Medical Absence')),
                        DropdownMenuItem(
                            value: 'OFFICIAL_ACTIVITY',
                            child: Text('Official University Activity')),
                        DropdownMenuItem(
                            value: 'BEREAVEMENT', child: Text('Bereavement')),
                        DropdownMenuItem(
                            value: 'EMERGENCY',
                            child: Text('Family Emergency')),
                        DropdownMenuItem(value: 'OTHER', child: Text('Other')),
                      ],
                      onChanged: (val) {
                        if (val != null) setModalState(() => category = val);
                      },
                    ),
                    const SizedBox(height: 12),
                    TextField(
                      controller: descController,
                      maxLines: 3,
                      decoration: const InputDecoration(
                        labelText: 'Description / Details *',
                        border: OutlineInputBorder(),
                      ),
                    ),
                    const SizedBox(height: 12),
                    TextField(
                      controller: docRefController,
                      decoration: const InputDecoration(
                        labelText: 'Document Reference / ID (Optional)',
                        border: OutlineInputBorder(),
                      ),
                    ),
                    const SizedBox(height: 16),
                    ElevatedButton(
                      style: ElevatedButton.styleFrom(
                        backgroundColor: Colors.blue.shade700,
                        foregroundColor: Colors.white,
                        padding: const EdgeInsets.symmetric(vertical: 14),
                      ),
                      onPressed: isSubmitting
                          ? null
                          : () async {
                              final desc = descController.text.trim();
                              if (desc.length < 5) {
                                ScaffoldMessenger.of(context).showSnackBar(
                                  const SnackBar(
                                      content: Text(
                                          'Please enter a description (5+ chars).')),
                                );
                                return;
                              }

                              final messenger = ScaffoldMessenger.of(context);
                              final navigator = Navigator.of(ctx);
                              setModalState(() => isSubmitting = true);
                              try {
                                await widget.operationsService
                                    .submitExcuseRequest(
                                  attendanceRecordId:
                                      record['record_id'] as String?,
                                  attendanceSessionId:
                                      record['session_id'] as String?,
                                  classOccurrenceId:
                                      record['occurrence_id'] as String?,
                                  category: category,
                                  description: desc,
                                  documentReference:
                                      docRefController.text.trim().isNotEmpty
                                          ? docRefController.text.trim()
                                          : null,
                                  authToken: widget.authToken,
                                );
                                if (mounted) {
                                  navigator.pop();
                                  setState(() {
                                    _successMessage =
                                        'Absence excuse submitted successfully.';
                                  });
                                  _loadRequests();
                                }
                              } catch (e) {
                                setModalState(() => isSubmitting = false);
                                messenger.showSnackBar(
                                  SnackBar(content: Text('Error: $e')),
                                );
                              }
                            },
                      child: isSubmitting
                          ? const CircularProgressIndicator(color: Colors.white)
                          : const Text('Submit Excuse'),
                    ),
                  ],
                ),
              ),
            );
          },
        );
      },
    );
  }

  void _showLeaveDialog(Map<String, dynamic> record) {
    final reasonController = TextEditingController();
    bool isSubmitting = false;

    showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (ctx) {
        return StatefulBuilder(
          builder: (context, setModalState) {
            return Padding(
              padding: EdgeInsets.only(
                left: 20,
                right: 20,
                top: 20,
                bottom: MediaQuery.of(context).viewInsets.bottom + 20,
              ),
              child: SingleChildScrollView(
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        Text(
                          'Submit Pre-Class Leave Request',
                          style:
                              Theme.of(context).textTheme.titleMedium?.copyWith(
                                    fontWeight: FontWeight.bold,
                                  ),
                        ),
                        IconButton(
                          icon: const Icon(Icons.close),
                          onPressed: () => Navigator.pop(ctx),
                        ),
                      ],
                    ),
                    const SizedBox(height: 8),
                    Container(
                      padding: const EdgeInsets.all(12),
                      decoration: BoxDecoration(
                        color: Colors.amber.shade50,
                        border: Border.all(color: Colors.amber.shade300),
                        borderRadius: BorderRadius.circular(8),
                      ),
                      child: Text(
                        'Important Policy Notice (Section 38):\nApproved leave grants status "LEAVE" with 0.00 credit. It excuses absence but does NOT grant checkpoint attendance credit.',
                        style: TextStyle(
                            fontSize: 12,
                            color: Colors.amber.shade900,
                            fontWeight: FontWeight.w500),
                      ),
                    ),
                    const SizedBox(height: 16),
                    TextField(
                      controller: reasonController,
                      maxLines: 3,
                      decoration: const InputDecoration(
                        labelText: 'Reason for Leave *',
                        border: OutlineInputBorder(),
                      ),
                    ),
                    const SizedBox(height: 16),
                    ElevatedButton(
                      style: ElevatedButton.styleFrom(
                        backgroundColor: Colors.purple.shade700,
                        foregroundColor: Colors.white,
                        padding: const EdgeInsets.symmetric(vertical: 14),
                      ),
                      onPressed: isSubmitting
                          ? null
                          : () async {
                              final reason = reasonController.text.trim();
                              if (reason.length < 5) {
                                ScaffoldMessenger.of(context).showSnackBar(
                                  const SnackBar(
                                      content: Text(
                                          'Please enter a valid reason (5+ chars).')),
                                );
                                return;
                              }

                              final messenger = ScaffoldMessenger.of(context);
                              final navigator = Navigator.of(ctx);
                              setModalState(() => isSubmitting = true);
                              try {
                                await widget.operationsService
                                    .submitLeaveRequest(
                                  classOccurrenceId:
                                      record['occurrence_id'] as String,
                                  reason: reason,
                                  authToken: widget.authToken,
                                );
                                if (mounted) {
                                  navigator.pop();
                                  setState(() {
                                    _successMessage =
                                        'Leave request submitted successfully.';
                                  });
                                  _loadRequests();
                                }
                              } catch (e) {
                                setModalState(() => isSubmitting = false);
                                messenger.showSnackBar(
                                  SnackBar(content: Text('Error: $e')),
                                );
                              }
                            },
                      child: isSubmitting
                          ? const CircularProgressIndicator(color: Colors.white)
                          : const Text('Submit Leave Request'),
                    ),
                  ],
                ),
              ),
            );
          },
        );
      },
    );
  }

  void _showTimeline(String recordId) async {
    showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (ctx) {
        return FutureBuilder<RecordTimelineModel>(
          future: widget.operationsService.getRecordTimeline(
            recordId: recordId,
            authToken: widget.authToken,
          ),
          builder: (context, snapshot) {
            if (snapshot.connectionState == ConnectionState.waiting) {
              return const SizedBox(
                height: 250,
                child: Center(child: CircularProgressIndicator()),
              );
            }

            if (snapshot.hasError) {
              return Padding(
                padding: const EdgeInsets.all(24),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    const Icon(Icons.error_outline,
                        color: Colors.red, size: 40),
                    const SizedBox(height: 8),
                    Text('Failed to load timeline: ${snapshot.error}'),
                    const SizedBox(height: 12),
                    ElevatedButton(
                      onPressed: () => Navigator.pop(ctx),
                      child: const Text('Close'),
                    ),
                  ],
                ),
              );
            }

            final timeline = snapshot.data!;
            return Padding(
              padding: const EdgeInsets.all(20),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      const Text(
                        'Audit Revision Timeline',
                        style: TextStyle(
                            fontSize: 16, fontWeight: FontWeight.bold),
                      ),
                      IconButton(
                        icon: const Icon(Icons.close),
                        onPressed: () => Navigator.pop(ctx),
                      ),
                    ],
                  ),
                  const SizedBox(height: 8),
                  Text(
                    'Status: ${timeline.currentStatus} (${timeline.currentCredit.toStringAsFixed(2)} cr) — v${timeline.versionNo}',
                    style: const TextStyle(
                        fontSize: 13, fontWeight: FontWeight.w600),
                  ),
                  const SizedBox(height: 12),
                  const Divider(),
                  if (timeline.revisions.isEmpty)
                    const Padding(
                      padding: EdgeInsets.symmetric(vertical: 24),
                      child: Center(
                        child: Text(
                          'No revisions recorded for this session.',
                          style: TextStyle(color: Colors.grey),
                        ),
                      ),
                    )
                  else
                    Flexible(
                      child: ListView.builder(
                        shrinkWrap: true,
                        itemCount: timeline.revisions.length,
                        itemBuilder: (context, idx) {
                          final rev = timeline.revisions[idx];
                          return ListTile(
                            leading: const CircleAvatar(
                              radius: 14,
                              child: Icon(Icons.history, size: 16),
                            ),
                            title: Text(
                              rev.eventType,
                              style: const TextStyle(
                                  fontSize: 13, fontWeight: FontWeight.bold),
                            ),
                            subtitle: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(
                                  '${rev.previousStatus ?? "NONE"} → ${rev.newStatus ?? "UNCHANGED"}',
                                  style: const TextStyle(fontSize: 12),
                                ),
                                if (rev.reason != null)
                                  Text(
                                    '"${rev.reason}"',
                                    style: const TextStyle(
                                        fontSize: 11,
                                        fontStyle: FontStyle.italic),
                                  ),
                              ],
                            ),
                            trailing: Text(
                              rev.occurredAtUtc
                                  .toLocal()
                                  .toString()
                                  .split('.')[0],
                              style: const TextStyle(
                                  fontSize: 10, color: Colors.grey),
                            ),
                          );
                        },
                      ),
                    ),
                ],
              ),
            );
          },
        );
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Attendance History & Requests'),
        centerTitle: true,
        bottom: TabBar(
          controller: _tabController,
          tabs: const [
            Tab(icon: Icon(Icons.calendar_month), text: 'Attendance Records'),
            Tab(icon: Icon(Icons.pending_actions), text: 'My Requests'),
          ],
        ),
      ),
      body: TabBarView(
        controller: _tabController,
        children: [
          // Tab 1: Records list with actions
          RefreshIndicator(
            onRefresh: _loadRequests,
            child: ListView(
              padding: const EdgeInsets.all(16),
              children: [
                if (_successMessage != null)
                  Container(
                    margin: const EdgeInsets.only(bottom: 12),
                    padding: const EdgeInsets.all(12),
                    decoration: BoxDecoration(
                      color: Colors.green.shade50,
                      borderRadius: BorderRadius.circular(8),
                      border: Border.all(color: Colors.green.shade300),
                    ),
                    child: Row(
                      children: [
                        const Icon(Icons.check_circle,
                            color: Colors.green, size: 20),
                        const SizedBox(width: 8),
                        Expanded(
                          child: Text(
                            _successMessage!,
                            style: TextStyle(
                                color: Colors.green.shade900, fontSize: 13),
                          ),
                        ),
                        IconButton(
                          icon: const Icon(Icons.close, size: 16),
                          onPressed: () =>
                              setState(() => _successMessage = null),
                        ),
                      ],
                    ),
                  ),
                Text(
                  'Recent Class Sessions',
                  style: Theme.of(context).textTheme.titleSmall?.copyWith(
                        fontWeight: FontWeight.bold,
                      ),
                ),
                const SizedBox(height: 8),
                ..._sampleRecords.map((rec) {
                  final status = rec['status'] as String;
                  Color statusColor = Colors.grey;
                  if (status == 'PRESENT') statusColor = Colors.green;
                  if (status == 'LATE') statusColor = Colors.amber.shade800;
                  if (status == 'ABSENT') statusColor = Colors.red;

                  return Card(
                    margin: const EdgeInsets.only(bottom: 12),
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(12),
                    ),
                    child: Padding(
                      padding: const EdgeInsets.all(16),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Row(
                            mainAxisAlignment: MainAxisAlignment.spaceBetween,
                            children: [
                              Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text(
                                    rec['course_code'] as String,
                                    style: const TextStyle(
                                        fontSize: 16,
                                        fontWeight: FontWeight.bold),
                                  ),
                                  Text(
                                    rec['course_title'] as String,
                                    style: const TextStyle(
                                        fontSize: 12, color: Colors.grey),
                                  ),
                                ],
                              ),
                              Container(
                                padding: const EdgeInsets.symmetric(
                                    horizontal: 10, vertical: 4),
                                decoration: BoxDecoration(
                                  color: statusColor.withAlpha(30),
                                  borderRadius: BorderRadius.circular(12),
                                  border: Border.all(color: statusColor),
                                ),
                                child: Text(
                                  status,
                                  style: TextStyle(
                                    color: statusColor,
                                    fontWeight: FontWeight.bold,
                                    fontSize: 12,
                                  ),
                                ),
                              ),
                            ],
                          ),
                          const SizedBox(height: 12),
                          Row(
                            children: [
                              Text(
                                'Credit: ${(rec['credit'] as double).toStringAsFixed(1)}',
                                style: const TextStyle(
                                    fontSize: 12, fontWeight: FontWeight.w600),
                              ),
                              const Spacer(),
                              Text(
                                rec['date'] as String,
                                style: const TextStyle(
                                    fontSize: 12, color: Colors.grey),
                              ),
                            ],
                          ),
                          const SizedBox(height: 12),
                          const Divider(),
                          Wrap(
                            spacing: 8,
                            runSpacing: 4,
                            children: [
                              OutlinedButton.icon(
                                icon: const Icon(Icons.edit_note, size: 16),
                                label: const Text('Correction',
                                    style: TextStyle(fontSize: 12)),
                                onPressed: () => _showCorrectionDialog(rec),
                              ),
                              OutlinedButton.icon(
                                icon: const Icon(
                                    Icons.medical_services_outlined,
                                    size: 16),
                                label: const Text('Excuse',
                                    style: TextStyle(fontSize: 12)),
                                onPressed: () => _showExcuseDialog(rec),
                              ),
                              OutlinedButton.icon(
                                icon: const Icon(Icons.time_to_leave_outlined,
                                    size: 16),
                                label: const Text('Leave',
                                    style: TextStyle(fontSize: 12)),
                                onPressed: () => _showLeaveDialog(rec),
                              ),
                              IconButton(
                                icon: const Icon(Icons.history,
                                    size: 20, color: Colors.indigo),
                                tooltip: 'View Audit Timeline',
                                onPressed: () =>
                                    _showTimeline(rec['record_id'] as String),
                              ),
                            ],
                          ),
                        ],
                      ),
                    ),
                  );
                }),
              ],
            ),
          ),

          // Tab 2: My Requests
          RefreshIndicator(
            onRefresh: _loadRequests,
            child: _isLoading
                ? const Center(child: CircularProgressIndicator())
                : ListView(
                    padding: const EdgeInsets.all(16),
                    children: [
                      if (_errorMessage != null)
                        Container(
                          padding: const EdgeInsets.all(12),
                          margin: const EdgeInsets.only(bottom: 12),
                          decoration: BoxDecoration(
                            color: Colors.red.shade50,
                            borderRadius: BorderRadius.circular(8),
                            border: Border.all(color: Colors.red.shade300),
                          ),
                          child: Text(
                            _errorMessage!,
                            style: TextStyle(
                                color: Colors.red.shade900, fontSize: 13),
                          ),
                        ),
                      Text(
                        'Corrections (${_corrections.length})',
                        style: const TextStyle(
                            fontSize: 14, fontWeight: FontWeight.bold),
                      ),
                      const SizedBox(height: 8),
                      if (_corrections.isEmpty)
                        const Padding(
                          padding: EdgeInsets.symmetric(vertical: 8),
                          child: Text('No correction requests.',
                              style:
                                  TextStyle(color: Colors.grey, fontSize: 12)),
                        )
                      else
                        ..._corrections.map((c) {
                          return Card(
                            margin: const EdgeInsets.only(bottom: 8),
                            child: ListTile(
                              title: Text(
                                'Target: ${c.requestedStatus} (${c.requestType})',
                                style: const TextStyle(
                                    fontSize: 13, fontWeight: FontWeight.bold),
                              ),
                              subtitle: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text(c.reason,
                                      style: const TextStyle(fontSize: 12)),
                                  if (c.reviewNote != null)
                                    Text(
                                      'Review Note: ${c.reviewNote}',
                                      style: const TextStyle(
                                          fontSize: 11,
                                          fontStyle: FontStyle.italic),
                                    ),
                                ],
                              ),
                              trailing: Row(
                                mainAxisSize: MainAxisSize.min,
                                children: [
                                  Container(
                                    padding: const EdgeInsets.symmetric(
                                        horizontal: 8, vertical: 2),
                                    decoration: BoxDecoration(
                                      color: c.status == 'PENDING'
                                          ? Colors.amber.shade100
                                          : (c.status == 'APPROVED'
                                              ? Colors.green.shade100
                                              : Colors.red.shade100),
                                      borderRadius: BorderRadius.circular(8),
                                    ),
                                    child: Text(
                                      c.status,
                                      style: TextStyle(
                                        fontSize: 11,
                                        fontWeight: FontWeight.bold,
                                        color: c.status == 'PENDING'
                                            ? Colors.amber.shade900
                                            : (c.status == 'APPROVED'
                                                ? Colors.green.shade900
                                                : Colors.red.shade900),
                                      ),
                                    ),
                                  ),
                                  if (c.status == 'PENDING')
                                    IconButton(
                                      icon: const Icon(Icons.cancel,
                                          size: 18, color: Colors.grey),
                                      tooltip: 'Cancel Request',
                                      onPressed: () async {
                                        final messenger =
                                            ScaffoldMessenger.of(context);
                                        try {
                                          await widget.operationsService
                                              .cancelCorrectionRequest(
                                            requestId: c.id,
                                            authToken: widget.authToken,
                                          );
                                          _loadRequests();
                                        } catch (e) {
                                          messenger.showSnackBar(
                                            SnackBar(
                                                content:
                                                    Text('Cancel failed: $e')),
                                          );
                                        }
                                      },
                                    ),
                                ],
                              ),
                            ),
                          );
                        }),
                      const SizedBox(height: 16),
                      Text(
                        'Absence Excuses (${_excuses.length})',
                        style: const TextStyle(
                            fontSize: 14, fontWeight: FontWeight.bold),
                      ),
                      const SizedBox(height: 8),
                      if (_excuses.isEmpty)
                        const Padding(
                          padding: EdgeInsets.symmetric(vertical: 8),
                          child: Text('No excuse requests.',
                              style:
                                  TextStyle(color: Colors.grey, fontSize: 12)),
                        )
                      else
                        ..._excuses.map((e) {
                          return Card(
                            margin: const EdgeInsets.only(bottom: 8),
                            child: ListTile(
                              title: Text(
                                e.category,
                                style: const TextStyle(
                                    fontSize: 13, fontWeight: FontWeight.bold),
                              ),
                              subtitle: Text(e.description,
                                  style: const TextStyle(fontSize: 12)),
                              trailing: Text(
                                e.status,
                                style: const TextStyle(
                                    fontSize: 11, fontWeight: FontWeight.bold),
                              ),
                            ),
                          );
                        }),
                      const SizedBox(height: 16),
                      Text(
                        'Pre-Class Leaves (${_leaves.length})',
                        style: const TextStyle(
                            fontSize: 14, fontWeight: FontWeight.bold),
                      ),
                      const SizedBox(height: 8),
                      if (_leaves.isEmpty)
                        const Padding(
                          padding: EdgeInsets.symmetric(vertical: 8),
                          child: Text('No leave requests.',
                              style:
                                  TextStyle(color: Colors.grey, fontSize: 12)),
                        )
                      else
                        ..._leaves.map((l) {
                          return Card(
                            margin: const EdgeInsets.only(bottom: 8),
                            child: ListTile(
                              title: const Text(
                                'Leave Request (0.00 credit)',
                                style: TextStyle(
                                    fontSize: 13, fontWeight: FontWeight.bold),
                              ),
                              subtitle: Text(l.reason,
                                  style: const TextStyle(fontSize: 12)),
                              trailing: Text(
                                l.status,
                                style: const TextStyle(
                                    fontSize: 11, fontWeight: FontWeight.bold),
                              ),
                            ),
                          );
                        }),
                    ],
                  ),
          ),
        ],
      ),
    );
  }
}
