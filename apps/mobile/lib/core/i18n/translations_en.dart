/// English translations dictionary for DSAS mobile client.
const Map<String, String> translationsEn = {
  // App
  'app_title': 'University Attendance',
  'system_name': 'Digital Student Attendance System',
  'select_language': 'Select Language',
  'close': 'Close',
  'retry': 'Retry',
  'cancel': 'Cancel',
  'confirm': 'Confirm',
  'refresh': 'Refresh',

  // Statuses
  'status_present': 'Present',
  'status_late': 'Late',
  'status_absent': 'Absent',
  'status_excused': 'Excused',
  'status_good_standing': 'Good Standing',
  'status_warning': 'Warning',
  'status_critical': 'Critical',
  'status_not_applicable': 'Not Applicable (No Eligible Sessions)',

  // Academic Terminology
  'academic_university': 'University',
  'academic_faculty': 'Faculty',
  'academic_department': 'Department',
  'academic_credit': 'Credit',
  'academic_semester': 'Semester',
  'academic_morning_shift': 'Morning Shift',
  'academic_afternoon_shift': 'Afternoon Shift',

  // Home Screen
  'student_id_prefix': 'Student ID: ',
  'standing_label': 'Attendance Standing',
  'attendance_rate': 'Overall Attendance Rate',
  'quick_actions': 'Quick Actions',
  'scan_qr_checkin': 'Scan QR Check-In',
  'device_trust': 'Device Trust',
  'attendance_ledger': 'Attendance Ledger',
  'offline_sync_queue': 'Offline Sync Queue',
  'enrolled_courses': 'Enrolled Courses',
  'conducted_sessions': 'Conducted',
  'eligible_sessions': 'Eligible',
  'view_details': 'View Details',
  'connection_online': 'Online',
  'connection_offline': 'Offline Mode',
  'connection_syncing': 'Syncing...',

  // Scanner Screen
  'scanner_title': 'Scan Attendance QR',
  'scanner_instruction': 'Point camera at classroom projection screen',
  'scanning_active': 'Scanning dynamic classroom QR code...',
  'ble_detecting': 'Verifying classroom BLE presence beacon...',
  'ble_verified': 'Classroom BLE beacon verified',
  'ble_not_found': 'Classroom BLE beacon not detected yet',
  'network_verified': 'Campus network verified',
  'manual_entry_toggle': 'Enter Dynamic Token Manually',
  'manual_token_label': 'Dynamic Checkpoint Token',
  'submit_token': 'Submit Token',

  // Check-In Result Cards
  'attendance_confirmed_title': 'Attendance Confirmed',
  'attendance_confirmed_subtitle':
      'Your attendance checkpoint has been successfully recorded on the university ledger.',
  'already_recorded_title': 'Already Recorded',
  'already_recorded_subtitle':
      'Your attendance for this checkpoint was already recorded. Duplicate submission ignored without penalty.',
  'offline_recorded_title': 'Saved for Synchronization',
  'offline_recorded_subtitle':
      'Evidence captured and cryptographically signed offline. Will sync automatically when network is restored.',
  'token_expired_title': 'Token Expired',
  'token_expired_subtitle':
      'The projected token has rotated. Please scan the newly displayed dynamic QR code on the classroom screen.',
  'checkpoint_not_open_title': 'Checkpoint Not Open',
  'checkpoint_not_open_subtitle':
      'This session checkpoint is not currently accepting check-ins.',
  'session_closed_title': 'Session Closed',
  'session_closed_subtitle':
      'The attendance window for this lecture session has concluded.',
  'device_not_registered_title': 'Device Not Registered',
  'device_not_registered_subtitle':
      'This device is not bound to your university account. Register this phone under Device Trust first.',
  'ble_required_title': 'Classroom BLE Required',
  'ble_required_subtitle':
      'Bluetooth presence beacon not detected. Ensure Bluetooth is enabled and you are inside the classroom.',
  'campus_wifi_required_title': 'Campus Wi-Fi Required',
  'campus_wifi_required_subtitle':
      'Session requires connection to authorized campus network.',
  'not_enrolled_title': 'Not Enrolled',
  'not_enrolled_subtitle':
      'You are not officially registered in this course section.',
  'server_unreachable_title': 'Server Unreachable',
  'server_unreachable_subtitle':
      'Unable to connect to university server. Attendance evidence has been saved offline.',

  // Device Trust
  'device_trust_title': 'Device Trust & Cryptography',
  'device_registered': 'Device Registered & Trusted',
  'device_unregistered': 'Device Unregistered',
  'device_fingerprint': 'Device Key Fingerprint',
  'register_device': 'Register This Device',
  'verify_hardware_keystore': 'OS-Protected Keystore Security Verified',
};
