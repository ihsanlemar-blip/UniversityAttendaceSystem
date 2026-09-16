import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'core/api_client.dart';
import 'screens/student_attendance_history_screen.dart';
import 'screens/student_device_security_screen.dart';
import 'screens/student_qr_scanner_screen.dart';
import 'services/attendance_operations_service.dart';
import 'services/campus_network_service.dart';
import 'services/device_key_service.dart';
import 'services/qr_checkin_service.dart';


void main() {
  WidgetsFlutterBinding.ensureInitialized();
  runApp(const ProviderScope(child: AttendanceApp()));
}

class AttendanceApp extends StatelessWidget {
  const AttendanceApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'University Attendance',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(
          seedColor: Colors.indigo,
          brightness: Brightness.light,
        ),
        useMaterial3: true,
      ),
      home: const HomeScreen(),
    );
  }
}

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  // Physical Android device over ADB uses 127.0.0.1 (with adb reverse), emulator uses 10.0.2.2
  late final ApiClient _apiClient;
  bool _isBackendHealthy = false;
  bool _isChecking = true;
  String _activeUrl = 'http://127.0.0.1:8000';

  @override
  void initState() {
    super.initState();
    _initAndCheckConnectivity();
  }

  Future<void> _initAndCheckConnectivity() async {
    setState(() => _isChecking = true);

    // 1. Try 127.0.0.1:8000 (ADB reverse for physical device)
    try {
      final client1 = ApiClient(baseUrl: 'http://127.0.0.1:8000');
      final res1 = await client1.checkReadiness();
      if (res1['status'] == 'ready') {
        _apiClient = client1;
        _activeUrl = 'http://127.0.0.1:8000';
        if (mounted) {
          setState(() {
            _isBackendHealthy = true;
            _isChecking = false;
          });
        }
        return;
      }
    } catch (_) {}

    // 2. Fallback to 10.0.2.2:8000 (Android Emulator standard)
    try {
      final client2 = ApiClient(baseUrl: 'http://10.0.2.2:8000');
      final res2 = await client2.checkReadiness();
      if (res2['status'] == 'ready') {
        _apiClient = client2;
        _activeUrl = 'http://10.0.2.2:8000';
        if (mounted) {
          setState(() {
            _isBackendHealthy = true;
            _isChecking = false;
          });
        }
        return;
      }
    } catch (_) {}

    // Default fallback
    _apiClient = ApiClient(baseUrl: _activeUrl);
    if (mounted) {
      setState(() {
        _isBackendHealthy = false;
        _isChecking = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Scaffold(
      appBar: AppBar(
        title: const Text('University Attendance'),
        centerTitle: true,
        backgroundColor: theme.colorScheme.inversePrimary,
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            tooltip: 'Recheck Backend Status',
            onPressed: _initAndCheckConnectivity,
          ),
        ],
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            const Center(
              child: Column(
                children: [
                  Icon(Icons.school, size: 56, color: Colors.indigo),
                  SizedBox(height: 12),
                  Text(
                    'Digital Student Attendance System',
                    textAlign: TextAlign.center,
                    style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
                  ),
                  SizedBox(height: 4),
                  Text(
                    'Milestone 3 — Bootstrap Shell',
                    style: TextStyle(fontSize: 12, color: Colors.grey),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 20),

            // Backend Connectivity Status Card
            Card(
              elevation: 0,
              color: _isBackendHealthy
                  ? Colors.green.withAlpha(25)
                  : Colors.amber.withAlpha(25),
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(12),
                side: BorderSide(
                  color:
                      _isBackendHealthy ? Colors.green : Colors.amber.shade700,
                ),
              ),
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Row(
                  children: [
                    Icon(
                      _isChecking
                          ? Icons.sync
                          : (_isBackendHealthy
                              ? Icons.check_circle
                              : Icons.warning_amber),
                      color: _isBackendHealthy
                          ? Colors.green
                          : Colors.amber.shade800,
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            _isChecking
                                ? 'Checking Backend API...'
                                : (_isBackendHealthy
                                    ? 'Backend Operational (Ready)'
                                    : 'Backend Offline / Connecting...'),
                            style: const TextStyle(
                              fontWeight: FontWeight.bold,
                              fontSize: 14,
                            ),
                          ),
                          const SizedBox(height: 2),
                          Text(
                            'Endpoint: $_activeUrl',
                            style: TextStyle(
                              fontSize: 12,
                              color: Colors.grey.shade700,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 24),

            // Services Header
            Text(
              'Student Attendance Services',
              style: theme.textTheme.titleMedium?.copyWith(
                fontWeight: FontWeight.bold,
              ),
            ),
            const SizedBox(height: 12),

            // Device Security Screen Launcher
            Card(
              elevation: 1,
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(12),
              ),
              child: ListTile(
                leading: const CircleAvatar(
                  backgroundColor: Colors.indigo,
                  child: Icon(Icons.security, color: Colors.white),
                ),
                title: const Text('Device Trust & Security'),
                subtitle: const Text(
                  'Hardware-backed Ed25519 identity & primary device trust',
                  style: TextStyle(fontSize: 12),
                ),
                trailing: const Icon(Icons.chevron_right),
                onTap: () {
                  Navigator.push(
                    context,
                    MaterialPageRoute(
                      builder: (ctx) => StudentDeviceSecurityScreen(
                        apiClient: _apiClient,
                        authToken: 'demo_dev_token',
                        universityId: '0192323e-6708-724a-a43b-8106daee86fa',
                        userId: '0192323e-6708-724a-a43b-8106daee86fb',
                      ),
                    ),
                  );
                },
              ),
            ),
            const SizedBox(height: 12),

            // QR & BLE Scanner Launcher
            Card(
              elevation: 1,
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(12),
              ),
              child: ListTile(
                leading: const CircleAvatar(
                  backgroundColor: Colors.teal,
                  child: Icon(Icons.qr_code_scanner, color: Colors.white),
                ),
                title: const Text('Attendance QR & BLE Scanner'),
                subtitle: const Text(
                  'Camera QR scanner with dual-factor BLE verification',
                  style: TextStyle(fontSize: 12),
                ),
                trailing: const Icon(Icons.chevron_right),
                onTap: () {
                  Navigator.push(
                    context,
                    MaterialPageRoute(
                      builder: (ctx) => StudentQrScannerScreen(
                        checkInService: QrCheckInService(
                          baseUrl: _apiClient.baseUrl,
                        ),
                        deviceKeyService: DeviceKeyService(),
                        campusNetworkService: CampusNetworkService(
                          baseUrl: _apiClient.baseUrl,
                        ),
                        authToken: 'demo_dev_token',
                        userId: '0192323e-6708-724a-a43b-8106daee86fb',
                        universityId: '0192323e-6708-724a-a43b-8106daee86fa',
                        enableManualTokenEntry: true,
                        onCompleted: () => Navigator.pop(context),
                      ),
                    ),
                  );
                },
              ),
            ),
            const SizedBox(height: 12),

            // Attendance Operations & Corrections Launcher
            Card(
              elevation: 1,
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(12),
              ),
              child: ListTile(
                leading: const CircleAvatar(
                  backgroundColor: Colors.amber,
                  child: Icon(Icons.history_edu, color: Colors.white),
                ),
                title: const Text('Attendance History & Requests'),
                subtitle: const Text(
                  'Record audit timeline, corrections, absence excuses, and leave',
                  style: TextStyle(fontSize: 12),
                ),
                trailing: const Icon(Icons.chevron_right),
                onTap: () {
                  Navigator.push(
                    context,
                    MaterialPageRoute(
                      builder: (ctx) => StudentAttendanceHistoryScreen(
                        operationsService: AttendanceOperationsService(
                          baseUrl: _apiClient.baseUrl,
                        ),
                        authToken: 'demo_dev_token',
                        studentId: '0192323e-6708-724a-a43b-8106daee86fa',
                      ),
                    ),
                  );
                },
              ),
            ),
          ],
        ),
      ),
    );
  }
}
