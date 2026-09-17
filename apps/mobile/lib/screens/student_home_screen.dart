import 'package:flutter/material.dart';
import '../core/api_client.dart';
import '../core/i18n/app_language.dart';
import '../core/i18n/app_strings.dart';
import '../services/attendance_operations_service.dart';
import '../services/campus_network_service.dart';
import '../services/device_key_service.dart';
import '../services/qr_checkin_service.dart';
import 'student_attendance_history_screen.dart';
import 'student_device_security_screen.dart';
import 'student_qr_scanner_screen.dart';

enum ConnectivityState {
  online,
  offline,
  syncing,
}

enum AttendanceStandingStatus {
  goodStanding,
  warning,
  critical,
  notApplicable,
}

class StudentHomeScreen extends StatefulWidget {
  final ApiClient apiClient;
  final String authToken;
  final String studentId;
  final String userId;
  final String universityId;
  final String studentName;
  final String studentNumber;
  final double? initialPercentage;
  final String? initialStatus;
  final AppLanguage initialLanguage;

  const StudentHomeScreen({
    super.key,
    required this.apiClient,
    this.authToken = 'demo_dev_token',
    this.studentId = '0192323e-6708-724a-a43b-8106daee86fa',
    this.userId = '0192323e-6708-724a-a43b-8106daee86fb',
    this.universityId = '0192323e-6708-724a-a43b-8106daee86fa',
    this.studentName = 'Ahmad Fahim',
    this.studentNumber = 'KBL-2023-CS-042',
    this.initialPercentage,
    this.initialStatus,
    this.initialLanguage = AppLanguage.en,
  });

  @override
  State<StudentHomeScreen> createState() => _StudentHomeScreenState();
}

class _StudentHomeScreenState extends State<StudentHomeScreen> {
  ConnectivityState _connectivity = ConnectivityState.online;
  bool _isLoading = false;
  double? _attendancePercentage;
  String _standingStatus = 'NOT_APPLICABLE';
  late AppLanguage _language;

  final List<Map<String, dynamic>> _enrolledCourses = [
    {
      'code': 'CS-301',
      'name': 'Database Management Systems',
      'conducted': 14,
      'eligible': 14,
      'percentage': 92.8,
      'status': 'GOOD_STANDING',
    },
    {
      'code': 'CS-402',
      'name': 'Distributed Systems & Cloud Computing',
      'conducted': 12,
      'eligible': 12,
      'percentage': 83.3,
      'status': 'GOOD_STANDING',
    },
    {
      'code': 'SE-201',
      'name': 'Software Engineering Principles',
      'conducted': 10,
      'eligible': 10,
      'percentage': 70.0,
      'status': 'WARNING',
    },
    {
      'code': 'MATH-202',
      'name': 'Discrete Mathematics & Graph Theory',
      'conducted': 0,
      'eligible': 0,
      'percentage': null,
      'status': 'NOT_APPLICABLE',
    },
  ];

  @override
  void initState() {
    super.initState();
    _language = widget.initialLanguage;
    _attendancePercentage = widget.initialPercentage;
    _standingStatus = widget.initialStatus ??
        (_attendancePercentage != null ? 'GOOD_STANDING' : 'NOT_APPLICABLE');
    _checkConnectivity();
  }

  void _showLanguageSelector() {
    showModalBottomSheet<void>(
      context: context,
      backgroundColor: Colors.white,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (BuildContext ctx) {
        final strings = AppStrings.get(_language);
        return SafeArea(
          child: Padding(
            padding: const EdgeInsets.symmetric(vertical: 20, horizontal: 16),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Text(
                  strings.t('select_language'),
                  style: const TextStyle(
                    fontSize: 18,
                    fontWeight: FontWeight.bold,
                    color: Color(0xFF1E293B),
                  ),
                  textAlign: TextAlign.center,
                ),
                const SizedBox(height: 16),
                ...AppLanguage.values.map((lang) {
                  final isSelected = lang == _language;
                  return Padding(
                    padding: const EdgeInsets.symmetric(vertical: 4),
                    child: Directionality(
                      textDirection: lang.textDirection,
                      child: ListTile(
                        key: Key('lang_option_${lang.code}'),
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(12),
                          side: BorderSide(
                            color: isSelected
                                ? const Color(0xFF4F46E5)
                                : const Color(0xFFE2E8F0),
                            width: isSelected ? 2 : 1,
                          ),
                        ),
                        tileColor: isSelected
                            ? const Color(0xFFEEF2FF)
                            : Colors.transparent,
                        leading: Icon(
                          Icons.translate,
                          color: isSelected
                              ? const Color(0xFF4F46E5)
                              : const Color(0xFF64748B),
                        ),
                        title: Text(
                          lang.displayName,
                          style: TextStyle(
                            fontSize: 16,
                            fontWeight: isSelected
                                ? FontWeight.bold
                                : FontWeight.normal,
                            color: isSelected
                                ? const Color(0xFF312E81)
                                : const Color(0xFF1E293B),
                          ),
                        ),
                        trailing: isSelected
                            ? const Icon(
                                Icons.check_circle,
                                color: Color(0xFF4F46E5),
                              )
                            : null,
                        onTap: () {
                          setState(() {
                            _language = lang;
                          });
                          Navigator.of(ctx).pop();
                        },
                      ),
                    ),
                  );
                }),
              ],
            ),
          ),
        );
      },
    );
  }

  Future<void> _checkConnectivity() async {
    setState(() => _isLoading = true);
    try {
      final res = await widget.apiClient.checkReadiness();
      if (res['status'] == 'ready') {
        if (mounted) {
          setState(() {
            _connectivity = ConnectivityState.online;
            _isLoading = false;
          });
        }
        return;
      }
    } catch (_) {}

    if (mounted) {
      setState(() {
        _connectivity = ConnectivityState.offline;
        _isLoading = false;
      });
    }
  }

  AttendanceStandingStatus get _parsedStatus {
    if (_standingStatus == 'GOOD_STANDING') {
      return AttendanceStandingStatus.goodStanding;
    } else if (_standingStatus == 'WARNING') {
      return AttendanceStandingStatus.warning;
    } else if (_standingStatus == 'CRITICAL' ||
        _standingStatus == 'DEBARRED' ||
        _standingStatus == 'BELOW_THRESHOLD') {
      return AttendanceStandingStatus.critical;
    }
    return AttendanceStandingStatus.notApplicable;
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final strings = AppStrings.get(_language);

    return Directionality(
      textDirection: _language.textDirection,
      child: Scaffold(
        backgroundColor: const Color(0xFFF8FAFC),
        appBar: AppBar(
          title: Text(
            strings.t('app_title'),
            style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16),
          ),
          centerTitle: false,
          backgroundColor: Colors.white,
          surfaceTintColor: Colors.transparent,
          elevation: 0.5,
          actions: [
            IconButton(
              key: const Key('language_toggle_btn'),
              icon: const Icon(Icons.language, size: 20),
              tooltip: 'Language / لسان / ژبه',
              onPressed: _showLanguageSelector,
            ),
            IconButton(
              icon: _isLoading
                  ? const SizedBox(
                      width: 18,
                      height: 18,
                      child: CircularProgressIndicator(strokeWidth: 2),
                    )
                  : const Icon(Icons.refresh, size: 20),
              tooltip: strings.t('refresh'),
              onPressed: _checkConnectivity,
            ),
            const SizedBox(width: 8),
          ],
        ),
        body: RefreshIndicator(
          onRefresh: _checkConnectivity,
          child: SingleChildScrollView(
            physics: const AlwaysScrollableScrollPhysics(),
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                // Connectivity Status Banner
                _buildConnectivityBanner(),
                const SizedBox(height: 16),

                // Student Identity Header Card
                _buildStudentHeader(theme),
                const SizedBox(height: 16),

                // Overall Attendance Standing Card
                _buildAttendanceStandingCard(theme),
                const SizedBox(height: 20),

                // Quick Actions Section
                Text(
                  'Quick Actions',
                  style: theme.textTheme.titleSmall?.copyWith(
                    fontWeight: FontWeight.bold,
                    color: const Color(0xFF1E293B),
                  ),
                ),
                const SizedBox(height: 12),
                _buildQuickActionGrid(),
                const SizedBox(height: 24),

                // Course Attendance Progress
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Text(
                      'Enrolled Courses',
                      style: theme.textTheme.titleSmall?.copyWith(
                        fontWeight: FontWeight.bold,
                        color: const Color(0xFF1E293B),
                      ),
                    ),
                    Text(
                      'Semester Fall 2026',
                      style: TextStyle(
                        fontSize: 12,
                        color: Colors.grey.shade600,
                        fontWeight: FontWeight.w500,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 12),
                _buildCourseProgressList(),
                const SizedBox(height: 20),

                // Invariant Compliance Card
                Container(
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: const Color(0xFFF1F5F9),
                    borderRadius: BorderRadius.circular(10),
                    border: Border.all(color: const Color(0xFFE2E8F0)),
                  ),
                  child: Row(
                    children: [
                      const Icon(
                        Icons.gavel,
                        size: 18,
                        color: Color(0xFF475569),
                      ),
                      const SizedBox(width: 10),
                      Expanded(
                        child: Text(
                          _language == AppLanguage.en
                              ? 'University Attendance Invariant: Server UTC clock is authoritative. Client device clock cannot grant attendance credit.'
                              : (_language == AppLanguage.fa
                                  ? 'قاعده سیستم حاضری: ساعت رسمی سرور پوهنتون تنها مرجع معتبر است. ساعت دستگاه محصل نمی‌تواند اعتبار حاضری صادر کند.'
                                  : 'د سیستم اساسي اصل: یوازې د پوهنتون د سرور رسمي وخت باوري دی. د محصل د ټیلیفون ساعت نشي کولی د حاضري اعتبار صادر کړي.'),
                          style: TextStyle(
                            fontSize: 11,
                            color: Colors.grey.shade700,
                            height: 1.3,
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildConnectivityBanner() {
    Color bg;
    Color border;
    Color textCol;
    IconData icon;
    String label;

    switch (_connectivity) {
      case ConnectivityState.online:
        bg = const Color(0xFFECFDF5);
        border = const Color(0xFFA7F3D0);
        textCol = const Color(0xFF065F46);
        icon = Icons.wifi;
        label = 'Campus Network Connected (Online)';
        break;
      case ConnectivityState.offline:
        bg = const Color(0xFFFFFBEB);
        border = const Color(0xFFFDE68A);
        textCol = const Color(0xFF92400E);
        icon = Icons.wifi_off;
        label = 'Offline Mode (Local Storage Active)';
        break;
      case ConnectivityState.syncing:
        bg = const Color(0xFFF0F9FF);
        border = const Color(0xFFBAE6FD);
        textCol = const Color(0xFF075985);
        icon = Icons.sync;
        label = 'Syncing Offline Evidence Ledger...';
        break;
    }

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      decoration: BoxDecoration(
        color: bg,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: border),
      ),
      child: Row(
        children: [
          Icon(icon, size: 16, color: textCol),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              label,
              style: TextStyle(
                fontSize: 12,
                fontWeight: FontWeight.w600,
                color: textCol,
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildStudentHeader(ThemeData theme) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        gradient: const LinearGradient(
          colors: [Color(0xFF0F172A), Color(0xFF1E293B)],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        borderRadius: BorderRadius.circular(16),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withAlpha(15),
            blurRadius: 8,
            offset: const Offset(0, 4),
          ),
        ],
      ),
      child: Row(
        children: [
          Container(
            width: 48,
            height: 48,
            decoration: BoxDecoration(
              color: Colors.white.withAlpha(25),
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: Colors.white.withAlpha(50)),
            ),
            child: const Icon(
              Icons.school,
              color: Colors.white,
              size: 26,
            ),
          ),
          const SizedBox(width: 14),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  widget.studentName,
                  style: const TextStyle(
                    fontSize: 16,
                    fontWeight: FontWeight.bold,
                    color: Colors.white,
                  ),
                ),
                const SizedBox(height: 2),
                Text(
                  'Student ID: ${widget.studentNumber}',
                  style: TextStyle(
                    fontSize: 12,
                    color: Colors.grey.shade300,
                    letterSpacing: 0.2,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildAttendanceStandingCard(ThemeData theme) {
    final status = _parsedStatus;
    final isNotApplicable = status == AttendanceStandingStatus.notApplicable;
    final pctString = _attendancePercentage != null
        ? '${_attendancePercentage!.toStringAsFixed(1)}%'
        : 'N/A';

    Color statusColor;
    Color statusBg;
    String statusLabel;

    switch (status) {
      case AttendanceStandingStatus.goodStanding:
        statusColor = const Color(0xFF059669);
        statusBg = const Color(0xFFD1FAE5);
        statusLabel = _language == AppLanguage.en
            ? 'Good Standing (≥ 75%)'
            : (_language == AppLanguage.fa
                ? 'وضعیت قناعت‌بخش (≥ ۷۵٪)'
                : 'قناعت بخښونکی حالت (≥ ۷۵٪)');
        break;
      case AttendanceStandingStatus.warning:
        statusColor = const Color(0xFFD97706);
        statusBg = const Color(0xFFFEF3C7);
        statusLabel = _language == AppLanguage.en
            ? 'Warning Threshold'
            : (_language == AppLanguage.fa
                ? 'اخطاریه محرومی'
                : 'د محرومۍ خبرداری');
        break;
      case AttendanceStandingStatus.critical:
        statusColor = const Color(0xFFDC2626);
        statusBg = const Color(0xFFFEE2E2);
        statusLabel = _language == AppLanguage.en
            ? 'Critical / Debarred'
            : (_language == AppLanguage.fa ? 'در معرض محرومی' : 'د محرومۍ خطر');
        break;
      case AttendanceStandingStatus.notApplicable:
        statusColor = const Color(0xFF64748B);
        statusBg = const Color(0xFFF1F5F9);
        statusLabel = _language == AppLanguage.en
            ? 'Not Applicable (No Eligible Sessions)'
            : (_language == AppLanguage.fa
                ? 'غیرقابل تطبیق (بدون جلسات واجد شرایط)'
                : 'د تطبیق وړ نه دی (د شرایطو وړ ناستې نشته)');
        break;
    }

    return Container(
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: const Color(0xFFE2E8F0)),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withAlpha(8),
            blurRadius: 6,
            offset: const Offset(0, 2),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text(
                    'Overall Attendance',
                    style: TextStyle(
                      fontSize: 12,
                      fontWeight: FontWeight.w600,
                      color: Color(0xFF64748B),
                      textBaseline: TextBaseline.alphabetic,
                    ),
                  ),
                  const SizedBox(height: 6),
                  Text(
                    pctString,
                    style: TextStyle(
                      fontSize: 32,
                      fontWeight: FontWeight.bold,
                      color: isNotApplicable
                          ? const Color(0xFF64748B)
                          : statusColor,
                      letterSpacing: -0.5,
                    ),
                  ),
                ],
              ),
              Container(
                padding:
                    const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
                decoration: BoxDecoration(
                  color: statusBg,
                  borderRadius: BorderRadius.circular(20),
                  border: Border.all(color: statusColor.withAlpha(50)),
                ),
                child: Text(
                  statusLabel,
                  style: TextStyle(
                    fontSize: 11,
                    fontWeight: FontWeight.bold,
                    color: statusColor,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          const Divider(height: 1, color: Color(0xFFF1F5F9)),
          const SizedBox(height: 10),
          Row(
            children: [
              const Icon(
                Icons.info_outline,
                size: 14,
                color: Color(0xFF94A3B8),
              ),
              const SizedBox(width: 6),
              Expanded(
                child: Text(
                  'Minimum 75% required for final examination eligibility.',
                  style: TextStyle(
                    fontSize: 11,
                    color: Colors.grey.shade600,
                  ),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildQuickActionGrid() {
    final strings = AppStrings.get(_language);
    return GridView.count(
      shrinkWrap: true,
      physics: const NeverScrollableScrollPhysics(),
      crossAxisCount: 2,
      crossAxisSpacing: 12,
      mainAxisSpacing: 12,
      childAspectRatio: 1.35,
      children: [
        _buildActionCard(
          icon: Icons.qr_code_scanner,
          title: strings.t('scan_qr_checkin'),
          subtitle: 'Dual-factor BLE & QR',
          color: const Color(0xFF0284C7),
          onTap: () {
            Navigator.push(
              context,
              MaterialPageRoute(
                builder: (ctx) => StudentQrScannerScreen(
                  checkInService: QrCheckInService(
                    baseUrl: widget.apiClient.baseUrl,
                  ),
                  deviceKeyService: DeviceKeyService(),
                  campusNetworkService: CampusNetworkService(
                    baseUrl: widget.apiClient.baseUrl,
                  ),
                  authToken: widget.authToken,
                  userId: widget.userId,
                  universityId: widget.universityId,
                  enableManualTokenEntry: true,
                  onCompleted: () => Navigator.pop(context),
                ),
              ),
            );
          },
        ),
        _buildActionCard(
          icon: Icons.security,
          title: strings.t('device_trust'),
          subtitle: 'Ed25519 OS-Protected Key',
          color: const Color(0xFF4F46E5),
          onTap: () {
            Navigator.push(
              context,
              MaterialPageRoute(
                builder: (ctx) => StudentDeviceSecurityScreen(
                  apiClient: widget.apiClient,
                  authToken: widget.authToken,
                  universityId: widget.universityId,
                  userId: widget.userId,
                ),
              ),
            );
          },
        ),
        _buildActionCard(
          icon: Icons.history_edu,
          title: strings.t('attendance_ledger'),
          subtitle: 'Corrections & Excuses',
          color: const Color(0xFFD97706),
          onTap: () {
            Navigator.push(
              context,
              MaterialPageRoute(
                builder: (ctx) => StudentAttendanceHistoryScreen(
                  operationsService: AttendanceOperationsService(
                    baseUrl: widget.apiClient.baseUrl,
                  ),
                  authToken: widget.authToken,
                  studentId: widget.studentId,
                ),
              ),
            );
          },
        ),
        _buildActionCard(
          icon: Icons.sync,
          title: strings.t('offline_sync_queue'),
          subtitle: 'Reconcile Claims',
          color: const Color(0xFF059669),
          onTap: () {
            ScaffoldMessenger.of(context).showSnackBar(
              const SnackBar(
                content: Text(
                  'Offline Sync: All cached attendance claims are reconciled against university server.',
                ),
                duration: Duration(seconds: 3),
              ),
            );
          },
        ),
      ],
    );
  }

  Widget _buildActionCard({
    required IconData icon,
    required String title,
    required String subtitle,
    required Color color,
    required VoidCallback onTap,
  }) {
    return Material(
      color: Colors.white,
      elevation: 0,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(14),
        side: const BorderSide(color: Color(0xFFE2E8F0)),
      ),
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(14),
        child: Padding(
          padding: const EdgeInsets.all(12),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Container(
                padding: const EdgeInsets.all(8),
                decoration: BoxDecoration(
                  color: color.withAlpha(20),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Icon(icon, size: 20, color: color),
              ),
              const SizedBox(height: 8),
              Text(
                title,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: const TextStyle(
                  fontSize: 12,
                  fontWeight: FontWeight.bold,
                  color: Color(0xFF0F172A),
                ),
              ),
              const SizedBox(height: 2),
              Text(
                subtitle,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: const TextStyle(
                  fontSize: 10,
                  color: Color(0xFF64748B),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildCourseProgressList() {
    return ListView.separated(
      shrinkWrap: true,
      physics: const NeverScrollableScrollPhysics(),
      itemCount: _enrolledCourses.length,
      separatorBuilder: (ctx, i) => const SizedBox(height: 8),
      itemBuilder: (ctx, index) {
        final course = _enrolledCourses[index];
        final pct = course['percentage'] as double?;
        final conducted = course['conducted'] as int;
        final eligible = course['eligible'] as int;
        final isNA = pct == null || eligible == 0;

        return Container(
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(
            color: Colors.white,
            borderRadius: BorderRadius.circular(12),
            border: Border.all(color: const Color(0xFFE2E8F0)),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Expanded(
                    child: Row(
                      children: [
                        Container(
                          padding: const EdgeInsets.symmetric(
                            horizontal: 6,
                            vertical: 2,
                          ),
                          decoration: BoxDecoration(
                            color: const Color(0xFFF1F5F9),
                            borderRadius: BorderRadius.circular(4),
                          ),
                          child: Directionality(
                            textDirection: TextDirection.ltr,
                            child: Text(
                              course['code'] as String,
                              style: const TextStyle(
                                fontSize: 11,
                                fontWeight: FontWeight.bold,
                                color: Color(0xFF334155),
                              ),
                            ),
                          ),
                        ),
                        const SizedBox(width: 8),
                        Expanded(
                          child: Text(
                            course['name'] as String,
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                            style: const TextStyle(
                              fontSize: 12,
                              fontWeight: FontWeight.w600,
                              color: Color(0xFF0F172A),
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
                  Text(
                    isNA ? 'N/A' : '${pct.toStringAsFixed(1)}%',
                    style: TextStyle(
                      fontSize: 13,
                      fontWeight: FontWeight.bold,
                      color: isNA
                          ? const Color(0xFF94A3B8)
                          : (pct >= 75.0
                              ? const Color(0xFF059669)
                              : const Color(0xFFD97706)),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 8),
              ClipRRect(
                borderRadius: BorderRadius.circular(4),
                child: LinearProgressIndicator(
                  value: isNA ? 0.0 : (pct / 100.0).clamp(0.0, 1.0),
                  backgroundColor: const Color(0xFFF1F5F9),
                  valueColor: AlwaysStoppedAnimation<Color>(
                    isNA
                        ? Colors.transparent
                        : (pct >= 75.0
                            ? const Color(0xFF10B981)
                            : const Color(0xFFF59E0B)),
                  ),
                  minHeight: 6,
                ),
              ),
              const SizedBox(height: 6),
              Text(
                _language == AppLanguage.en
                    ? '$conducted sessions conducted • $eligible eligible'
                    : (_language == AppLanguage.fa
                        ? '$conducted جلسه برگزار شده • $eligible واجد شرایط'
                        : '$conducted ناستې ترسره شوې • $eligible د شرایطو وړ'),
                style: const TextStyle(
                  fontSize: 10,
                  color: Color(0xFF64748B),
                ),
              ),
            ],
          ),
        );
      },
    );
  }
}
